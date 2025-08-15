import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    # Gemini API Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    TRANSLATION_SERVICE_MODEL = 'gemini-2.0-flash-lite'

    # Speech Recognition Configuration
    LANGUAGE_ZH = os.getenv("LANGUAGE_ZH", "zh-CN")
    LANGUAGE_EN = os.getenv("LANGUAGE_EN", "en-US")

    # Audio Configuration
    SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "16000"))
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1024"))
    CHANNELS = int(os.getenv("CHANNELS", "1"))

    # Server Configuration
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8765"))

    # Translation prompts
    ZH_TO_EN_PROMPT = """
    You are a professional Chinese to English translator. 
    Translate the following Chinese text to natural, fluent English. 
    Maintain the original meaning and tone. Only return the English translation, nothing else.
    
    Chinese text: {text}
    """

    EN_TO_ZH_PROMPT = """
    You are a professional English to Chinese translator. 
    Translate the following English text to natural, fluent Chinese. 
    Maintain the original meaning and tone. Only return the Chinese translation, nothing else.
    
    English text: {text}
    """

