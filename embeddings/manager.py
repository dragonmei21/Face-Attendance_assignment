from __future__ import annotations

import pickle
from pathlib import Path
from typing import Dict, List

import face_recognition


class EmbeddingManager:
    def __init__(self, users_dir: str, storage_path: str) -> None:
        self.users_dir = Path(users_dir)
        self.storage_path = Path(storage_path)

    def build_database(self) -> Dict[str, List[float]]:
        if not self.users_dir.exists():
            raise FileNotFoundError(f"Users directory not found: {self.users_dir}")

        embeddings: Dict[str, List[float]] = {}
        for user_dir in sorted(self.users_dir.iterdir()):
            if not user_dir.is_dir():
                continue
            user_id = user_dir.name

            user_embeddings: List[List[float]] = []
            for image_path in user_dir.glob("*"):
                if not image_path.is_file():
                    continue
                image = face_recognition.load_image_file(image_path)
                face_locations = face_recognition.face_locations(image)
                if not face_locations:
                    print(f"[WARN] No face found in {image_path}")
                    continue
                encodings = face_recognition.face_encodings(image, face_locations)
                if not encodings:
                    print(f"[WARN] Cannot encode face in {image_path}")
                    continue
                user_embeddings.append(encodings[0].tolist())

            if user_embeddings:
                embeddings[user_id] = user_embeddings[0]

        if not embeddings:
            raise RuntimeError("No embeddings generated. Ensure user photos exist.")

        self.save(embeddings)
        return embeddings

    def load(self) -> Dict[str, List[float]]:
        if not self.storage_path.exists():
            raise FileNotFoundError(f"Embedding file not found: {self.storage_path}")
        with self.storage_path.open("rb") as file:
            return pickle.load(file)

    def save(self, embeddings: Dict[str, List[float]]) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with self.storage_path.open("wb") as file:
            pickle.dump(embeddings, file)
