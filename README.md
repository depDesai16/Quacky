# Quacky
A repo for Quacky, the unhinged desktop assistant with JARVIS-like voice interaction.

## Features
- **Voice-activated AI assistant** with "Hey Quacky" wake word detection
- **Continuous speech recognition** with automatic microphone selection
- **Gemini AI integration** for intelligent responses and tool usage
- **Cross-platform speech-to-text** recognition
- **System tool integration** (calendar, email, app launching)
- **Clean voice command interface** with quit functionality

## The Stack
- **Google Gemini AI**: Advanced language model with tool support
- **SpeechRecognition**: Cross-platform speech-to-text
- **PyAudio**: Audio input handling
- **HTTP Server**: Local AI backend with REST API
- **Python**: Core application logic

## Project Structure
```
Quacky/
├── backend/
│   ├── server.py           # Gemini AI backend server
│   ├── client.py           # HTTP client for AI communication
│   └── tools.py            # AI tools (calendar, email, apps)
├── speechToText/
│   ├── quacky_stt.py       # Main speech-to-text system
│   ├── speech_to_text.py   # Core STT module
│   └── setup.py            # STT setup script
├── quacky_full.py          # Complete integrated system
├── run_quacky.py           # Simple launcher
├── requirements.txt        # Python dependencies
└── .env                    # API keys (create from .env.example)
```

## Setup

### Quick Start
1. **Run setup once:**
   ```bash
   ./scripts/setup.sh
   ```

   On Windows PowerShell:
   ```powershell
   .\scripts\setup.ps1
   ```

2. **Add your API key in `.env`:**
   - Set `GEMINI_API_KEY=your_key_here`
   - `GOOGLE_API_KEY` also works

3. **Run Quacky:**
   ```bash
   python scripts/dev.py ui
   ```

   On Windows PowerShell:
   ```powershell
   python .\scripts\dev.py ui
   ```

4. **Check your local setup any time:**
   ```bash
   python scripts/dev.py doctor
   ```

5. **Install dependencies manually if you prefer:**
   ```bash
   pip install -r requirements.txt
   ```

6. **Run the full system with wrappers if you prefer:**
   ```bash
   ./scripts/run-ui.sh
   ```

   On Windows PowerShell:
   ```powershell
   .\scripts\run-ui.ps1
   ```

7. **Or run backend only:**
   ```bash
   ./scripts/run-server.sh
   ```

8. **Start talking:**
   - Say "Hey Quacky, what's the weather?"
   - Say "Hey Quacky, open my calendar"
   - Say "quit" to exit

### Alternative Launchers
```bash
# One command interface
python scripts/dev.py setup
python scripts/dev.py doctor
python scripts/dev.py server
python scripts/dev.py ui
python scripts/dev.py cli

# Wrapper scripts still work
./scripts/run-server.sh
./scripts/run-ui.sh
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

## Architecture

### Two-Process System
1. **Speech-to-Text Client**: Handles voice recognition and microphone input
2. **AI Backend Server**: Processes commands through Gemini AI with tool access

### Voice Interaction Flow
1. Continuous listening for "Hey Quacky" wake word
2. Capture command after wake word detection
3. Send to Gemini AI backend with tool access
4. Display AI response with personality
5. Return to listening for next command

## Usage

### Voice Commands
- **"Hey Quacky, [your command]"** - General AI interaction
- **"Hey Quacky, what's on my calendar?"** - Uses calendar tool
- **"Hey Quacky, email John about the meeting"** - Uses email tool
- **"Hey Quacky, open Spotify"** - Uses app launcher tool
- **"quit"** - Exit the system

### API Usage (Advanced)

```python
from backend.client import QuackyClient

# Connect to AI backend
client = QuackyClient("http://localhost:8000")

# Start chat with personality
chat = client.start_chat(
    system="You are Quacky, an unhinged but helpful assistant."
)

# Send message
response = client.send_message(chat["chat_id"], "What's the weather?")
print(response["text"])
```

## Tooling Guide (Gemini)
The server exposes Gemini tools declared in `backend/tools.py`. To encourage tool use, include a system instruction when you start a chat and then ask for actions in normal language.

### Example system instruction
Use this in `POST /chat/start` as the `system` field:
"You can use tools to: get calendar events, send email, and open apps. Use them when needed and summarize the result."

### Example prompts
- "What's on my calendar today?"
- "Email sam@example.com with subject 'Status' and say I'll send notes tonight."
- "Open Spotify."

### Forcing tool usage
If you want to be explicit, say:
- "Use the send_email tool to send an email to sam@example.com with subject 'Status' and body 'I'll send notes tonight.'"

## Development

### Adding New Tools
1. Add function to `backend/tools.py`
2. Import in `backend/server.py`
3. Add to `_TOOLS` list
4. Restart server

### Customizing Voice Recognition
- Modify wake words in `speechToText/quacky_stt.py`
- Adjust microphone sensitivity and timeout settings
- Add custom voice commands

## Personality
> Quacky is an unhinged but helpful desktop assistant with personality. He's conversational, witty, and adds character to responses while remaining useful.
The server exposes Gemini tools declared in `backend/tools.py`. To encourage tool use, include a system instruction when you start a chat and then ask for actions in normal language.

### Example system instruction
Use this in `POST /chat/start` as the `system` field:
“You can use tools to: get calendar events, send email, and open apps. Use them when needed and summarize the result.”

### Example prompts
- “What’s on my calendar today?”
- “Email sam@example.com with subject ‘Status’ and say I’ll send notes tonight.”
- “Open Spotify.”

### Forcing tool usage
If you want to be explicit, say:
- “Use the send_email tool to send an email to sam@example.com with subject ‘Status’ and body ‘I’ll send notes tonight.’”
