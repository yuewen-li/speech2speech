import pyttsx3
import sounddevice as sd
import numpy as np
import tempfile
import os
from typing import Optional
import logging
import base64


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TTSService:
    def __init__(self):
        """
        Initialize the text-to-speech service
        """
        self.engine = pyttsx3.init()
        self.setup_voice_properties()
        logger.info("TTS service initialized")

    def setup_voice_properties(self):
        """
        Configure voice properties for better quality
        """
        # Get available voices
        voices = self.engine.getProperty("voices")

        # Set default properties
        self.engine.setProperty("rate", 150)  # Speed of speech
        self.engine.setProperty("volume", 0.9)  # Volume level

        # Try to set appropriate voice for each language
        for voice in voices:
            if "chinese" in voice.name.lower() or "mandarin" in voice.name.lower():
                self.engine.setProperty("voice", voice.id)
                logger.info(f"Set Chinese voice: {voice.name}")
                break

        # If no Chinese voice found, use default
        if not any(
            "chinese" in voice.name.lower() or "mandarin" in voice.name.lower()
            for voice in voices
        ):
            logger.info("No Chinese voice found, using default voice")

    def save_audio_in_memory(self, text: str) -> Optional[str]:
        """
        Generate TTS audio and return it as a base64-encoded string (WAV format).
        """

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".wav", delete=True
            ) as temp_audio_file:
                self.engine.save_to_file(text, temp_audio_file.name)
                self.engine.runAndWait()
                temp_audio_file.seek(0)
                audio_bytes = temp_audio_file.read()
                audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
                return audio_base64
        except Exception as e:
            logger.error(f"Error saving audio to memory: {e}")
            return None

    def speak_text(self, text: str, language: str = "en") -> bool:
        """
        Convert text to speech and play it
        """
        try:
            logger.info(f"Speaking text in {language}: {text}")

            # Set appropriate voice based on language
            voices = self.engine.getProperty("voices")

            if language == "zh-CN":
                # Try to find Chinese voice
                for voice in voices:
                    if (
                        "chinese" in voice.name.lower()
                        or "mandarin" in voice.name.lower()
                    ):
                        self.engine.setProperty("voice", voice.id)
                        break
                # Adjust rate for Chinese (slightly slower)
                self.engine.setProperty("rate", 130)
            else:
                # Use English voice
                for voice in voices:
                    if "english" in voice.name.lower():
                        self.engine.setProperty("voice", voice.id)
                        break
                # Reset rate for English
                self.engine.setProperty("rate", 150)

            # Speak the text
            self.engine.say(text)
            self.engine.runAndWait()

            logger.info("Speech completed successfully")
            return True

        except Exception as e:
            logger.error(f"Error in text-to-speech: {e}")
            return False

    def save_audio_to_file(self, text: str, filename: str = None) -> Optional[str]:
        """
        Save text-to-speech audio to a file
        """
        try:
            if not filename:
                # Generate temporary filename
                temp_dir = tempfile.gettempdir()
                filename = os.path.join(temp_dir, f"tts_output_tmp.wav")

            logger.info(f"Saving audio to file: {filename}")

            # Set output file
            self.engine.setProperty("output", filename)

            # Speak and save
            self.engine.say(text)
            self.engine.runAndWait()

            # Reset output to default (speakers)
            self.engine.setProperty("output", None)

            logger.info(f"Audio saved successfully to: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Error saving audio to file: {e}")
            return None

    def get_available_voices(self) -> list:
        """
        Get list of available voices
        """
        voices = self.engine.getProperty("voices")
        voice_info = []

        for voice in voices:
            voice_info.append(
                {
                    "id": voice.id,
                    "name": voice.name,
                    "languages": voice.languages,
                    "gender": voice.gender,
                }
            )

        return voice_info

    def set_voice_properties(
        self, rate: int = None, volume: float = None, voice_id: str = None
    ):
        """
        Set voice properties
        """
        if rate is not None:
            self.engine.setProperty("rate", rate)
        if volume is not None:
            self.engine.setProperty("volume", volume)
        if voice_id is not None:
            self.engine.setProperty("voice", voice_id)

        logger.info("Voice properties updated")
