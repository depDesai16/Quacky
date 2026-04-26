#!/usr/bin/env python3
"""
Simple manual test to check if speech_recognition is available.
Import-safe so unittest discovery does not execute or fail on it.
"""

import sys


def main():
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print(f"Python path: {sys.path}")

    try:
        import speech_recognition as sr

        print("✅ SpeechRecognition imported successfully!")
        print(f"SpeechRecognition version: {sr.__version__}")

        r = sr.Recognizer()
        print("✅ Recognizer created successfully!")

        try:
            mics = sr.Microphone.list_microphone_names()
            print(f"✅ Found {len(mics)} microphones:")
            for i, mic in enumerate(mics[:5]):
                print(f"  {i}: {mic}")
        except Exception as e:
            print(f"⚠️  Could not list microphones: {e}")
            print("This is normal if PyAudio is not installed")

    except ImportError as e:
        print(f"❌ Failed to import SpeechRecognition: {e}")
        print("Try: pip install SpeechRecognition")
    except Exception as e:
        print(f"❌ Error testing SpeechRecognition: {e}")


if __name__ == "__main__":
    main()
