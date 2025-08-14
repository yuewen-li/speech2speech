#!/usr/bin/env python3
"""
Test script for the Speech Translation Service (moved to tests/)
"""

import os
import sys
import time
import logging
from unittest.mock import patch
import tempfile
import numpy as np

# Ensure src is on path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
SRC_PATH = os.path.join(PROJECT_ROOT, 'src')
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from src.utils.config import Config
from src.service.speech_recognition_service import SpeechRecognitionService
from src.service.translation_service import TranslationService
from src.service.tts_service import TTSService
from src.service.speech_translation_service import SpeechTranslationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_config():
    assert Config.SAMPLE_RATE == 16000
    assert Config.CHUNK_SIZE == 1024
    assert Config.CHANNELS == 1


def test_speech_recognition_service_init():
    service = SpeechRecognitionService()
    assert service.sample_rate == 16000
    assert service.chunk_size == 1024
    assert service.recognizer is not None


def test_tts_service_basic():
    service = TTSService()
    assert service.engine is not None
    voices = service.get_available_voices()
    assert isinstance(voices, list)
    with patch('pyttsx3.Engine.runAndWait'):
        assert service.speak_text("Test", "en-US") is True


def test_translation_service_smoke():
    api_key = Config.GEMINI_API_KEY
    if not api_key:
        return  # skip in CI without key
    service = TranslationService(api_key)
    assert service.model is not None


def test_pipeline_info():
    api_key = Config.GEMINI_API_KEY or "dummy"
    st = SpeechTranslationService(api_key)
    info = st.get_translation_pipeline_info()
    assert 'speech_recognition' in info
    assert 'translation' in info
    assert 'tts' in info

