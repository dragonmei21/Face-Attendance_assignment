from __future__ import annotations

from typing import Dict, List, Optional

import cv2
import face_recognition
import numpy as np

from attendance.logger import AttendanceLogger
from embeddings.manager import EmbeddingManager
from recognition.face_recognizer import FaceRecognizer

class ClassAttendanceSystem:
    def __init__(
        self,
        users_dir: str = "data/users",
        embeddings_file: str = "data/known_faces.pkl",
        threshold: float = 0.5,
    ) -> None:
        self.embedding_manager = EmbeddingManager(users_dir, embeddings_file)
        self.logger = AttendanceLogger()
        self.threshold = threshold
        self.recognizer: Optional[FaceRecognizer] = None

    def _ensure_recognizer(self) -> None:
        if self.recognizer is None:
            embeddings = self.embedding_manager.load()
            self.recognizer = FaceRecognizer(embeddings, threshold=self.threshold)

    def build_database(self) -> Dict[str, List[float]]:
        embeddings = self.embedding_manager.build_database()
        self.recognizer = FaceRecognizer(embeddings, threshold=self.threshold)
        return embeddings

    def recognize(self, image_path: str) -> List[Dict]:
        self._ensure_recognizer()
        assert self.recognizer is not None
        return self.recognizer.recognize(image_path)

    def log_attendance(self, user_id: str, source: str = "manual") -> bool:
        return self.logger.log(user_id, source)

    def recognize_frame(self, frame: np.ndarray) -> List[Dict]:
        self._ensure_recognizer()
        assert self.recognizer is not None
        return self.recognizer.recognize_frame(frame)

    def enroll_user(self, user_id: str, face_image_bgr: np.ndarray) -> None:
        if not user_id:
            raise ValueError("user_id is required for enrollment")

        rgb_face = cv2.cvtColor(face_image_bgr, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(rgb_face)
        if not encodings:
            raise ValueError("Unable to encode face for enrollment")
        embedding_vector = encodings[0].tolist()

        success, buffer = cv2.imencode(".jpg", face_image_bgr)
        if not success:
            raise ValueError("Failed to encode face image for storage")
        image_bytes = buffer.tobytes()
        self.embedding_manager.store_user_image(user_id, image_bytes, extension="jpg")
        self.embedding_manager.upsert_embedding(user_id, embedding_vector)

        embeddings = self.embedding_manager.load()
        self.recognizer = FaceRecognizer(embeddings, threshold=self.threshold)