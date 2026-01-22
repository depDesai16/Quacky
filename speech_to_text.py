"""
Cross-platform Speech-to-Text module for Quacky
Supports Windows, macOS, and Linux
"""
import speech_recognition as sr
import threading
import queue
import time
from typing import Optional, Callable

class SpeechToText:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        try:
            self.microphone = sr.Microphone()
            self.mic_available = True
            # Adjust for ambient noise
            print("Calibrating microphone for ambient noise...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Calibration complete!")
        except Exception as e:
            print(f"Microphone initialization failed: {e}")
            print("You may need to install PyAudio or check microphone permissions")
            self.mic_available = False
        
        self.is_listening = False
        self.text_queue = queue.Queue()
        self.callback = None
    
    def set_callback(self, callback: Callable[[str], None]):
        """Set a callback function to process recognized text"""
        self.callback = callback
    
    def listen_continuously(self):
        """Start continuous listening in a separate thread"""
        if not self.mic_available:
            print("Microphone not available. Cannot start continuous listening.")
            return
            
        if self.is_listening:
            print("Already listening!")
            return
        
        self.is_listening = True
        self.listen_thread = threading.Thread(target=self._listen_worker)
        self.listen_thread.daemon = True
        self.listen_thread.start()
        print("Started continuous listening...")
    
    def _listen_worker(self):
        """Worker function for continuous listening"""
        while self.is_listening:
            try:
                with self.microphone as source:
                    # Listen for audio with timeout
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                
                # Recognize speech using Google's service (free tier)
                try:
                    text = self.recognizer.recognize_google(audio)
                    if text:
                        print(f"Recognized: {text}")
                        self.text_queue.put(text)
                        if self.callback:
                            self.callback(text)
                except sr.UnknownValueError:
                    # Speech was unintelligible
                    pass
                except sr.RequestError as e:
                    print(f"Could not request results; {e}")
                    
            except sr.WaitTimeoutError:
                # No speech detected within timeout
                pass
            except Exception as e:
                print(f"Error in speech recognition: {e}")
                time.sleep(0.1)
    
    def listen_once(self) -> Optional[str]:
        """Listen for a single phrase and return the text"""
        if not self.mic_available:
            print("Microphone not available. Cannot listen.")
            return None
            
        try:
            print("Listening for speech...")
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=5)
            
            print("Processing speech...")
            text = self.recognizer.recognize_google(audio)
            print(f"Recognized: {text}")
            return text
            
        except sr.UnknownValueError:
            print("Could not understand the audio")
            return None
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
            return None
        except sr.WaitTimeoutError:
            print("No speech detected within timeout")
            return None
    
    def get_text_from_queue(self) -> Optional[str]:
        """Get recognized text from the queue (non-blocking)"""
        try:
            return self.text_queue.get_nowait()
        except queue.Empty:
            return None
    
    def stop_listening(self):
        """Stop continuous listening"""
        self.is_listening = False
        if hasattr(self, 'listen_thread'):
            self.listen_thread.join(timeout=2)
        print("Stopped listening")
    
    def test_microphone(self):
        """Test if microphone is working"""
        if not self.mic_available:
            print("❌ Microphone not available")
            return False
        
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
            print(f"❌ Speech recognition service error: {e}")
            return False
        except sr.WaitTimeoutError:
            print("❌ No speech detected during test")
            return False
        except Exception as e:
            print(f"❌ Microphone test failed: {e}")
            return False