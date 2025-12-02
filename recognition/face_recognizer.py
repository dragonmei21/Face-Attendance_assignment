from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import face_recognition
import numpy as np


class FaceRecognizer:
    def __init__(self, embeddings: Dict[str, List[float]], threshold: float = 0.5) -> None:
        self.threshold = threshold
        self.known_ids = list(embeddings.keys())
        self.known_vectors = np.array(list(embeddings.values()))

    def detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        return face_recognition.face_locations(image)

    def get_embedding(self, face_image: np.ndarray) -> np.ndarray:
        encodings = face_recognition.face_encodings(face_image)
        if not encodings:
            raise ValueError("Unable to encode face")
        return encodings[0]

    def match_embedding(self, embedding: np.ndarray) -> Tuple[str, float]:
        if not len(self.known_vectors):
            return "Unknown", 1.0
        distances = np.linalg.norm(self.known_vectors - embedding, axis=1)
        best_idx = int(np.argmin(distances))
        best_dist = float(distances[best_idx])
        if best_dist <= self.threshold:
            return self.known_ids[best_idx], best_dist
        return "Unknown", best_dist

    def recognize(self, image_path: str) -> List[Dict]:
        image = face_recognition.load_image_file(Path(image_path))
        return self._recognize_from_image(image)

    def recognize_frame(self, frame: np.ndarray) -> List[Dict]:
        return self._recognize_from_image(frame)

    def _recognize_from_image(self, image: np.ndarray) -> List[Dict]:
        results: List[Dict] = []
        locations = self.detect_faces(image)
        encodings = face_recognition.face_encodings(image, locations)
        for location, encoding in zip(locations, encodings):
            user_id, distance = self.match_embedding(encoding)
            results.append({"user_id": user_id, "distance": distance, "bbox": location})
        return results
