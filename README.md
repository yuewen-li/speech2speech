# Real-Time Speech-to-Speech Translation Service

This project provides a real-time, streaming speech-to-speech translation service. It captures audio from a user's microphone, transcribes it to text, translates it to a target language, and synthesizes the translated text back into speech, all in a continuous stream.

The service is built with a Python backend using WebSockets for low-latency communication and Google's Gemini API for translation.

## Features

- **Real-Time Streaming:** Audio is processed in chunks, allowing for low-latency transcription and translation as the user is speaking.
- **Bidirectional Language Support:** Currently supports English (`en-US`) and Chinese (`zh-CN`) translation in either direction.
- **Asynchronous Architecture:** Built with `asyncio` to handle multiple concurrent client connections efficiently.
- **Text-to-Speech (TTS) Output:** Plays the translated audio back to the user.
- **Command-Line Client:** A simple and easy-to-use client to connect to the service.

## How It Works

The application consists of two main components:

1.  **WebSocket Server:** The core of the service. It listens for client connections and manages the translation pipeline.
    - It receives audio chunks from the client.
    - Uses the `speech_recognition` library for initial transcription.
    - Sends the transcribed text to the Google Gemini API for translation.
    - Uses `pyttsx3` to convert the translated text back into speech audio.
    - Streams the generated audio back to the client.

2.  **WebSocket Client:** A command-line application that captures microphone audio and communicates with the server.
    - It streams the user's voice to the server in real-time.
    - It receives the translated audio from the server and plays it through the user's speakers.

## Setup and Installation

Follow these steps to set up and run the project locally.

### 1. Prerequisites

- Python 3.9+
- A Google Gemini API key

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

To run the service, you need to start the server first, and then run the client in a separate terminal.

### 1. Start the Server

Run the following command from the root of the project directory:

```bash
python -m src.websocket_server
```

You should see a log message indicating that the server has started:
`INFO:root:WebSocket streaming server started on ws://0.0.0.0:8000`

### 2. Start the Client

Open a new terminal, activate the virtual environment, and run the client:

```bash
python -m src.websocket_client
```

- The client will prompt you to select a source language (`en-US` or `zh-CN`).
- After selecting the language, press **Enter** to start streaming your voice.
- Speak into your microphone. The translated audio should play back shortly after.
- Press **Enter** again to stop streaming.
- Type `q` and press **Enter** to quit the client.
