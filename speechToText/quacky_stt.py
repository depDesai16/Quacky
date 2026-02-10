#!/usr/bin/env python3
"""
Quacky Speech-to-Text - Clean implementation
Listens for "Hey Quacky" wake word, then captures and processes speech
"""
import speech_recognition as sr
import threading
import time
import os
import sys
import pyaudio
from typing import Optional, Callable

# Ensure we can find modules regardless of where script is run from
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

class QuackySpeechToText:
    def __init__(self, mic_index=None):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_listening = False
        self.wake_word = "hey quacky"
        self.callback = None
        
        # Initialize microphone
        try:
            if mic_index is not None:
                try:
                    self.microphone = sr.Microphone(device_index=mic_index)
                    print(f"🎤 Using microphone {mic_index}")
                except Exception as e:
                    print(f"❌ Selected microphone {mic_index} failed: {e}")
                    print("🎤 Falling back to default microphone...")
                    self.microphone = sr.Microphone()
            else:
                self.microphone = sr.Microphone()
                print("🎤 Using default microphone")

            print("🎤 Initializing microphone...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ Microphone ready!")
        except Exception as e:
            print(f"❌ Microphone initialization failed: {e}")
            raise
    
    @staticmethod
    def list_microphones():
        """List filtered microphones (real input devices only, deduplicated)"""
        pa = pyaudio.PyAudio()
        all_mics = sr.Microphone.list_microphone_names()
        
        # Filter out virtual/system microphones
        filtered_mics = []
        seen_names = set()
        skip_keywords = [
            "stereo mix", "what u hear", "wave out mix", "loopback", 
            "virtual", "output", "speakers", "headphones", "realtek hd audio rear output",
            "realtek hd audio front output", "realtek digital output", "sound mapper",
            "primary sound", "voicemod", "steelseries sonar", "line out", "line in",
            "earphone", "nvidia high definition"
        ]
        
        for i, name in enumerate(all_mics):
            name_lower = name.lower()
            
            # Skip if contains filtered keywords
            if any(keyword in name_lower for keyword in skip_keywords):
                continue
            
            # Only include real input devices
            try:
                info = pa.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) < 1:
                    continue
            except Exception:
                continue

            # Clean up the name for deduplication
            clean_name = name.split('(')[0].strip()  # Remove parenthetical info
            
            # Skip if we've already seen this microphone name
            if clean_name.lower() in seen_names:
                continue
            
            seen_names.add(clean_name.lower())
            filtered_mics.append((i, name))
        
        print("🎤 Available input microphones:")
        for idx, (original_index, name) in enumerate(filtered_mics):
            print(f"  {idx+1}: {name}")
        
        pa.terminate()
        return filtered_mics
    
    def test_microphone(self):
        """Test the current microphone"""
        try:
            print("🎤 Testing microphone... Say something!")
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=3)
            
            text = self.recognizer.recognize_google(audio)
            print(f"✅ Microphone test successful! Heard: '{text}'")
            return True
            
        except sr.UnknownValueError:
            print("❌ Could not understand the audio")
            return False
        except sr.RequestError as e:
            print(f"❌ Speech recognition error: {e}")
            return False
        except sr.WaitTimeoutError:
            print("❌ No speech detected during test")
            return False
        except Exception as e:
            print(f"❌ Microphone test failed: {e}")
            return False
    
    def set_callback(self, callback: Callable[[str], None]):
        """Set callback function to process recognized speech after wake word"""
        self.callback = callback
    
    def start_listening(self):
        """Start continuous listening for wake word"""
        if self.is_listening:
            print("Already listening!")
            return
        
        self.is_listening = True
        self.listen_thread = threading.Thread(target=self._listen_worker)
        self.listen_thread.daemon = True
        self.listen_thread.start()
        print("� Listening. ..")
    
    def _listen_worker(self):
        """Main listening loop - waits for wake word and captures full phrase"""
        while self.is_listening:
            try:
                # Listen for a complete phrase that might contain wake word + command
                full_text = self._listen_for_phrase()
                if full_text:
                    # Check for quit command first
                    if "quit" in full_text.lower():
                        print("👋 Goodbye!")
                        import os
                        os._exit(0)  # Force exit without thread cleanup
                    
                    # Check if it contains wake word and extract command
                    command = self._extract_command_from_phrase(full_text)
                    if command:
                        print(f"{command}")
                        if self.callback:
                            self.callback(command)
                        # Continue listening for next "Hey Quacky" command
                
            except Exception as e:
                if self.is_listening:  # Only print error if we're still supposed to be listening
                    print(f"❌ Error in listening: {e}")
                time.sleep(0.1)
    
    def _listen_for_phrase(self) -> Optional[str]:
        """Listen for a complete phrase"""
        try:
            with self.microphone as source:
                # Listen for longer phrases to capture wake word + command
                audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=8)
            
            text = self.recognizer.recognize_google(audio)
            return text
                
        except sr.UnknownValueError:
            # Speech was unintelligible - continue listening silently
            pass
        except sr.RequestError as e:
            print(f"❌ Speech recognition error: {e}")
        except sr.WaitTimeoutError:
            # No speech detected - continue listening silently
            pass
        
        return None
    
    def _extract_command_from_phrase(self, text: str) -> Optional[str]:
        """Extract command from phrase if it contains wake word"""
        text_lower = text.lower()
        
        # Check for wake words and extract everything after them
        wake_words = ["hey quacky", "hey quaky", "quacky", "hey ducky"]
        
        for wake_word in wake_words:
            if wake_word in text_lower:
                # Find the position after the wake word
                wake_pos = text_lower.find(wake_word)
                command_start = wake_pos + len(wake_word)
                
                # Extract everything after the wake word
                command = text[command_start:].strip()
                
                # Only return if there's actually a command after the wake word
                if command:
                    return command
        
        return None
    
    def stop_listening(self):
        """Stop the listening loop"""
        self.is_listening = False
        # Don't try to join the thread if we're calling this from within the thread

def process_command(command: str):
    """Process the captured command - this is where you'll send to Gemini AI"""
    # TODO: Send to Gemini AI here
    # For now, just acknowledge silently - the command is already printed
    pass

def main():
    print("🦆 Quacky Speech-to-Text")
    print("=" * 30)
    
    # List filtered microphones
    filtered_mics = QuackySpeechToText.list_microphones()
    
    if not filtered_mics:
        print("❌ No input microphones found. Using default.")
        mic_index = None
    else:
        # Ask user to select microphone
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
                    # Get the original index from the filtered list
                    mic_index = filtered_mics[choice - 1][0]
                    break
                else:
                    print(f"❌ Please enter a number between 1 and {len(filtered_mics)}, or 0 for default.")
            except ValueError:
                print("❌ Please enter a valid number.")
    
    print("\n" + "=" * 30)
    print("🎧 Listening... (Say 'quit' to exit)")
    print("=" * 30)
    
    try:
        stt = QuackySpeechToText(mic_index=mic_index)
        
        # Test microphone first
        if stt.test_microphone():
            stt.set_callback(process_command)
            stt.start_listening()
            
            # Keep the main thread alive
            while True:
                time.sleep(1)
        else:
            print("❌ Microphone test failed. Please try a different microphone.")
            
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        if 'stt' in locals():
            stt.stop_listening()
    except Exception as e:
        print(f"❌ Error: {e}")
        if 'stt' in locals():
            stt.stop_listening()

if __name__ == "__main__":
    main()
