import pyttsx3
import tempfile
import os
from typing import Optional
import logging
import base64
import pythoncom


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TTSService:
    def _initialize_engine(self, language: str = "en"):
        """Initializes and configures a new pyttsx3 engine."""
        engine = pyttsx3.init()

        # Set appropriate voice based on language
        voices = engine.getProperty("voices")
        if language == "zh-CN":
            for voice in voices:
                if "chinese" in voice.name.lower() or "mandarin" in voice.name.lower():
                    engine.setProperty("voice", voice.id)
                    break
            engine.setProperty("rate", 130)
        else:
            for voice in voices:
                if "english" in voice.name.lower():
                    engine.setProperty("voice", voice.id)
                    break
            engine.setProperty("rate", 150)

        engine.setProperty("volume", 0.9)
        return engine

    def save_audio_in_memory(self, text: str, language: str = "en") -> Optional[str]:
        """
        Generate TTS audio and return it as a base64-encoded string (WAV format).
        This method is thread-safe by creating a new engine for each call.
        """
        pythoncom.CoInitialize()
        temp_filename = ""
        try:
            engine = self._initialize_engine(language)

            # Create a temporary file that pyttsx3 can write to
            with tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False
            ) as temp_audio_file:
                temp_filename = temp_audio_file.name

            engine.save_to_file(text, temp_filename)
            engine.runAndWait()

            # Stop the engine event loop
            engine.stop()

            # Read the generated audio file
            with open(temp_filename, "rb") as f:
                audio_bytes = f.read()

            # audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            return audio_bytes
        except Exception as e:
            logger.error(f"Error saving audio to memory: {e}")
            return None
        finally:
            # Clean up the temporary file
            if temp_filename and os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def speak_text(self, text: str, language: str = "en") -> bool:
        """
        Convert text to speech and play it.
        """
        try:
            logger.info(f"Speaking text in {language}: {text}")
            engine = self._initialize_engine(language)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
            logger.info("Speech completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error in text-to-speech: {e}")
            return False
