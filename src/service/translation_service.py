import google.generativeai as genai
from typing import Optional
import logging
from src.utils.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TranslationService:
    def __init__(self, api_key: str):
        """
        Initialize the translation service with Gemini API
        """
        if not api_key:
            raise ValueError("Gemini API key is required")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(Config.TRANSLATION_SERVICE_MODEL)
        logger.info("Translation service initialized with Gemini API")

    def translate_zh_to_en(self, chinese_text: str) -> Optional[str]:
        """
        Translate Chinese text to English
        """
        try:
            prompt = Config.ZH_TO_EN_PROMPT.format(text=chinese_text)
            logger.info(f"Translating Chinese to English: {chinese_text}")

            response = self.model.generate_content(prompt)
            translation = response.text.strip()

            logger.info(f"Translation successful: {translation}")
            return translation

        except Exception as e:
            logger.error(f"Error translating Chinese to English: {e}")
            return None

    def translate_en_to_zh(self, english_text: str) -> Optional[str]:
        """
        Translate English text to Chinese
        """
        try:
            prompt = Config.EN_TO_ZH_PROMPT.format(text=english_text)
            logger.info(f"Translating English to Chinese: {english_text}")

            response = self.model.generate_content(prompt)
            translation = response.text.strip()

            logger.info(f"Translation successful: {translation}")
            return translation

        except Exception as e:
            logger.error(f"Error translating English to Chinese: {e}")
            return None

    def auto_translate(self, text: str, source_language: str) -> Optional[str]:
        """
        Automatically translate text based on detected source language
        """
        try:
            if source_language == "zh-CN":
                return self.translate_zh_to_en(text)
            elif source_language == "en-US":
                return self.translate_en_to_zh(text)
            else:
                logger.error(f"Unsupported source language: {source_language}")
                return None

        except Exception as e:
            logger.error(f"Error in auto translation: {e}")
            return None

    def batch_translate(self, texts: list, source_language: str) -> list:
        """
        Translate multiple texts in batch
        """
        translations = []
        for text in texts:
            translation = self.auto_translate(text, source_language)
            translations.append(translation)
        return translations

