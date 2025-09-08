import asyncio
import numpy as np
import speech_recognition as sr
import logging
from typing import Optional, Callable
from collections import deque

logger = logging.getLogger(__name__)


class StreamingSpeechService:
    """
    Real-time streaming speech recognition service with VAD-based end-of-utterance detection.
    """

    def __init__(
        self,
        language: str,
        sample_rate: int = 16000,
        chunk_size: int = 1024,
        buffer_duration: float = 3.5,
        vad_silence_ms: int = 700,
        vad_min_utterance_ms: int = 300,
        vad_max_utterance_ms: int = 15000,
        vad_rms_threshold: float = 300.0,
    ):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.buffer_duration = buffer_duration
        self.buffer_size = int(sample_rate * buffer_duration)
        self.language = language

        # Audio buffer for streaming (utterance-level; unlimited, we flush via VAD)
        self.audio_buffer = deque()
        self.is_recording = False
        self.audio_queue = asyncio.Queue()

        # Speech recognition setup
        self.recognizer = sr.Recognizer()
        # minimum audio energy to consider for recording
        self.recognizer.energy_threshold = 1000
        self.recognizer.dynamic_energy_threshold = False

        # VAD parameters
        self.vad_silence_ms = vad_silence_ms
        self.vad_min_utterance_ms = vad_min_utterance_ms
        self.vad_max_utterance_ms = vad_max_utterance_ms
        # Simple RMS threshold for voiced/unvoiced decision (int16 amplitude)
        self.vad_rms_threshold = vad_rms_threshold

        # Runtime VAD state
        self.current_utterance_samples = 0
        self.current_silence_ms = 0

        # Callbacks
        self.on_transcription = None

    def set_callbacks(self, on_transcription: Callable = None):
        """Set callback functions for real-time events"""
        self.on_transcription = on_transcription

    async def start_streaming(self):
        """Start the streaming recognition service"""
        self.is_recording = True
        self.recognition_task = asyncio.create_task(self._recognition_worker())
        logger.info("Streaming speech recognition started")

    async def stop_streaming(self):
        """Stop the streaming recognition service"""
        self.is_recording = False
        if self.recognition_task:
            await self.recognition_task
        logger.info("Streaming speech recognition stopped")

    async def add_audio_chunk(self, audio_chunk: np.ndarray):
        """Add audio chunk to the streaming buffer"""
        if self.is_recording:
            await self.audio_queue.put(audio_chunk)

    async def _recognition_worker(self):
        """Background worker for continuous recognition"""
        while self.is_recording:
            try:
                # Get audio chunk from queue with a timeout
                audio_chunk = await asyncio.wait_for(
                    self.audio_queue.get(), timeout=0.1
                )

                # Add to utterance buffer
                flat = audio_chunk.flatten()
                self.audio_buffer.extend(flat)
                self.current_utterance_samples += len(flat)

                # Compute simple RMS to detect speech vs silence
                rms = float(np.sqrt(np.mean(flat.astype(np.float32) ** 2)))
                chunk_ms = int(1000 * len(flat) / self.sample_rate)
                if rms >= self.vad_rms_threshold:
                    # voiced
                    self.current_silence_ms = 0
                else:
                    # silence
                    self.current_silence_ms += chunk_ms

                # Trigger transcription if sufficient silence after speech
                utterance_ms = int(1000 * self.current_utterance_samples / self.sample_rate)
                if (
                    self.current_silence_ms >= self.vad_silence_ms
                    and utterance_ms >= self.vad_min_utterance_ms
                ) or utterance_ms >= self.vad_max_utterance_ms:
                    await self._process_audio_buffer()

            except asyncio.TimeoutError:
                # Continue to check if recording has stopped
                continue
            except Exception as e:
                logger.error(f"Error in recognition worker: {e}")

        # Process any remaining audio in the queue
        while not self.audio_queue.empty():
            audio_chunk = self.audio_queue.get_nowait()
            self.audio_buffer.extend(audio_chunk.flatten())

        # Process the final buffer if there's anything in it
        if len(self.audio_buffer) > 0:
            await self._process_audio_buffer()

    async def _process_audio_buffer(self):
        """Process the current audio buffer for recognition"""
        try:
            # Convert buffer to numpy array
            audio_data = np.array(list(self.audio_buffer), dtype=np.int16)
            if audio_data.size == 0:
                return

            # Try to transcribe
            transcribed_text = self._transcribe_audio(audio_data)
            if transcribed_text:
                # Call callbacks
                if self.on_transcription:
                    await self.on_transcription(transcribed_text)

        except Exception as e:
            logger.error(f"Error processing audio buffer: {e}")
        finally:
            # Clear buffer and reset VAD state after processing
            self.audio_buffer.clear()
            self.current_utterance_samples = 0
            self.current_silence_ms = 0

    def _transcribe_audio(self, audio_data: np.ndarray) -> Optional[str]:
        """Transcribe audio data"""
        try:
            # Ensure audio data is in 16-bit format
            audio_data = audio_data.astype(np.int16)

            audio_bytes = audio_data.tobytes()
            audio_data_sr = sr.AudioData(audio_bytes, self.sample_rate, 2)
            text = self.recognizer.recognize_google(
                audio_data_sr, language=self.language
            )
            return text
        except sr.UnknownValueError:
            logger.warning("Speech recognition could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(
                f"Could not request results from speech recognition service: {e}"
            )
            return None
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None
