"""
Face Recognition Engine using DeepFace.
Compares detected faces against images in the wanted_faces/ folder.
Triggers FACE_MATCH_WANTED events (reliability weight = 0.95).
"""

import os
try:
    import cv2
except ImportError:
    cv2 = None
import numpy as np
from datetime import datetime

try:
    from deepface import DeepFace
    HAS_DEEPFACE = True
except ImportError:
    HAS_DEEPFACE = False
    print("[WARN] deepface not installed. Face recognition disabled.")

WANTED_FACES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "wanted_faces")
FACE_CHECK_INTERVAL = 30
FACE_MATCH_THRESHOLD = 0.6


class FaceRecognitionEngine:
    def __init__(self):
        self.wanted_faces = {}
        self.last_check_frame = 0
        self.matches = []
        self._load_wanted_faces()

    def _load_wanted_faces(self):
        if not os.path.exists(WANTED_FACES_DIR):
            os.makedirs(WANTED_FACES_DIR, exist_ok=True)
            print(f"[FACE] Created wanted_faces directory: {WANTED_FACES_DIR}")
            print("[FACE] Add photos of 'wanted' persons here for demo.")
            return

        valid_extensions = {".jpg", ".jpeg", ".png", ".bmp"}
        for filename in os.listdir(WANTED_FACES_DIR):
            ext = os.path.splitext(filename)[1].lower()
            if ext in valid_extensions:
                filepath = os.path.join(WANTED_FACES_DIR, filename)
                name = os.path.splitext(filename)[0].replace("_", " ").title()
                self.wanted_faces[name] = filepath

        if self.wanted_faces:
            print(f"[FACE] Loaded {len(self.wanted_faces)} wanted face(s): {list(self.wanted_faces.keys())}")
        else:
            print("[FACE] No wanted faces found. Add .jpg/.png images to wanted_faces/ folder.")

    def check_frame(self, frame, frame_count, camera_location=None):
        """
        Check a video frame for wanted faces.
        Only runs every FACE_CHECK_INTERVAL frames to save performance.
        Returns list of match events.
        """
        if not HAS_DEEPFACE or not self.wanted_faces:
            return []

        if frame_count - self.last_check_frame < FACE_CHECK_INTERVAL:
            return []

        self.last_check_frame = frame_count
        events = []
        location = camera_location or {"lat": 3.1466, "lon": 101.7108}

        for name, wanted_path in self.wanted_faces.items():
            try:
                result = DeepFace.verify(
                    img1_path=frame,
                    img2_path=wanted_path,
                    model_name="VGG-Face",
                    enforce_detection=False,
                    detector_backend="opencv",
                )

                if result.get("verified", False):
                    distance = result.get("distance", 1.0)
                    confidence = max(0.5, min(1.0 - distance, 0.99))

                    event = {
                        "event_type": "FACE_MATCH_WANTED",
                        "confidence_score": round(confidence, 2),
                        "latitude": location["lat"],
                        "longitude": location["lon"],
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "source": "CCTV_AI",
                        "details": f"WANTED PERSON DETECTED: {name} (confidence: {confidence:.0%})",
                        "person_name": name,
                    }
                    events.append(event)
                    self.matches.append(event)
                    print(f"[FACE] *** MATCH: {name} detected! Confidence: {confidence:.0%} ***")

            except Exception:
                pass

        return events

    def get_recent_matches(self, n=10):
        return self.matches[-n:]

    def add_wanted_face(self, name, image_path):
        if os.path.exists(image_path):
            dest = os.path.join(WANTED_FACES_DIR, f"{name.replace(' ', '_')}.jpg")
            img = cv2.imread(image_path)
            if img is not None:
                cv2.imwrite(dest, img)
                self.wanted_faces[name] = dest
                print(f"[FACE] Added wanted person: {name}")
                return True
        return False
