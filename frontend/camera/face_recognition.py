"""
face_recognition.py - Face recognition and user profile management
"""
import pickle
from pathlib import Path

import cv2
import numpy as np


class FaceRecognitionManager:
    """
    Manages face recognition and user profiles
    - Register new users
    - Recognize existing users
    - Store face encodings
    """
    
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # Storage paths - use absolute path
        script_dir = Path(__file__).parent
        self.data_dir = script_dir / "face_data"
        self.data_dir.mkdir(exist_ok=True)
        self.encodings_file = self.data_dir / "face_encodings.pkl"
        self.profiles_file = self.data_dir / "user_profiles.pkl"
        
        # Load existing data
        self.face_encodings = {}  # {user_name: [encoding1, encoding2, ...]}
        self.user_profiles = {}   # {user_name: {preferences, history, etc}}
        self._load_data()
        
        # Recognition settings
        self.recognition_threshold = 0.65  # Adjusted for new encoding
        self.min_face_size = (80, 80)
    
    def _load_data(self):
        """Load face encodings and user profiles from disk"""
        if self.encodings_file.exists():
            try:
                with open(self.encodings_file, 'rb') as f:
                    self.face_encodings = pickle.load(f)
            except Exception as e:
                print(f"Error loading face encodings: {e}")
                self.face_encodings = {}
        
        if self.profiles_file.exists():
            try:
                with open(self.profiles_file, 'rb') as f:
                    self.user_profiles = pickle.load(f)
            except Exception as e:
                print(f"Error loading user profiles: {e}")
                self.user_profiles = {}
    
    def _save_data(self):
        """Save face encodings and user profiles to disk"""
        try:
            with open(self.encodings_file, 'wb') as f:
                pickle.dump(self.face_encodings, f)
            
            with open(self.profiles_file, 'wb') as f:
                pickle.dump(self.user_profiles, f)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def register_user(self, name, frame):
        """
        Register a new user with their face
        Returns: (success: bool, message: str)
        """
        if not name or name.strip() == "":
            return False, "Name cannot be empty"
        
        name = name.strip()
        
        # Detect face in frame
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=self.min_face_size
        )
        
        if len(faces) == 0:
            return False, "No face detected. Please face the camera."
        
        if len(faces) > 1:
            return False, "Multiple faces detected. Please ensure only you are visible."
        
        # Extract face region
        (x, y, w, h) = faces[0]
        face_roi = gray[y:y+h, x:x+w]
        
        # Create encoding
        encoding = self._create_face_encoding(face_roi)
        
        # Add to database
        if name not in self.face_encodings:
            self.face_encodings[name] = []
            self.user_profiles[name] = {
                'registered_date': str(np.datetime64('now')),
                'login_count': 0,
                'preferences': {}
            }
        
        self.face_encodings[name].append(encoding)
        
        # Keep only last 5 encodings per user
        if len(self.face_encodings[name]) > 5:
            self.face_encodings[name] = self.face_encodings[name][-5:]
        
        self._save_data()
        
        return True, f"Successfully registered {name}!"
    
    def recognize_user(self, frame):
        """
        Recognize user from frame
        Returns: (name: str, confidence: float) or ("Unknown", 0.0)
        """
        if not self.face_encodings:
            return "Unknown", 0.0
        
        # Detect face
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=self.min_face_size
        )
        
        if len(faces) == 0:
            return "Unknown", 0.0
        
        # Use first detected face
        (x, y, w, h) = faces[0]
        face_roi = gray[y:y+h, x:x+w]
        
        # Create encoding
        encoding = self._create_face_encoding(face_roi)
        
        # Compare with all known faces
        best_match = None
        best_distance = float('inf')
        
        for name, encodings in self.face_encodings.items():
            for stored_encoding in encodings:
                distance = self._compare_encodings(encoding, stored_encoding)
                if distance < best_distance:
                    best_distance = distance
                    best_match = name
        
        # Check if match is good enough
        if best_distance < self.recognition_threshold:
            confidence = 1.0 - best_distance
            
            # Update profile
            if best_match in self.user_profiles:
                self.user_profiles[best_match]['login_count'] += 1
                self.user_profiles[best_match]['last_seen'] = str(np.datetime64('now'))
                self._save_data()
            
            return best_match, confidence
        
        return "Unknown", 0.0
    
    def _create_face_encoding(self, face_roi):
        """
        Create a more robust face encoding using multiple features
        """
        # Resize to standard size
        face_resized = cv2.resize(face_roi, (128, 128))
        
        # 1. Histogram features (global intensity distribution)
        hist = cv2.calcHist([face_resized], [0], None, [64], [0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        
        # 2. Local Binary Pattern (texture features)
        lbp = self._compute_lbp(face_resized)
        lbp_hist = cv2.calcHist([lbp], [0], None, [32], [0, 256])
        lbp_hist = cv2.normalize(lbp_hist, lbp_hist).flatten()
        
        # 3. Grid-based features (spatial information)
        grid_features = []
        h, w = face_resized.shape
        grid_size = 16
        for i in range(0, h, grid_size):
            for j in range(0, w, grid_size):
                region = face_resized[i:i+grid_size, j:j+grid_size]
                if region.size > 0:
                    grid_features.append(region.mean())
                    grid_features.append(region.std())
        
        # 4. Edge features (facial structure)
        edges = cv2.Canny(face_resized, 50, 150)
        edge_density = edges.sum() / (h * w)
        
        # Combine all features
        encoding = np.concatenate([
            hist,
            lbp_hist,
            grid_features,
            [edge_density]
        ])
        
        return encoding
    
    def _compute_lbp(self, image):
        """Compute Local Binary Pattern for texture analysis"""
        lbp = np.zeros_like(image)
        h, w = image.shape
        
        for i in range(1, h-1):
            for j in range(1, w-1):
                center = image[i, j]
                code = 0
                code |= (image[i-1, j-1] >= center) << 7
                code |= (image[i-1, j] >= center) << 6
                code |= (image[i-1, j+1] >= center) << 5
                code |= (image[i, j+1] >= center) << 4
                code |= (image[i+1, j+1] >= center) << 3
                code |= (image[i+1, j] >= center) << 2
                code |= (image[i+1, j-1] >= center) << 1
                code |= (image[i, j-1] >= center) << 0
                lbp[i, j] = code
        
        return lbp
    
    def _compare_encodings(self, encoding1, encoding2):
        """
        Compare two face encodings using cosine similarity
        Returns: distance (lower = more similar)
        """
        # Ensure same length
        min_len = min(len(encoding1), len(encoding2))
        encoding1 = encoding1[:min_len]
        encoding2 = encoding2[:min_len]
        
        # Normalize encodings
        norm1 = np.linalg.norm(encoding1)
        norm2 = np.linalg.norm(encoding2)
        
        if norm1 == 0 or norm2 == 0:
            return 1.0
        
        encoding1_norm = encoding1 / norm1
        encoding2_norm = encoding2 / norm2
        
        # Calculate cosine similarity
        similarity = np.dot(encoding1_norm, encoding2_norm)
        
        # Convert to distance (0 = identical, 1 = completely different)
        distance = (1.0 - similarity) / 2.0
        
        return distance
    
    def get_registered_users(self):
        """Get list of registered user names"""
        return list(self.face_encodings.keys())
    
    def delete_user(self, name):
        """Delete a user from the system"""
        if name in self.face_encodings:
            del self.face_encodings[name]
        if name in self.user_profiles:
            del self.user_profiles[name]
        self._save_data()
        return True
    
    def get_user_profile(self, name):
        """Get user profile data"""
        return self.user_profiles.get(name, {})
