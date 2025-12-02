from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Union

import cv2
import face_recognition
import numpy as np

from attendance.logger import AttendanceLogger
from attendance.dynamodb_logger import DynamoDBLogger
from embeddings.manager import EmbeddingManager
from recognition.face_recognizer import FaceRecognizer

class ClassAttendanceSystem:
    def __init__(
        self,
        users_dir: str = "data/users",
        embeddings_file: str = "data/known_faces.pkl",
        logs_file: str = "data/attendance.csv",
        threshold: float = 0.5,
        storage_type: str = "csv",
        dynamodb_table: Optional[str] = None,
        dynamodb_region: str = "us-east-1",
    ) -> None:
        """
        Initialize the Class Attendance System.
        
        Args:
            users_dir: Directory path for user face images
            embeddings_file: Path to embeddings pickle file
            logs_file: Path to logs file (used only if storage_type is 'csv')
            threshold: Distance threshold for face recognition
            storage_type: Either 'csv' or 'dynamodb'
            dynamodb_table: DynamoDB table name (required if storage_type is 'dynamodb')
            dynamodb_region: AWS region for DynamoDB
        """
        self.embedding_manager = EmbeddingManager(users_dir, embeddings_file)
        
        # Initialize logger based on storage type
        if storage_type == "dynamodb":
            if not dynamodb_table:
                raise ValueError("dynamodb_table is required when storage_type is 'dynamodb'")
            self.logger: Union[AttendanceLogger, DynamoDBLogger] = DynamoDBLogger(
                table_name=dynamodb_table,
                region=dynamodb_region,
                create_table=False,
            )
        elif storage_type == "csv":
            self.logger = AttendanceLogger(storage_path=logs_file)
        else:
            raise ValueError(f"Unsupported storage_type: {storage_type}")
        
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

        try:
            embeddings = self.embedding_manager.load()
        except FileNotFoundError:
            embeddings = {}

        embeddings[user_id] = embedding_vector
        self.embedding_manager.save(embeddings)
        self.recognizer = FaceRecognizer(embeddings, threshold=self.threshold)
        self._persist_face_image(user_id, face_image_bgr)

    def _persist_face_image(self, user_id: str, face_image_bgr: np.ndarray) -> None:
        user_dir = self.embedding_manager.users_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jpg"
        image_path = user_dir / filename
        cv2.imwrite(str(image_path), face_image_bgr)