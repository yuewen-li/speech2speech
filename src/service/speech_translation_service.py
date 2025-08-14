from src.service.speech_recognition_service import SpeechRecognitionService
from src.service.translation_service import TranslationService
from src.service.tts_service import TTSService
from src.utils.config import Config
from typing import Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpeechTranslationService:
    def __init__(self, gemini_api_key: str):
        """
        Initialize the speech translation service
        """
        self.speech_recognition = SpeechRecognitionService(
            sample_rate=Config.SAMPLE_RATE, chunk_size=Config.CHUNK_SIZE
        )
        self.translation = TranslationService(gemini_api_key)
        self.tts = TTSService()
        logger.info("Speech translation service initialized")

    def translate_speech_to_speech(
        self, source_language: str, record_duration: int = 5
    ) -> bool:
        """
        Main method: Record speech, translate, and speak the translation
        """
        try:
            # Step 1: Record audio
            logger.info("Starting speech-to-speech translation...")
            audio_data = self.speech_recognition.record_audio(record_duration)

            if audio_data is None:
                logger.error("Failed to record audio")
                return False

            # Transcribe audio
            transcribed_text = self.speech_recognition.transcribe_audio(
                audio_data, source_language
            )

            if transcribed_text is None:
                logger.error("Failed to transcribe audio")
                return False

            logger.info(f"Transcribed text: {transcribed_text}")

            # Step 3: Translate text
            translated_text = self.translation.auto_translate(
                transcribed_text, source_language
            )

            if translated_text is None:
                logger.error("Failed to translate text")
                return False

            logger.info(f"Translated text: {translated_text}")

            # Step 4: Convert translation to speech
            target_language = "en-US" if source_language == "zh-CN" else "zh-CN"
            success = self.tts.speak_text(translated_text, target_language)

            if success:
                logger.info("Speech-to-speech translation completed successfully")
                return True
            else:
                logger.error("Failed to convert translation to speech")
                return False

        except Exception as e:
            logger.error(f"Error in speech-to-speech translation: {e}")
            return False

    def translate_speech_to_speech_until_silence(
        self,
        source_language: str, 
        silence_threshold: float = 0.01,
        silence_duration: float = 1.0,
    ) -> bool:
        """
        Record speech until silence, then translate and speak
        """
        try:
            # Step 1: Record audio until silence
            logger.info("Recording speech until silence detected...")
            audio_data = self.speech_recognition.record_audio_until_silence(
                silence_threshold, silence_duration
            )

            if audio_data is None:
                logger.error("Failed to record audio")
                return False

            # Transcribe audio
            transcribed_text = self.speech_recognition.transcribe_audio(
                audio_data, source_language
            )

            if transcribed_text is None:
                logger.error("Failed to transcribe audio")
                return False

            logger.info(f"Transcribed text: {transcribed_text}")

            # Step 3: Translate text
            translated_text = self.translation.auto_translate(
                transcribed_text, source_language
            )

            if translated_text is None:
                logger.error("Failed to translate text")
                return False

            logger.info(f"Translated text: {translated_text}")

            # Step 4: Convert translation to speech
            target_language = "en-US" if source_language == "zh-CN" else "zh-CN"
            success = self.tts.speak_text(translated_text, target_language)

            if success:
                logger.info("Speech-to-speech translation completed successfully")
                return True
            else:
                logger.error("Failed to convert translation to speech")
                return False

        except Exception as e:
            logger.error(f"Error in speech-to-speech translation: {e}")
            return False

    def get_translation_pipeline_info(self) -> dict:
        """
        Get information about the translation pipeline
        """
        return {
            "speech_recognition": {
                "sample_rate": Config.SAMPLE_RATE,
                "chunk_size": Config.CHUNK_SIZE,
                "channels": Config.CHANNELS,
            },
            "translation": {
                "provider": "Gemini API",
                "supported_languages": ["zh-CN", "en-US"],
            },
            "tts": {"available_voices": self.tts.get_available_voices()},
        }

