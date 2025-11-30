from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from attendance.logger import AttendanceLogger
from embeddings.manager import EmbeddingManager
from recognition.face_recognizer import FaceRecognizer
import numpy as np

class ClassAttendanceSystem:
    def __init__(
        self,
        users_dir: str = "data/users",
        embeddings_file: str = "data/known_faces.pkl",
        logs_file: str = "data/attendance.csv",
        threshold: float = 0.6,
    ) -> None:
        self.embedding_manager = EmbeddingManager(users_dir, embeddings_file)
        self.logger = AttendanceLogger(storage_path=logs_file)
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

    def recognize_frame(self, frame: np.ndarray) -> List[Dict]:
        self._ensure_recognizer()
        assert self.recognizer is not None
        return self.recognizer.recognize_frame(frame)