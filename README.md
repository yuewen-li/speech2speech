# Chinese-English Speech-to-Speech Translation Service

A real-time speech translation service that converts spoken Chinese to English and vice versa using Google's Gemini API for translation and local speech recognition and text-to-speech services.

## 🌟 Features

- **Real-time Speech Recognition**: Automatically detects and transcribes Chinese and English speech
- **AI-Powered Translation**: Uses Gemini API for high-quality Chinese-English translation
- **Natural Text-to-Speech**: Converts translated text back to natural-sounding speech
- **Multiple Input Modes**: Fixed duration recording or silence-based recording
- **CLI Interface**: Interactive command-line application for easy testing
- **REST API**: FastAPI server for integration with other applications
- **Language Auto-Detection**: Automatically identifies the source language
- **Configurable Settings**: Adjustable audio parameters and service configuration

## 🏗️ Architecture

The service consists of three main components:

1. **Speech Recognition Service** (`speech_recognition_service.py`)
   - Records audio from microphone
   - Transcribes speech to text using Google Speech Recognition
   - Auto-detects language (Chinese/English)

2. **Translation Service** (`translation_service.py`)
   - Interfaces with Gemini API for translation
   - Handles Chinese ↔ English bidirectional translation
   - Optimized prompts for natural translations

3. **Text-to-Speech Service** (`tts_service.py`)
   - Converts translated text back to speech
   - Supports both Chinese and English voices
   - Configurable speech rate and voice selection

## 📋 Prerequisites

- Python 3.8 or higher
- Microphone access
- Speakers or headphones
- Gemini API key from Google AI Studio
- Internet connection for translation service

## 🚀 Installation

### 1. Clone the repository
```bash
git clone <repository-url>
cd tts
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables
Create a `.env` file in the project root:
```bash
# Copy the example file
cp env_example.txt .env

# Edit .env and add your Gemini API key
GEMINI_API_KEY=your_actual_api_key_here
```

### 4. Get a Gemini API key
1. Visit [Google AI Studio](https://aistudio.google.com/)
2. Create a new API key
3. Add it to your `.env` file

## 🎯 Usage

### CLI Application

Run the interactive command-line interface:
```bash
python main.py
```

**Available Options:**
1. **Start Speech Translation (5 seconds)**: Records for 5 seconds then translates
2. **Start Speech Translation (until silence)**: Records until silence is detected
3. **Test Speech Recognition**: Test the speech recognition component
4. **Test Translation Service**: Test the Gemini translation API
5. **Test Text-to-Speech**: Test the TTS component
6. **Show System Information**: Display configuration and available voices
7. **Configure Settings**: View current settings
8. **Exit**: Close the application

### API Server

Start the FastAPI server:
```bash
python api_server.py
```

The server will start on `http://localhost:8000`

**API Endpoints:**

- `GET /` - Service information
- `GET /health` - Health check
- `POST /translate/speech-to-text` - Convert speech to text
- `POST /translate/text-to-text` - Translate text between languages
- `POST /translate/speech-to-speech` - Complete speech-to-speech translation
- `GET /system/info` - System configuration information
- `POST /test/translation` - Test translation service

**API Documentation:**
- Interactive docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Your Gemini API key | Required |
| `LANGUAGE_ZH` | Chinese language code | `zh-CN` |
| `LANGUAGE_EN` | English language code | `en-US` |
| `SAMPLE_RATE` | Audio sample rate | `16000` |
| `CHUNK_SIZE` | Audio chunk size | `1024` |
| `CHANNELS` | Audio channels | `1` |
| `HOST` | API server host | `0.0.0.0` |
| `PORT` | API server port | `8000` |

### Audio Settings

- **Sample Rate**: 16kHz (recommended for speech recognition)
- **Chunk Size**: 1024 samples (adjustable for latency vs. quality)
- **Channels**: Mono (1 channel) for optimal speech recognition

## 📱 Example Usage Scenarios

### 1. Real-time Conversation Translation
```python
from speech_translation_service import SpeechTranslationService

service = SpeechTranslationService("your_api_key")

# Translate Chinese speech to English
success = service.translate_speech_to_speech(record_duration=5)
```

### 2. API Integration
```python
import requests

# Upload audio file and get translation
with open("speech.wav", "rb") as audio_file:
    response = requests.post(
        "http://localhost:8000/translate/speech-to-speech",
        files={"audio_file": audio_file}
    )
    
# Save translated audio
with open("translated_speech.wav", "wb") as output_file:
    output_file.write(response.content)
```

### 3. Text Translation Only
```python
from translation_service import TranslationService

translator = TranslationService("your_api_key")
english_text = translator.translate_zh_to_en("你好，世界")
print(english_text)  # Output: Hello, world
```

## 🚀 Performance Optimization

### Reducing Latency

1. **Lower Chunk Size**: Reduce `CHUNK_SIZE` in config for faster processing
2. **GPU Acceleration**: Use GPU if available for faster inference
3. **Streaming**: Implement streaming audio processing for real-time translation
4. **Caching**: Cache common translations to reduce API calls

### Improving Quality

1. **Higher Sample Rate**: Increase sample rate for better audio quality
2. **Noise Reduction**: Implement audio preprocessing for cleaner input
3. **Voice Selection**: Choose appropriate voices for each language
4. **Prompt Engineering**: Optimize Gemini prompts for better translations

## 🐛 Troubleshooting

### Common Issues

1. **"No module named 'pyaudio'"**
   - Install system dependencies: `sudo apt-get install portaudio19-dev` (Linux)
   - On Windows: `pip install pyaudio`

2. **"Speech recognition could not understand audio"**
   - Check microphone permissions
   - Ensure clear speech and minimal background noise
   - Adjust `energy_threshold` in speech recognition service

3. **"Translation failed"**
   - Verify Gemini API key is correct
   - Check internet connection
   - Ensure API quota is not exceeded

4. **"No Chinese voice found"**
   - Install additional language packs on your system
   - The service will fall back to default voice

### Debug Mode

Enable detailed logging by modifying the logging level in any service file:
```python
logging.basicConfig(level=logging.DEBUG)
```

## 🔮 Future Enhancements

- **Streaming Translation**: Real-time translation without waiting for silence
- **Multiple Language Support**: Add more languages beyond Chinese/English
- **Voice Cloning**: Personalized voice synthesis
- **Offline Mode**: Local translation models for privacy
- **Web Interface**: Browser-based UI for easier access
- **Mobile App**: Native mobile applications
- **Batch Processing**: Process multiple audio files simultaneously

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Support

If you encounter any issues or have questions:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Open an issue on the repository
4. Check the API documentation at `/docs` endpoint

## 🙏 Acknowledgments

- Google Gemini API for translation services
- Google Speech Recognition for speech-to-text
- PyAudio and SoundDevice for audio processing
- FastAPI for the web server framework
- The open-source community for various audio processing libraries
