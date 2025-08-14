"""
FastAPI server for Chinese-English Speech-to-Speech Translation Service
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import io
import tempfile
import os
import logging
from typing import Optional
import json

from src.service.speech_translation_service import SpeechTranslationService
from src.utils.config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Speech Translation API",
    description="Chinese-English Speech-to-Speech Translation Service using Gemini API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global service instance
translation_service: Optional[SpeechTranslationService] = None

@app.on_event("startup")
async def startup_event():
    """Initialize the translation service on startup"""
    global translation_service
    
    api_key = Config.GEMINI_API_KEY
    if not api_key:
        logger.error("No Gemini API key found. Please set GEMINI_API_KEY environment variable.")
        return
    
    try:
        translation_service = SpeechTranslationService(api_key)
        logger.info("Translation service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize translation service: {e}")

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Chinese-English Speech Translation API",
        "version": "1.0.0",
        "status": "running",
        "provider": "Gemini API",
        "supported_languages": ["zh-CN", "en-US"]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if translation_service is None:
        raise HTTPException(status_code=503, detail="Translation service not initialized")
    
    return {
        "status": "healthy",
        "service": "running",
        "timestamp": "2024-01-01T00:00:00Z"
    }

@app.post("/translate/speech-to-text")
async def speech_to_text(
    source_language: str,
    audio_file: UploadFile = File(...)
):
    """
    Convert speech audio to text
    """
    if translation_service is None:
        raise HTTPException(status_code=503, detail="Translation service not initialized")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            content = await audio_file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Load audio data
            import numpy as np
            import soundfile as sf
            
            audio_data, sample_rate = sf.read(temp_file_path)
            
            # Convert to int16 if needed
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
            
            # Transcribe
            transcribed_text = translation_service.speech_recognition.transcribe_audio(
                audio_data, source_language
            )
            
            if transcribed_text is None:
                raise HTTPException(status_code=400, detail="Failed to transcribe audio")
            
            return {
                "success": True,
                "transcribed_text": transcribed_text,
                "source_language": source_language,
                "sample_rate": sample_rate
            }
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except Exception as e:
        logger.error(f"Error in speech-to-text: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/translate/text-to-text")
async def translate_text(
    source_language: str,
    text: str = Form(...)
):
    """
    Translate text between Chinese and English
    """
    if translation_service is None:
        raise HTTPException(status_code=503, detail="Translation service not initialized")
    
    try:
        # Validate languages
        if source_language not in ["zh-CN", "en-US"]:
            raise HTTPException(status_code=400, detail="Invalid source language")
        
        # Translate
        if source_language == "zh-CN":
            translated_text = translation_service.translation.translate_zh_to_en(text)
        else:
            translated_text = translation_service.translation.translate_en_to_zh(text)
        
        if translated_text is None:
            raise HTTPException(status_code=500, detail="Translation failed")
        
        return {
            "success": True,
            "original_text": text,
            "translated_text": translated_text,
            "source_language": source_language
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in text translation: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/translate/speech-to-speech")
async def speech_to_speech(
    source_language: str,
    audio_file: UploadFile = File(...), 
):
    """
    Complete speech-to-speech translation pipeline
    """
    if translation_service is None:
        raise HTTPException(status_code=503, detail="Translation service not initialized")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            content = await audio_file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Load audio data
            import numpy as np
            import soundfile as sf
            
            audio_data, sample_rate = sf.read(temp_file_path)
            
            # Convert to int16 if needed
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
            
            target_language = "en-US" if source_language == "zh-CN" else "zh-CN"
            
            # Transcribe
            transcribed_text = translation_service.speech_recognition.transcribe_audio(
                audio_data, source_language
            )
            
            if transcribed_text is None:
                raise HTTPException(status_code=400, detail="Failed to transcribe audio")
            
            # Translate
            translated_text = translation_service.translation.auto_translate(
                transcribed_text, source_language
            )
            
            if translated_text is None:
                raise HTTPException(status_code=500, detail="Translation failed")
            
            # Generate speech
            audio_filename = translation_service.tts.save_audio_to_file(
                translated_text, target_language
            )
            
            if audio_filename is None:
                raise HTTPException(status_code=500, detail="Failed to generate speech")
            
            try:
                # Read generated audio file
                with open(audio_filename, "rb") as audio_file:
                    audio_content = audio_file.read()
                
                # Return audio as streaming response
                return StreamingResponse(
                    io.BytesIO(audio_content),
                    media_type="audio/wav",
                    headers={
                        "Content-Disposition": f"attachment; filename=translated_speech.wav"
                    }
                )
                
            finally:
                # Clean up generated audio file
                if os.path.exists(audio_filename):
                    os.unlink(audio_filename)
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in speech-to-speech: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/system/info")
async def get_system_info():
    """
    Get system information and configuration
    """
    if translation_service is None:
        raise HTTPException(status_code=503, detail="Translation service not initialized")
    
    try:
        pipeline_info = translation_service.get_translation_pipeline_info()
        
        return {
            "success": True,
            "system_info": {
                "sample_rate": Config.SAMPLE_RATE,
                "chunk_size": Config.CHUNK_SIZE,
                "channels": Config.CHANNELS,
                "host": Config.HOST,
                "port": Config.PORT
            },
            "pipeline_info": pipeline_info
        }
        
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/test/translation")
async def test_translation():
    """
    Test the translation service with sample texts
    """
    if translation_service is None:
        raise HTTPException(status_code=503, detail="Translation service not initialized")
    
    try:
        # Test Chinese to English
        test_zh = "你好，世界"
        translated_zh_to_en = translation_service.translation.translate_zh_to_en(test_zh)
        
        # Test English to Chinese
        test_en = "Hello, world"
        translated_en_to_zh = translation_service.translation.translate_en_to_zh(test_en)
        
        return {
            "success": True,
            "tests": {
                "chinese_to_english": {
                    "input": test_zh,
                    "output": translated_zh_to_en,
                    "success": translated_zh_to_en is not None
                },
                "english_to_chinese": {
                    "input": test_en,
                    "output": translated_en_to_zh,
                    "success": translated_en_to_zh is not None
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error in translation test: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=True,
        log_level="info"
    )
