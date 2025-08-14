import speech_recognition as sr
import numpy as np
import sounddevice as sd
from typing import Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpeechRecognitionService:
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 4000
        self.recognizer.dynamic_energy_threshold = True

    def record_audio(self, duration: int = 5) -> Optional[np.ndarray]:
        """
        Record audio from microphone for specified duration
        """
        try:
            logger.info(f"Recording audio for {duration} seconds...")
            audio_data = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.int16,
            )
            sd.wait()
            logger.info("Audio recording completed")
            return audio_data
        except Exception as e:
            logger.error(f"Error recording audio: {e}")
            return None

    def record_audio_until_silence(
        self, silence_threshold: float = 0.01, silence_duration: float = 1.0
    ) -> Optional[np.ndarray]:
        """
        Record audio until silence is detected
        """
        try:
            logger.info("Recording audio until silence detected...")

            # Initialize audio stream
            audio_data = []
            silence_counter = 0
            silence_threshold_samples = int(silence_duration * self.sample_rate)

            with sd.InputStream(
                samplerate=self.sample_rate, channels=1, dtype=np.int16
            ) as stream:
                while True:
                    audio_chunk, _ = stream.read(self.chunk_size)
                    audio_data.append(audio_chunk)

                    # Check if audio is below threshold (silence)
                    if np.mean(np.abs(audio_chunk)) < silence_threshold * 32767:
                        silence_counter += 1
                    else:
                        silence_counter = 0

                    # If silence detected for specified duration, stop recording
                    if silence_counter >= silence_threshold_samples:
                        break

            if audio_data:
                # Concatenate all chunks
                full_audio = np.concatenate(audio_data, axis=0)
                logger.info("Audio recording completed (silence detected)")
                return full_audio
            else:
                logger.warning("No audio data recorded")
                return None

        except Exception as e:
            logger.error(f"Error recording audio until silence: {e}")
            return None

    def transcribe_audio(self, audio_data: np.ndarray, language: str) -> Optional[str]:
        """
        Transcribe audio data to text using Google Speech Recognition
        """
        try:
            # Convert numpy array to AudioData format
            audio_bytes = audio_data.tobytes()
            audio_data_sr = sr.AudioData(audio_bytes, self.sample_rate, 2)

            logger.info(f"Transcribing audio in {language}...")

            # Use Google Speech Recognition
            text = self.recognizer.recognize_google(audio_data_sr, language=language)
            logger.info(f"Transcription successful: {text}")
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
        