# Real-Time Speech-to-Speech Translation Service

This project provides a real-time, streaming speech-to-speech translation service. It captures audio from a user's microphone, transcribes it to text, translates it to a target language, and synthesizes the translated text back into speech, all in a continuous stream.

The service is built with a Python backend using WebRTC for real-time audio streaming and WebSockets for signaling, with Google's Gemini API for translation.

## Features

- **Real-Time Streaming:** Audio is processed in chunks, allowing for low-latency transcription and translation as the user is speaking.
- **Bidirectional Language Support:** Currently supports English (`en-US`) and Chinese (`zh-CN`) translation in either direction.
- **WebRTC Audio Streaming:** Uses WebRTC for high-quality, low-latency audio streaming between client and server.
- **Asynchronous Architecture:** Built with `asyncio` to handle multiple concurrent client connections efficiently.
- **Text-to-Speech (TTS) Output:** Plays the translated audio back to the user via WebRTC audio tracks.
- **Real-Time Transcripts:** Displays both original and translated text in real-time via WebRTC data channels.
- **Web-Based Client:** A modern web-based client that runs in the browser with full WebRTC support.
- **Flexible Response Modes:** Choose between receiving only transcripts or both transcripts and audio output.

## How It Works

The application consists of two main components:

1.  **WebRTC + WebSocket Server:** The core of the service. It manages WebRTC peer connections and the translation pipeline.
    - Establishes WebRTC peer connections with clients for real-time audio streaming.
    - Receives audio tracks from the client via WebRTC.
    - Uses streaming speech recognition for real-time transcription.
    - Sends the transcribed text to the Google Gemini API for translation.
    - Uses TTS service to convert the translated text back into speech audio.
    - Streams the generated audio back to the client via WebRTC audio tracks.
    - Sends transcripts (original and translated text) via WebRTC data channels.

2.  **Web-Based Client:** A modern browser-based client with full WebRTC support.
    - Captures microphone audio and streams it to the server via WebRTC.
    - Receives translated audio from the server and plays it through the user's speakers.
    - Displays real-time transcripts of both original and translated text.
    - Uses WebSockets for signaling (SDP offers/answers and ICE candidates).

## Setup and Installation

Follow these steps to set up and run the project locally.

### 1. Prerequisites

- Python 3.9+
- A Google Gemini API key
- A modern web browser with WebRTC support (Chrome, Firefox, Safari, Edge)
- Microphone access for audio input

### 2. Create a Virtual Environment

It is highly recommended to use a virtual environment to manage dependencies.

```bash
# For Windows
python -m venv .venv
.venv\Scripts\activate

# For macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

Install all the required Python packages from the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

The application requires a Google Gemini API key. Create a `.env` file in the root of the project directory:

```
touch .env
```

Open the `.env` file and add your API key:

```
GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
```

## Usage

To run the service, you need to start the server first, and then open the web client in your browser.

### 1. Start the Server

Run the following command from the root of the project directory:

```bash
python -m src.websocket_server
```

You should see log messages indicating that the server has started:
- `INFO:root:WebSocket streaming server started on ws://0.0.0.0:8000`
- `INFO:root:HTTP health endpoint started on http://0.0.0.0:8001/healthz`

### 2. Open the Web Client

Open your web browser and navigate to the client file:

```bash
# Open the HTML file directly in your browser
open src/webrtc_browser_client.html
```

### 3. Using the Client

1. **Select Language:** Choose your source language (`en-US` for English or `zh-CN` for Chinese) from the dropdown.
2. **Choose Response Mode:** Select your preferred response mode:
   - **Both Transcript & Audio:** You'll receive both text transcripts and audio playback (default)
   - **Transcript Only:** You'll only receive text transcripts without audio playback
3. **Start Translation:** Click the "Start" button to begin the WebRTC connection and start streaming.
4. **Speak:** Speak into your microphone. You'll see:
   - Real-time transcripts of your speech and the translation in the UI
   - Translated audio playing through your speakers (if "Both Transcript & Audio" mode is selected)
5. **Stop:** Close the browser tab or refresh the page to stop the session.

### Architecture Notes

- **WebRTC Audio Tracks:** Handle real-time audio streaming between client and server
- **WebRTC Data Channels:** Deliver transcript data for real-time text display
- **WebSocket Signaling:** Manages WebRTC connection setup (SDP offers/answers, ICE candidates)
- **Health Check:** The server also runs an HTTP health endpoint at `http://localhost:8001/healthz`

## Technical Architecture

### WebRTC Integration

The application uses WebRTC for real-time communication:

- **Audio Tracks:** Client microphone audio is streamed to the server via WebRTC audio tracks
- **TTS Audio:** Server-generated translated audio is streamed back via WebRTC audio tracks
- **Data Channels:** Real-time transcripts are sent via WebRTC data channels for instant UI updates
- **Signaling:** WebSocket handles SDP offer/answer exchange and ICE candidate negotiation

### Key Components

- **`websocket_server.py`:** Main server handling WebRTC peer connections and translation pipeline
- **`webrtc_browser_client.html`:** Web-based client with WebRTC audio and data channel support
- **`transcription_service.py`:** Streaming speech recognition service
- **`translation_service.py`:** Google Gemini API integration for text translation
- **`tts_service.py`:** Text-to-speech audio generation service

### Data Flow

1. Client captures microphone audio → WebRTC audio track → Server
2. Server processes audio → Speech recognition → Translation → TTS
3. Server sends translated audio → WebRTC audio track → Client speakers
4. Server sends transcripts → WebRTC data channel → Client UI display
