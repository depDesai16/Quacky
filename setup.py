#!/usr/bin/env python3
"""
Setup script for cross-platform speech-to-text dependencies
"""
import subprocess
import sys
import platform

def install_dependencies():
    """Install required dependencies based on the operating system"""
    system = platform.system().lower()
    
    print(f"Detected OS: {system}")
    
    # Install Python packages
    print("Installing Python packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Platform-specific instructions
    if system == "linux":
        print("\nLinux setup:")
        print("You may need to install additional system packages:")
        print("Ubuntu/Debian: sudo apt-get install python3-pyaudio portaudio19-dev")
        print("CentOS/RHEL: sudo yum install python3-pyaudio portaudio-devel")
        
    elif system == "darwin":  # macOS
        print("\nmacOS setup:")
        print("If you encounter issues with pyaudio, try:")
        print("brew install portaudio")
        print("pip install --upgrade pyaudio")
        
    elif system == "windows":
        print("\nWindows setup:")
        print("PyAudio should install automatically on Windows")
        print("If you encounter issues, you may need to install Visual C++ Build Tools")
    
    print("\nSetup complete! You can now run: python app.py")

if __name__ == "__main__":
    install_dependencies()