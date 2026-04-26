"""
Manual face-recognition smoke script.
Import-safe so unittest discovery does not execute or fail on it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    import cv2

    from camera.face_recognition import FaceRecognitionManager

    print("Face Recognition Test")
    print("=" * 50)
    
    # Initialize face recognition
    fr = FaceRecognitionManager()
    
    # Check registered users
    users = fr.get_registered_users()
    print(f"\nRegistered users: {users if users else 'None'}")
    
    # Open camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Cannot open camera")
        return
    
    print("\nCamera opened successfully!")
    print("\nControls:")
    print("  'r' - Register new user")
    print("  't' - Test recognition")
    print("  'q' - Quit")
    print("\nPress a key...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("ERROR: Cannot read frame")
            break
        
        # Display frame
        display_frame = frame.copy()
        
        # Detect faces
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
        
        # Draw face rectangles
        for (x, y, w, h) in faces:
            cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        # Show instructions
        cv2.putText(display_frame, "Press 'r' to register, 't' to test, 'q' to quit",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow('Face Recognition Test', display_frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            break
        elif key == ord('r'):
            # Register user
            name = input("\nEnter your name: ").strip()
            if name:
                success, message = fr.register_user(name, frame)
                print(f"{'✓' if success else '✗'} {message}")
                users = fr.get_registered_users()
                print(f"Registered users: {users}")
        elif key == ord('t'):
            # Test recognition
            print("\nTesting recognition...")
            name, confidence = fr.recognize_user(frame)
            if name == "Unknown":
                print("✗ No user recognized")
            else:
                print(f"✓ Recognized: {name} ({confidence*100:.1f}% confidence)")
    
    cap.release()
    cv2.destroyAllWindows()
    print("\nTest complete!")

if __name__ == "__main__":
    main()
