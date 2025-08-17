import asyncio
import websockets
import json
import logging
import numpy as np
import base64
from typing import Dict, Set
from src.service.streaming_speech_service import StreamingSpeechService
from src.service.translation_service import TranslationService
from src.service.tts_service import TTSService
from src.utils.config import Config

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

    async def handle_connection(self, websocket):
        """Handle new WebSocket connection"""
        try:
            # Add to active connections
            self.active_connections.add(websocket)
            init_msg = await websocket.recv()
            data = json.loads(init_msg)
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
                on_transcription=self._on_transcription(websocket),
                on_translation_ready=self._on_translation_ready(websocket),
            )

            self.connection_services[websocket] = streaming_service

            # Start streaming service
            await streaming_service.start_streaming()

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

    def _on_transcription(self, websocket):
        """Callback for when transcription is ready"""

        async def callback(transcribed_text: str):
            try:
                await websocket.send(
                    json.dumps(
                        {
                            "type": "transcription",
                            "text": transcribed_text,
                            "timestamp": asyncio.get_event_loop().time(),
                        }
                    )
                )
            except Exception as e:
                logger.error(f"Error sending transcription: {e}")

        return callback

    def _on_translation_ready(self, websocket):
        """Callback for when translation is ready"""

        async def callback(
            original_text: str, translated_text: str, source_lang: str, target_lang: str
        ):
            try:
                # Generate TTS audio
                audio_base64 = self.tts_service.save_audio_in_memory(translated_text)

                if audio_base64:
                    # Send translation with audio
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "translation_ready",
                                "original_text": original_text,
                                "translated_text": translated_text,
                                "source_language": source_lang,
                                "target_language": target_lang,
                                "audio_data": audio_base64,
                                "timestamp": asyncio.get_event_loop().time(),
                            }
                        )
                    )

            except Exception as e:
                logger.error(f"Error sending translation: {e}")

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

            logger.info(
                f"Connection cleaned up. Total connections: {len(self.active_connections)}"
            )

        except Exception as e:
            logger.error(f"Error cleaning up connection: {e}")

    async def start_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the WebSocket server"""
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

            # Keep server running
            await server.wait_closed()

        except Exception as e:
            logger.error(f"Error starting WebSocket server: {e}")
            raise


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
