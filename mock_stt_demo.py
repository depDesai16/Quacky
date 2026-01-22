#!/usr/bin/env python3
"""
Mock demo to show expected speech-to-text output
This simulates what the real speech-to-text would look like
"""
import time
import threading
from typing import Optional, Callable

class MockSpeechToText:
    def __init__(self):
        self.is_listening = False
        self.callback = None
        print("🎤 Mock Speech-to-Text initialized")
        print("✅ Calibration complete!")
    
    def set_callback(self, callback: Callable[[str], None]):
        """Set a callback function to process recognized text"""
        self.callback = callback
    
    def listen_once(self) -> Optional[str]:
        """Simulate listening for a single phrase"""
        print("🎧 Listening for speech...")
        time.sleep(2)  # Simulate listening time
        
        # Simulate recognized text
        mock_phrases = [
            "Hello Quacky",
            "What's the weather like today",
            "Tell me a joke",
            "How are you doing",
            "Play some music"
        ]
        
        import random
        text = random.choice(mock_phrases)
        print(f"🎯 Processing speech...")
        time.sleep(1)
        print(f"✅ Recognized: {text}")
        return text
    
    def listen_continuously(self):
        """Start continuous listening simulation"""
        if self.is_listening:
            print("Already listening!")
            return
        
        self.is_listening = True
        self.listen_thread = threading.Thread(target=self._listen_worker)
        self.listen_thread.daemon = True
        self.listen_thread.start()
        print("🔄 Started continuous listening...")
    
    def _listen_worker(self):
        """Worker function for continuous listening simulation"""
        mock_phrases = [
            "Hey Quacky, how's it going",
            "What time is it",
            "Open my calendar",
            "Send a message to John",
            "What's on my todo list",
            "Play my favorite playlist",
            "Set a timer for 5 minutes"
        ]
        
        import random
        phrase_count = 0
        
        while self.is_listening and phrase_count < 5:  # Limit to 5 phrases for demo
            time.sleep(random.uniform(2, 4))  # Random intervals
            
            if not self.is_listening:
                break
                
            text = random.choice(mock_phrases)
            print(f"🎯 Recognized: {text}")
            
            if self.callback:
                self.callback(text)
            
            phrase_count += 1
    
    def stop_listening(self):
        """Stop continuous listening"""
        self.is_listening = False
        if hasattr(self, 'listen_thread'):
            self.listen_thread.join(timeout=2)
        print("⏹️  Stopped listening")
    
    def test_microphone(self):
        """Test microphone simulation"""
        print("🎤 Testing microphone...")
        time.sleep(1)
        print("✅ Microphone test successful! Heard: 'Testing one two three'")
        return True

def process_speech(text: str):
    """Callback function to process recognized speech"""
    print(f"🤖 Processing: {text}")
    
    # Simulate AI processing
    time.sleep(0.5)
    
    # Mock AI responses based on input
    if "weather" in text.lower():
        response = "The weather is sunny and 72°F today!"
    elif "joke" in text.lower():
        response = "Why don't scientists trust atoms? Because they make up everything! 🦆"
    elif "time" in text.lower():
        response = "It's currently 1:30 PM"
    elif "hello" in text.lower() or "hey" in text.lower():
        response = "Hello there! I'm Quacky, your unhinged desktop assistant! 🦆"
    else:
        response = f"I heard you say '{text}' - that's interesting!"
    
    print(f"💬 AI Response: {response}")

def main():
    print("🦆 Quacky Mock Speech-to-Text Demo")
    print("=" * 50)
    print("This shows what the real output would look like!")
    print("=" * 50)
    
    stt = MockSpeechToText()
    
    print("\nOptions:")
    print("1. Test microphone")
    print("2. Single recognition")
    print("3. Continuous listening (5 phrases)")
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
            
            print("🎤 Listening continuously... Press Enter to stop (or wait for 5 phrases)")
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