import asyncio
import websockets
import json
import pyaudio
import wave
import base64
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StreamingTranslationClient:
    """WebSocket client for streaming translation"""

    def __init__(self, language: str, server_url: str = "ws://localhost:8765"):
        self.server_url = server_url
        self.websocket = None
        self.language = language

        # Audio setup
        self.audio = pyaudio.PyAudio()
        self.sample_rate = 16000
        self.chunk_size = 1024
        self.channels = 1
        self.format = pyaudio.paInt16

        # Streaming state
        self.is_streaming = False

    async def connect(self):
        """Connect to the WebSocket server"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            init_msg = json.dumps({"language": self.language})
            await self.websocket.send(init_msg)
            logger.info(f"Connected to {self.server_url}")

            # Start listening for server messages
            asyncio.create_task(self._listen_for_messages())

            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    async def start_streaming(self):
        """Start streaming audio to the server"""
        if not self.websocket:
            logger.error("Not connected to server")
            return False

        try:
            # Send start streaming message
            await self.websocket.send(json.dumps({"type": "start_streaming"}))

            self.is_streaming = True

            # Start audio stream
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
            )

            logger.info("Started streaming audio")

            # Stream audio chunks
            while self.is_streaming:
                try:
                    audio_data = stream.read(self.chunk_size)

                    # Send audio chunk
                    await self.websocket.send(
                        json.dumps(
                            {
                                "type": "audio_chunk",
                                "audio_data": base64.b64encode(audio_data).decode(
                                    "utf-8"
                                ),
                            }
                        )
                    )

                    await asyncio.sleep(0.1)  # Small delay

                except Exception as e:
                    logger.error(f"Error streaming audio: {e}")
                    break

            stream.stop_stream()
            stream.close()

        except Exception as e:
            logger.error(f"Error starting streaming: {e}")
            return False

    async def stop_streaming(self):
        """Stop streaming audio"""
        if self.is_streaming:
            self.is_streaming = False

            if self.websocket:
                await self.websocket.send(json.dumps({"type": "stop_streaming"}))

            logger.info("Stopped streaming audio")

    async def _listen_for_messages(self):
        """Listen for messages from the server"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                message_type = data.get("type")

                if message_type == "transcription":
                    print(f"Transcribed: {data.get('text')}")

                elif message_type == "translation_ready":
                    print(
                        f"Translation: {data.get('original_text')} → {data.get('translated_text')}"
                    )

                    # Play translated audio
                    audio_data = base64.b64decode(data.get("audio_data"))
                    await self._play_audio(audio_data)

                elif message_type == "streaming_started":
                    print("Streaming started successfully")

                elif message_type == "streaming_stopped":
                    print("Streaming stopped")

                elif message_type == "pong":
                    pass  # Ignore pong messages

                else:
                    logger.info(f"Received message: {data}")

        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection to server closed")
        except Exception as e:
            logger.error(f"Error listening for messages: {e}")

    async def _play_audio(self, audio_data: bytes):
        """Play audio data"""
        try:
            # Save to temporary file
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(audio_data)
                temp_filename = f.name

            # Play audio
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
            )

            # Read and play
            with wave.open(temp_filename, "rb") as wf:
                data = wf.readframes(wf.getnframes())
                stream.write(data)

            stream.stop_stream()
            stream.close()

            # Clean up
            os.unlink(temp_filename)

        except Exception as e:
            logger.error(f"Error playing audio: {e}")

    async def disconnect(self):
        """Disconnect from the server"""
        if self.websocket:
            await self.stop_streaming()
            await self.websocket.close()
            logger.info("Disconnected from server")

    def cleanup(self):
        """Clean up resources"""
        self.audio.terminate()


async def main():
    """Main function for the client"""
    client = StreamingTranslationClient()

    try:
        # Connect to server
        if await client.connect():
            print("Press Enter to start streaming, or 'q' to quit")

            while True:
                user_input = input("> ").strip().lower()

                if user_input == "q":
                    break
                elif user_input == "":
                    # Start streaming
                    print("Starting streaming... Press Enter again to stop")
                    await client.start_streaming()

                    # Wait for user to stop
                    input("Press Enter to stop streaming...")
                    await client.stop_streaming()
                else:
                    print(
                        "Invalid command. Press Enter to start streaming or 'q' to quit"
                    )

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        await client.disconnect()
        client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
