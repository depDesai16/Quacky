#!/usr/bin/env python3
"""
Simple test to check if speech_recognition is available
"""
import sys

print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Python path: {sys.path}")

try:
    import speech_recognition as sr
    print("✅ SpeechRecognition imported successfully!")
    print(f"SpeechRecognition version: {sr.__version__}")
    
    # Test basic functionality
    r = sr.Recognizer()
    print("✅ Recognizer created successfully!")
    
    # Try to list microphones
    try:
        mics = sr.Microphone.list_microphone_names()
        print(f"✅ Found {len(mics)} microphones:")
        for i, mic in enumerate(mics[:5]):  # Show first 5
            print(f"  {i}: {mic}")
    except Exception as e:
        print(f"⚠️  Could not list microphones: {e}")
        print("This is normal if PyAudio is not installed")
    
except ImportError as e:
    print(f"❌ Failed to import SpeechRecognition: {e}")
    print("Try: pip install SpeechRecognition")
except Exception as e:
    print(f"❌ Error testing SpeechRecognition: {e}")