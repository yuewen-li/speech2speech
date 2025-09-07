import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    TRANSLATION_SERVICE_MODEL = "gemini-2.0-flash-lite"

    LANGUAGE_ZH = os.getenv("LANGUAGE_ZH", "zh-CN")
    LANGUAGE_EN = os.getenv("LANGUAGE_EN", "en-US")

    SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "16000"))
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1024"))
    CHANNELS = int(os.getenv("CHANNELS", "1"))

    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))

    # Simple bearer token for WebSocket auth
    WS_TOKEN = os.getenv("WS_TOKEN", "SECRET_WS_TOKEN")

    # Optional ICE servers for WebRTC
    # Comma-separated URLs, e.g.:
    # "stun:stun.l.google.com:19302,stun:global.stun.twilio.com:3478"
    ICE_SERVERS = [
        s.strip() for s in os.getenv("ICE_SERVERS", "stun:stun.l.google.com:19302").split(",") if s.strip()
    ]

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
