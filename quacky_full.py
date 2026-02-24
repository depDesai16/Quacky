#!/usr/bin/env python3
"""
Quacky Full System - Combined AI Backend + Speech-to-Text
Starts AI server and connects speech-to-text
"""
import threading
import time
import sys
import os
import base64
import shutil
import subprocess
import tempfile
from assistant_identity import get_assistant_name, get_wake_words

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from backend.server import run_server
    from backend.client import QuackyClient
    from speechToText.quacky_stt import QuackySpeechToText
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

ai_client = None
chat_id = None
current_audio_process = None  # Track the currently playing audio
ASSISTANT_NAME = get_assistant_name()
WAKE_WORDS = get_wake_words(ASSISTANT_NAME)


def _play_mp3_bytes(audio_bytes: bytes) -> bool:
    """Play MP3 bytes with the first available system player."""
    global current_audio_process
    
    if not audio_bytes:
        return False

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp.write(audio_bytes)
        audio_path = tmp.name

    player_candidates = [
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", audio_path],
        ["mpg123", "-q", audio_path],
        ["afplay", audio_path],
    ]

    try:
        for cmd in player_candidates:
            if shutil.which(cmd[0]):
                current_audio_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                current_audio_process.wait()
                current_audio_process = None
                return True
        return False
    finally:
        try:
            os.remove(audio_path)
        except OSError:
            pass


def stop_audio():
    """Stop currently playing audio"""
    global current_audio_process
    if current_audio_process and current_audio_process.poll() is None:
        current_audio_process.terminate()
        try:
            current_audio_process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            current_audio_process.kill()
        current_audio_process = None

def load_system_prompt():
    with open("backend/system_prompt.txt", "r", encoding="utf-8") as f:
        prompt = f.read()
    # Keep the default prompt template but reflect the configured assistant name.
    return prompt.replace("Quacky", ASSISTANT_NAME)
    
def initialize_ai():
    """Initialize connection to AI backend"""
    global ai_client, chat_id
    
    print("Connecting to AI backend...")
    
    for i in range(10):
        try:
            ai_client = QuackyClient("http://localhost:8000")
            health = ai_client.health()
            if health.get("status") == "ok":
                break
        except Exception:
            print(f"Waiting for AI backend... ({i+1}/10)")
            time.sleep(1)
    else:
        print("Failed to connect to AI backend after 10 seconds")
        return False
    
    try:
        response = ai_client.start_chat(system=load_system_prompt())
        chat_id = response["chat_id"]
        print(f"Connected to AI backend (Chat ID: {chat_id[:8]}...)")
        print(f"Using model: {response.get('model', 'unknown')}")
        return True
    except Exception as e:
        print(f"Failed to start chat session: {e}")
        return False

def process_command(command: str):
    """Send command to AI and display response"""
    global ai_client, chat_id
    
    # Stop any currently playing audio when new command comes in
    stop_audio()
    
    if not ai_client or not chat_id:
        print("AI backend not connected")
        return
    
    try:
        print(f"Thinking...")
        response = ai_client.send_message(chat_id, command, tts=True)
        if not isinstance(response, dict):
            print("AI error: Unexpected response type")
            return
        if "error" in response:
            print(f"AI error: {response['error']}")
            return
        ai_response = response.get("text", "")
        if not ai_response:
            print("AI error: Empty response")
            return
        print(f"{ASSISTANT_NAME}: {ai_response}")
        audio_b64 = response.get("audio_base64")
        if audio_b64:
            try:
                audio_bytes = base64.b64decode(audio_b64)
                played = _play_mp3_bytes(audio_bytes)
                if not played:
                    print("(TTS audio returned, but no local MP3 player was found.)")
            except Exception as audio_err:
                print(f"(TTS playback error: {audio_err})")
        elif response.get("tts_error"):
            print(f"(TTS unavailable: {response['tts_error']})")
        print()
        
    except Exception as e:
        print(f"AI error: {e}")

def start_ai_server():
    """Start the AI server in background"""
    print("Starting AI backend server...")
    try:
        run_server()
    except Exception as e:
        print(f"AI server error: {e}")

def main():
    print(f"{ASSISTANT_NAME} Full System")
    print("=" * 40)
    print("Starting AI backend + Speech-to-Text")
    print("=" * 40)
    
    server_thread = threading.Thread(target=start_ai_server, daemon=True)
    server_thread.start()
    
    if not initialize_ai():
        print("Failed to initialize AI system")
        return
    
    print("\n" + "=" * 40)
    print("Setting up Speech-to-Text")
    print("=" * 40)
    
    try:
        filtered_mics = QuackySpeechToText.list_microphones()
        
        if not filtered_mics:
            print("No input microphones found. Using default.")
            mic_index = None
        else:
            print("\nSelect microphone:")
            print("0: Use default microphone")
            
            while True:
                try:
                    choice = input(f"\nEnter microphone number 1-{len(filtered_mics)} (or 0 for default): ").strip()
                    if choice == "" or choice == "0":
                        mic_index = None
                        break
                    choice = int(choice)
                    if 1 <= choice <= len(filtered_mics):
                        mic_index = filtered_mics[choice - 1][0]
                        break
                    else:
                        print(f"Please enter a number between 1 and {len(filtered_mics)}, or 0 for default.")
                except ValueError:
                    print("Please enter a valid number.")
        
        stt = QuackySpeechToText(
            mic_index=mic_index,
            assistant_name=ASSISTANT_NAME,
            wake_words=WAKE_WORDS,
        )
        stt.set_callback(process_command)
        stt.set_stop_callback(stop_audio)  # Set callback to stop audio on speech detection
        
        print("\n" + "=" * 40)
        print(f"{ASSISTANT_NAME} is listening...")
        print(f"Say '{WAKE_WORDS[0]}' followed by your command")
        print("Say 'quit' to exit")
        print("=" * 40)
        
        stt.start_listening()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\nShutting down {ASSISTANT_NAME}...")
            stt.stop_listening()
            
    except Exception as e:
        print(f"Speech-to-text error: {e}")

if __name__ == "__main__":
    main()
