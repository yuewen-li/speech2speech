import asyncio
import websockets
import json
import logging
import numpy as np
import base64
from typing import Dict, Set
from src.service.transcription_service import StreamingSpeechService
from src.service.translation_service import TranslationService
from src.service.tts_service import TTSService
from src.utils.config import Config

# WebRTC imports
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    MediaStreamTrack,
)
from aiortc.sdp import candidate_from_sdp
import av
from aiohttp import web
import io


logger = logging.getLogger(__name__)


class StreamingTranslationServer:
    """
    WebSocket server for real-time streaming speech translation
    """

    def __init__(self, gemini_api_key: str):
        self.gemini_api_key = gemini_api_key
        self.translation_service = TranslationService(gemini_api_key)
        self.tts_service = TTSService()

        # Active connections
        self.active_connections: Set[websockets.WebSocketServerProtocol] = set()

        # Streaming services per connection
        self.connection_services: Dict[
            websockets.WebSocketServerProtocol, StreamingSpeechService
        ] = {}

        # For WebRTC peer connections per websocket
        self.ws_to_pc: Dict[websockets.WebSocketServerProtocol, RTCPeerConnection] = {}
        self.ws_to_tts_track: Dict[
            websockets.WebSocketServerProtocol, MediaStreamTrack
        ] = {}
        self.ws_to_data_channel: Dict[websockets.WebSocketServerProtocol, object] = {}

    async def handle_connection(self, websocket):
        """Handle new WebSocket connection"""
        try:
            # Add to active connections
            self.active_connections.add(websocket)
            init_msg = await websocket.recv()
            data = json.loads(init_msg)
            # Simple token auth
            token = data.get("token")
            if Config.WS_TOKEN and token != Config.WS_TOKEN:
                await websocket.close(code=4401, reason="Unauthorized")
                return
            language = data.get("language", "en-US")
            logger.info(
                f"New connection from {websocket.remote_address} for language: {language}"
            )

            # Create streaming service for this connection
            streaming_service = StreamingSpeechService(
                language=language,
                sample_rate=Config.SAMPLE_RATE,
                chunk_size=Config.CHUNK_SIZE,
            )

            # Set up callbacks
            streaming_service.set_callbacks(
                on_transcription=self._on_transcription(websocket)
            )

            self.connection_services[websocket] = streaming_service
            logger.info(
                f"New WebSocket connection established. Total connections: {len(self.active_connections)}"
            )

            # Handle messages
            async for message in websocket:
                await self._handle_message(websocket, message)

        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except websockets.exceptions.ConnectionClosedError as e:
            logger.error(f"WebSocket connection closed with error: {e}")
        except Exception as e:
            logger.error(f"Error handling WebSocket connection: {e}")
        finally:
            # Cleanup
            await self._cleanup_connection(websocket)

    async def _handle_message(self, websocket, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            message_type = data.get("type")

            if message_type == "audio_chunk":
                await self._handle_audio_chunk(websocket, data)
            elif message_type == "start_streaming":
                await self._handle_start_streaming(websocket)
            elif message_type == "stop_streaming":
                await self._handle_stop_streaming(websocket)
            elif message_type == "webrtc_offer":
                await self._handle_webrtc_offer(websocket, data)
            elif message_type == "webrtc_ice":
                await self._handle_webrtc_ice(websocket, data)
            elif message_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))
            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            logger.error("Invalid JSON message received")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def _handle_audio_chunk(self, websocket, data):
        """Handle incoming audio chunk"""
        try:
            # Decode base64 audio data
            audio_base64 = data.get("audio_data")
            if not audio_base64:
                return

            audio_bytes = base64.b64decode(audio_base64)
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16)

            # Add to streaming service
            streaming_service = self.connection_services.get(websocket)
            if streaming_service:
                await streaming_service.add_audio_chunk(audio_data)

        except Exception as e:
            logger.error(f"Error handling audio chunk: {e}")

    async def _handle_start_streaming(self, websocket):
        """Handle start streaming request"""
        try:
            streaming_service = self.connection_services.get(websocket)
            if streaming_service:
                await streaming_service.start_streaming()
                await websocket.send(
                    json.dumps({"type": "streaming_started", "status": "success"})
                )
                logger.info("Streaming started for connection")

        except Exception as e:
            logger.error(f"Error starting streaming: {e}")
            await websocket.send(
                json.dumps(
                    {"type": "streaming_started", "status": "error", "message": str(e)}
                )
            )

    async def _handle_stop_streaming(self, websocket):
        """Handle stop streaming request"""
        try:
            streaming_service = self.connection_services.get(websocket)
            if streaming_service:
                await streaming_service.stop_streaming()
                await websocket.send(
                    json.dumps({"type": "streaming_stopped", "status": "success"})
                )
                logger.info("Streaming stopped for connection")

        except Exception as e:
            logger.error(f"Error stopping streaming: {e}")

    async def _handle_webrtc_offer(self, websocket, data):
        """Handle incoming WebRTC SDP offer and set up peer connection"""
        try:
            sdp = data.get("sdp")
            if not sdp:
                return
            pc = RTCPeerConnection()
            self.ws_to_pc[websocket] = pc
            
            # Handle client-initiated data channel
            @pc.on("datachannel")
            async def on_datachannel(channel):
                if channel.label == "transcripts":
                    self.ws_to_data_channel[websocket] = channel
                    logger.info(f"Data channel '{channel.label}' received from client")

            # Inbound audio handler
            @pc.on("track")
            async def on_track(track):
                if track.kind != "audio":
                    return

                # Consume audio frames and feed into ASR pipeline as PCM16
                async def recv_audio():
                    # Resample all incoming audio to 16k mono s16 for ASR
                    resampler = av.audio.resampler.AudioResampler(
                        format="s16", layout="mono", rate=Config.SAMPLE_RATE
                    )
                    while True:
                        frame = await track.recv()
                        # Resample to 16k mono s16
                        try:
                            resampled = resampler.resample(frame)
                        except Exception:
                            # Fallback: convert without resample
                            resampled = frame

                        # resampled may be a list of frames; normalize to list
                        frames = (
                            resampled if isinstance(resampled, list) else [resampled]
                        )
                        streaming_service = self.connection_services.get(websocket)
                        for rf in frames:
                            # Convert to numpy int16
                            pcm = rf.to_ndarray()
                            if pcm.dtype != np.int16:
                                pcm = pcm.astype(np.int16, copy=False)
                            if streaming_service and streaming_service.is_recording:
                                await streaming_service.add_audio_chunk(pcm)

                asyncio.create_task(recv_audio())

            # Create a server-generated outbound audio track for TTS
            tts_track = TTSQueueAudioTrack()
            self.ws_to_tts_track[websocket] = tts_track
            pc.addTrack(tts_track)

            await pc.setRemoteDescription(
                RTCSessionDescription(sdp=sdp["sdp"], type=sdp["type"])
            )
            
            # Create an answer
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            
            # Reply with SDP answer
            resp = {
                "type": "webrtc_answer",
                "sdp": {
                    "sdp": pc.localDescription.sdp,
                    "type": pc.localDescription.type,
                },
            }
            await websocket.send(json.dumps(resp))

        except Exception as e:
            logger.error(f"Error handling WebRTC offer: {e}")

    async def _handle_webrtc_ice(self, websocket, data):
        """Handle remote ICE candidate from client"""
        try:
            candidate_dict = data.get("candidate")
            if candidate_dict is None:
                return

            # The aiortc library expects a specific object, not a raw dict.
            # We use the candidate_from_sdp helper for parsing.
            cand = candidate_from_sdp(candidate_dict["candidate"])
            cand.sdpMid = candidate_dict["sdpMid"]
            cand.sdpMLineIndex = candidate_dict["sdpMLineIndex"]

            pc = self.ws_to_pc.get(websocket)
            if pc:
                await pc.addIceCandidate(cand)

        except Exception as e:
            logger.error(f"Error handling ICE candidate: {e}")

    def _on_transcription(self, websocket):
        """Callback for when transcription is ready"""

        async def callback(transcribed_text: str):
            try:
                streaming_service = self.connection_services.get(websocket)
                if not streaming_service:
                    return

                source_lang = streaming_service.language
                target_lang = "en-US" if source_lang == "zh-CN" else "zh-CN"

                # Translate text
                translated_text = await self.translation_service.translate(
                    transcribed_text, source_lang
                )

                if not translated_text:
                    logger.warning("Translation resulted in empty text.")
                    return

                # Generate TTS audio (raw WAV bytes) in a separate thread
                loop = asyncio.get_running_loop()
                audio_bytes = await loop.run_in_executor(
                    None,
                    self.tts_service.save_audio_in_memory,
                    translated_text,
                    target_lang,
                )

                if audio_bytes:
                    # Enqueue to WebRTC TTS track if available; otherwise log warning
                    tts_track = self.ws_to_tts_track.get(websocket)
                    if tts_track and hasattr(tts_track, "enqueue_wav_bytes"):
                        await tts_track.enqueue_wav_bytes(audio_bytes)
                    else:
                        logger.warning("No WebRTC TTS track; unable to deliver audio")
                else:
                    logger.error("TTS service failed to generate audio.")

                # Send transcript over data channel if available
                channel = self.ws_to_data_channel.get(websocket)
                if channel and getattr(channel, "readyState", None) == "open":
                    payload = json.dumps(
                        {
                            "type": "transcript",
                            "transcribed_text": transcribed_text,
                            "translated_text": translated_text,
                            "source_language": source_lang,
                            "target_language": target_lang,
                        }
                    )
                    try:
                        channel.send(payload)
                        logger.debug("Sent transcript over data channel")
                    except Exception as e:
                        logger.warning(
                            f"Failed sending transcript on data channel: {e}"
                        )
                else:
                    logger.warning("No open data channel; unable to send transcript")

            except Exception as e:
                logger.error(f"Error in transcription callback: {e}")

        return callback

    async def _cleanup_connection(self, websocket):
        """Clean up connection resources"""
        try:
            # Stop streaming service
            streaming_service = self.connection_services.get(websocket)
            if streaming_service:
                await streaming_service.stop_streaming()
                del self.connection_services[websocket]

            # Remove from active connections
            self.active_connections.discard(websocket)

            # Close any peer connection
            pc = self.ws_to_pc.get(websocket)
            if pc:
                await pc.close()
                del self.ws_to_pc[websocket]
            # Close TTS track if present
            tts_track = self.ws_to_tts_track.get(websocket)
            if tts_track:
                try:
                    await tts_track.close()
                except Exception:
                    pass
                del self.ws_to_tts_track[websocket]

            # Close data channel if present
            channel = self.ws_to_data_channel.get(websocket)
            if channel:
                try:
                    channel.close()
                except Exception:
                    pass
                del self.ws_to_data_channel[websocket]

            logger.info(
                f"Connection cleaned up. Total connections: {len(self.active_connections)}"
            )

        except Exception as e:
            logger.error(f"Error cleaning up connection: {e}")

    async def start_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the WebSocket server and an HTTP health endpoint"""
        try:
            # Configure WebSocket server with ping/pong settings
            server = await websockets.serve(
                self.handle_connection,
                host,
                port,
                ping_interval=20,  # Send ping every 20 seconds
                ping_timeout=10,  # Wait 10 seconds for pong response
                close_timeout=10,  # Wait 10 seconds for close
            )

            logger.info(f"WebSocket streaming server started on ws://{host}:{port}")

            # Start aiohttp app for health check
            app = web.Application()

            async def healthz(_request):
                return web.json_response({"status": "ok"})

            app.router.add_get("/healthz", healthz)

            runner = web.AppRunner(app)
            await runner.setup()
            http_site = web.TCPSite(runner, host, port + 1)
            await http_site.start()
            logger.info(
                f"HTTP health endpoint started on http://{host}:{port+1}/healthz"
            )

            # Keep servers running
            await server.wait_closed()

        except Exception as e:
            logger.error(f"Error starting WebSocket server: {e}")
            raise


class TTSQueueAudioTrack(MediaStreamTrack):
    """Server-generated audio track that plays queued WAV bytes via aiortc."""

    kind = "audio"

    def __init__(self):
        super().__init__()
        self._queue: asyncio.Queue[av.AudioFrame] = asyncio.Queue()
        self._closed = False
        self._pts_offset = 0  # Running PTS offset for continuous stream

    async def enqueue_wav_bytes(self, wav_bytes: bytes):
        """Decode WAV bytes, offset timestamps, and enqueue for sending."""
        try:
            max_pts_in_file = 0
            with av.open(io.BytesIO(wav_bytes), format="wav") as container:
                resampler = av.audio.resampler.AudioResampler(
                    format="s16", layout="mono", rate=48000
                )
                for frame in container.decode(audio=0):
                    resampled_frames = resampler.resample(frame)
                    for r_frame in resampled_frames:
                        # Offset the PTS of each frame to make it continuous
                        r_frame.pts += self._pts_offset
                        max_pts_in_file = r_frame.pts  # Track the latest PTS
                        await self._queue.put(r_frame)

            # Update the offset for the next audio clip
            self._pts_offset = max_pts_in_file + 1

        except Exception as e:
            logger.error(f"Failed to enqueue WAV bytes: {e}")

    async def recv(self) -> av.AudioFrame:
        if self._closed:
            raise asyncio.CancelledError()
        frame = await self._queue.get()
        return frame


async def main():
    """Main function to start the WebSocket server"""
    # Get API key
    api_key = Config.GEMINI_API_KEY
    if not api_key:
        logger.error(
            "No Gemini API key found. Please set GEMINI_API_KEY environment variable."
        )
        return

    # Create and start server
    server = StreamingTranslationServer(api_key)
    await server.start_server(Config.HOST, Config.PORT)


if __name__ == "__main__":
    asyncio.run(main())
