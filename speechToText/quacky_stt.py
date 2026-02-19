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
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.microphone = None
        self.is_listening = False
        self.is_active = False
        self.wake_word = "hey quacky"
        self.callback = None
        self.stop_and_listen_callback = None
        self.background_listener = None  # For real-time speech detection
        
        try:
            if mic_index is not None:
                try:
                    self.microphone = sr.Microphone(device_index=mic_index)
                except Exception as e:
                    print(f"Selected microphone {mic_index} failed: {e}")
                    print("Falling back to default microphone...")
                    self.microphone = sr.Microphone()
            else:
                self.microphone = sr.Microphone()

            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
        except Exception as e:
            print(f"Microphone initialization failed: {e}")
            raise
    
    @staticmethod
    def list_microphones():
        """List filtered microphones (real input devices only, deduplicated)"""
        pa = pyaudio.PyAudio()
        all_mics = sr.Microphone.list_microphone_names()
        
        filtered_mics = []
        seen_names = set()
        skip_keywords = [
            "stereo mix", "what u hear", "wave out mix", "loopback", 
            "virtual", "output", "speakers", "realtek hd audio rear output",
            "realtek hd audio front output", "realtek digital output", "sound mapper",
            "primary sound", "voicemod", "steelseries sonar", "line out",
            "nvidia high definition"
        ]
        
        for i, name in enumerate(all_mics):
            name_lower = name.lower()
            
            # Don't filter out iPhone or other phone microphones
            if "iphone" in name_lower or "phone" in name_lower:
                clean_name = name.split('(')[0].strip()
                if clean_name.lower() not in seen_names:
                    seen_names.add(clean_name.lower())
                    filtered_mics.append((i, name))
                continue
            
            if any(keyword in name_lower for keyword in skip_keywords):
                continue
            
            try:
                info = pa.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) < 1:
                    continue
            except Exception:
                continue

            clean_name = name.split('(')[0].strip()
            
            if clean_name.lower() in seen_names:
                continue
            
            seen_names.add(clean_name.lower())
            filtered_mics.append((i, name))
        
        print("Available input microphones:")
        for idx, (original_index, name) in enumerate(filtered_mics):
            print(f"{idx+1}: {name}")
        
        pa.terminate()
        return filtered_mics
    
    def set_callback(self, callback: Callable[[str], None]):
        """Set callback function to process recognized speech after wake word"""
        self.callback = callback
    
    def set_stop_callback(self, stop_callback: Callable[[], None]):
        """Set callback to stop audio playback when speech is detected"""
        self.stop_and_listen_callback = stop_callback
    
    def start_listening(self):
        """Start continuous listening for wake word"""
        if self.is_listening:
            return
        
        self.is_listening = True
        
        # Start background listener for real-time speech detection
        def audio_callback(recognizer, audio):
            """Called whenever audio is captured"""
            # Stop any playing audio immediately when speech is detected
            if self.stop_and_listen_callback:
                self.stop_and_listen_callback()
            
            # Process the audio in a separate thread
            threading.Thread(target=self._process_audio, args=(audio,), daemon=True).start()
        
        self.background_listener = self.recognizer.listen_in_background(
            self.microphone, 
            audio_callback,
            phrase_time_limit=10
        )
    
    def _process_audio(self, audio):
        """Process captured audio"""
        try:
            text = self.recognizer.recognize_google(audio)
            if not text:
                return
            
            if "quit" in text.lower():
                import os
                os._exit(0)
            
            # If not active yet, check for wake word
            if not self.is_active:
                command = self._extract_command_from_phrase(text)
                if command:
                    self.is_active = True
                    print("Quacky activated! Listening for all commands...")
                    print(f"{command}")
                    if self.callback:
                        self.callback(command)
            else:
                # Already active, process everything as a command
                print(f"{text}")
                if self.callback:
                    self.callback(text)
                    
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            print(f"Speech recognition error: {e}")
        except Exception as e:
            if self.is_listening:
                print(f"Error processing audio: {e}")
    
    def _extract_command_from_phrase(self, text: str) -> Optional[str]:
        """Extract command from phrase if it contains wake word"""
        text_lower = text.lower()
        
        wake_words = ["hey quacky", "hey quaky", "quacky", "hey ducky"]
        
        for wake_word in wake_words:
            if wake_word in text_lower:
                wake_pos = text_lower.find(wake_word)
                command_start = wake_pos + len(wake_word)
                
                command = text[command_start:].strip()
                
                if command:
                    return command
        
        return None
    
    def stop_listening(self):
        """Stop the listening loop"""
        self.is_listening = False
        if self.background_listener:
            self.background_listener(wait_for_stop=False)

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
