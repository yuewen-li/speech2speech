#!/usr/bin/env python3
"""
Main CLI application for Chinese-English Speech-to-Speech Translation Service
"""

import os
import sys
import time
from src.service.speech_translation_service import SpeechTranslationService
from src.utils.config import Config
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_banner():
    """Print application banner"""
    print("=" * 60)
    print("🎤 Chinese-English Speech-to-Speech Translation Service")
    print("=" * 60)
    print("Powered by Gemini API")
    print("=" * 60)

def print_menu():
    """Print main menu options"""
    print("\n📋 Available Options:")
    print("1. 🎤 Start Speech Translation (5 seconds)")
    print("2. 🎤 Start Speech Translation (until silence)")
    print("6. 📊 Show System Information")
    print("7. ⚙️  Configure Settings")
    print("8. ❌ Exit")
    print("-" * 60)

def print_language_menu():
    """Print language menu options"""
    print("\n📋 Available Options:")
    print("1. 🎤 Chinese")
    print("2. 🎤 English")
    print("-" * 60)

def get_gemini_api_key():
    """Get Gemini API key from environment or user input"""
    api_key = Config.GEMINI_API_KEY
    
    if not api_key:
        print("\n⚠️  No Gemini API key found in environment variables.")
        print("Please enter your Gemini API key:")
        api_key = input("API Key: ").strip()
        
        if not api_key:
            print("❌ API key is required to use the translation service.")
            sys.exit(1)
    
    return api_key


def show_system_info(service):
    """Show system information and configuration"""
    print("\n📊 System Information:")
    print("-" * 40)
    
    # Configuration
    print(f"Sample Rate: {Config.SAMPLE_RATE} Hz")
    print(f"Chunk Size: {Config.CHUNK_SIZE}")
    print(f"Channels: {Config.CHANNELS}")
    print(f"Host: {Config.HOST}")
    print(f"Port: {Config.PORT}")
    
    # Pipeline info
    pipeline_info = service.get_translation_pipeline_info()
    print(f"\nTranslation Provider: {pipeline_info['translation']['provider']}")
    print(f"Supported Languages: {', '.join(pipeline_info['translation']['supported_languages'])}")
    
    # Available voices
    voices = pipeline_info['tts']['available_voices']
    print(f"\nAvailable TTS Voices ({len(voices)}):")
    for i, voice in enumerate(voices[:5]):  # Show first 5 voices
        print(f"  {i+1}. {voice['name']} ({voice['gender']})")
    if len(voices) > 5:
        print(f"  ... and {len(voices) - 5} more voices")

def configure_settings():
    """Configure system settings"""
    print("\n⚙️  Configure Settings:")
    print("-" * 40)
    
    print("Current settings:")
    print(f"1. Sample Rate: {Config.SAMPLE_RATE} Hz")
    print(f"2. Chunk Size: {Config.CHUNK_SIZE}")
    print(f"3. Record Duration: 5 seconds")
    print(f"4. Silence Threshold: 0.01")
    print(f"5. Silence Duration: 1.0 seconds")
    
    print("\nNote: To change these settings permanently, edit the .env file")
    print("or modify the config.py file.")

def main():
    """Main application loop"""
    print_banner()
    
    # Get API key
    api_key = get_gemini_api_key()
    
    # Initialize service
    try:
        service = SpeechTranslationService(api_key)
        print("✅ Service initialized successfully!")
    except Exception as e:
        print(f"❌ Failed to initialize service: {e}")
        sys.exit(1)
    
    # Main loop
    while True:
        print_menu()
        
        try:
            choice = input("\nEnter your choice (1-8): ").strip()
            
            if choice == "1":
                print_language_menu()
                language_option = input("\nEnter your source language: ").strip()
                source_language = 'zh-CN' if language_option == '1' else 'en-US'
                print("\n🎤 Starting Speech Translation (5 seconds)...")
                print("Please speak in Chinese or English...")
                success = service.translate_speech_to_speech(source_language, record_duration=5)
                if success:
                    print("✅ Translation completed successfully!")
                else:
                    print("❌ Translation failed")
                    
            elif choice == "2":
                print_language_menu()
                language_option = input("\nEnter your source language: ").strip()
                source_language = 'zh-CN' if language_option == '1' else 'en-US'
                print("\n🎤 Starting Speech Translation (until silence)...")
                print("Please speak in Chinese or English...")
                print("(Translation will start automatically when silence is detected)")
                success = service.translate_speech_to_speech_until_silence(source_language)
                if success:
                    print("✅ Translation completed successfully!")
                else:
                    print("❌ Translation failed")
                
            elif choice == "6":
                show_system_info(service)
                
            elif choice == "7":
                configure_settings()
                
            elif choice == "8":
                print("\n👋 Thank you for using the Speech Translation Service!")
                print("Goodbye!")
                break
                
            else:
                print("❌ Invalid choice. Please enter a number between 1-8.")
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            continue
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            logger.error(f"Unexpected error in main loop: {e}")
            continue
        
        # Wait a moment before showing menu again
        time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
