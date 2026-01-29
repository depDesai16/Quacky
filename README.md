# Quacky
A repo for Quacky, the unhinged desktop assistant.

## Features
- Cross-platform speech-to-text recognition
- Continuous and single-shot listening modes
- Ready for AI model integration

## The Stack
- PyQt: UI and runtime.
- SpeechRecognition: Cross-platform speech-to-text.
- PyAudio: Audio input handling.

## Project Structure
```
Quacky/
|-- Server/
|----- Server stuff
├── app.py              # Main application
├── speech_to_text.py   # Speech-to-text module
├── stt_demo.py         # Demo script for testing STT
├── setup.py            # Cross-platform setup script
└── requirements.txt    # Python dependencies
```

## Setup

### Quick Start
1. Run the setup script:
   ```bash
   python setup.py
   ```

2. Test speech-to-text:
   ```bash
   python stt_demo.py
   ```

3. Start the main application:
   ```bash
   python app.py
   ```


### Manual Installation
```bash
pip install -r requirements.txt
```

### Platform-Specific Notes

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install python3-pyaudio portaudio19-dev
```

**macOS:**
```bash
brew install portaudio
```

**Windows:**
PyAudio should install automatically. If issues occur, install Visual C++ Build Tools.

## Server app
This app has two processes: the client and the local server. The client handles the speech to text, text to speech, and User Interface.The local server sends this input to the API, receives the response by Gemini, handles system actions, and returns the response to the client.  

## Usage


### Using the Speech-to-Text Module

```python
from speech_to_text import SpeechToText

# Initialize
stt = SpeechToText()

# Single recognition
text = stt.listen_once()

# Continuous listening with callback
def ai_callback(text: str):
    # Process with your AI model
    response = your_ai_model.process(text)
    print(f"AI Response: {response}")

stt.set_callback(ai_callback)
stt.listen_continuously()
```

The speech-to-text system provides two modes:

1. **Single Recognition**: Listen for one phrase and return the text
2. **Continuous Listening**: Keep listening and process speech in real-time

Additional stuff here
> Quacky will have a "Quacked out" mode where he acts silly
