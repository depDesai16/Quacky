#!/usr/bin/env python3
"""
Quacky Full System - Combined AI Backend + Speech-to-Text
Starts AI server and connects speech-to-text
"""
import threading
import time
import sys
import os

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import components
try:
    from backend.server import run_server
    from backend.client import QuackyClient
    from speechToText.quacky_stt import QuackySpeechToText
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

# Global variables for AI connection
ai_client = None
chat_id = None

def load_system_prompt():
    with open("backend/system_prompt.txt", "r", encoding="utf-8") as f:
        return f.read()
    
def initialize_ai():
    """Initialize connection to AI backend"""
    global ai_client, chat_id
    
    print("🔗 Connecting to AI backend...")
    
    # Wait a bit more for server to fully start
    for i in range(10):
        try:
            ai_client = QuackyClient("http://localhost:8000")
            # Test connection
            health = ai_client.health()
            if health.get("status") == "ok":
                break
        except Exception:
            print(f"⏳ Waiting for AI backend... ({i+1}/10)")
            time.sleep(1)
    else:
        print("❌ Failed to connect to AI backend after 10 seconds")
        return False
    
    try:
        # Start a chat session with personality
        response = ai_client.start_chat(system=load_system_prompt())

        chat_id = response["chat_id"]
        print(f"✅ Connected to AI backend (Chat ID: {chat_id[:8]}...)")
        print(f"🤖 Using model: {response.get('model', 'unknown')}")
        return True
    except Exception as e:
        print(f"❌ Failed to start chat session: {e}")
        return False

def process_command(command: str):
    """Send command to AI and display response"""
    global ai_client, chat_id
    
    if not ai_client or not chat_id:
        print("❌ AI backend not connected")
        return
    
    try:
        print(f"🧠 Thinking...")
        response = ai_client.send_message(chat_id, command)
        if not isinstance(response, dict):
            print("❌ AI error: Unexpected response type")
            return
        if "error" in response:
            print(f"❌ AI error: {response['error']}")
            return
        ai_response = response.get("text", "")
        if not ai_response:
            print("❌ AI error: Empty response")
            return
        print(f"🦆 Quacky: {ai_response}")
        print()  # Add spacing for readability
        
    except Exception as e:
        print(f"❌ AI error: {e}")

def start_ai_server():
    """Start the AI server in background"""
    print("🚀 Starting AI backend server...")
    try:
        run_server()
    except Exception as e:
        print(f"❌ AI server error: {e}")

def main():
    print("🦆 Quacky Full System")
    print("=" * 40)
    print("Starting AI backend + Speech-to-Text")
    print("=" * 40)
    
    # Start AI server in background thread
    server_thread = threading.Thread(target=start_ai_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start and initialize AI connection
    if not initialize_ai():
        print("❌ Failed to initialize AI system")
        return
    
    # Initialize speech-to-text with microphone selection
    print("\n" + "=" * 40)
    print("Setting up Speech-to-Text")
    print("=" * 40)
    
    try:
        # Get microphone selection
        filtered_mics = QuackySpeechToText.list_microphones()
        
        if not filtered_mics:
            print("❌ No input microphones found. Using default.")
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
                        print(f"❌ Please enter a number between 1 and {len(filtered_mics)}, or 0 for default.")
                except ValueError:
                    print("❌ Please enter a valid number.")
        
        # Initialize speech-to-text
        stt = QuackySpeechToText(mic_index=mic_index)
        
        # Test microphone
        print("\nTesting microphone...")
        if not stt.test_microphone():
            print("❌ Microphone test failed. Please try a different microphone.")
            return
        
        # Set up callback and start listening
        stt.set_callback(process_command)
        
        print("\n" + "=" * 40)
        print("🎧 Quacky is listening...")
        print("Say 'Hey Quacky' followed by your command")
        print("Say 'quit' to exit")
        print("=" * 40)
        
        stt.start_listening()
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Shutting down Quacky...")
            stt.stop_listening()
            
    except Exception as e:
        print(f"❌ Speech-to-text error: {e}")

if __name__ == "__main__":
    main()
