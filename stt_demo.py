#!/usr/bin/env python3
"""
Demo script for testing the speech-to-text functionality
"""
from speech_to_text import SpeechToText

def process_speech(text: str):
    """Callback function to process recognized speech"""
    print(f"🤖 Processing: {text}")
    # Here you can add your AI model processing
    # For now, just echo the text
    print(f"💬 AI Response: I heard you say '{text}'")

def main():
    print("🦆 Quacky Speech-to-Text Demo")
    print("=" * 40)
    
    try:
        stt = SpeechToText()
    except Exception as e:
        print(f"❌ Failed to initialize speech recognition: {e}")
        print("Make sure you have installed the requirements:")
        print("pip install SpeechRecognition")
        return
    
    print("\nOptions:")
    print("1. Test microphone")
    print("2. Single recognition")
    print("3. Continuous listening")
    print("4. Quit")
    
    while True:
        choice = input("\n🎯 Enter your choice (1-4): ").strip()
        
        if choice == "1":
            print("\n🎤 Testing microphone...")
            stt.test_microphone()
        
        elif choice == "2":
            print("\n🎧 Single recognition mode")
            text = stt.listen_once()
            if text:
                process_speech(text)
        
        elif choice == "3":
            print("\n🔄 Continuous listening mode")
            stt.set_callback(process_speech)
            stt.listen_continuously()
            
            print("🎤 Listening continuously... Press Enter to stop")
            input()
            stt.stop_listening()
        
        elif choice == "4":
            stt.stop_listening()
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")

if __name__ == "__main__":
    main()