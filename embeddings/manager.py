from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

import boto3
import face_recognition

from aws.config import FACES_TABLE, S3_BUCKET, get_boto3_session_kwargs


class EmbeddingManager:
    """
    Handles user image storage in S3 and embedding vectors in DynamoDB.
    """

    USERS_PREFIX = "users"

    def __init__(self, users_dir: str, storage_path: str) -> None:
        # users_dir and storage_path retained for backward compatibility / local cache
        self.users_dir = Path(users_dir)
        self.storage_path = Path(storage_path)

        session_kwargs = get_boto3_session_kwargs()
        self.s3 = boto3.client("s3", **session_kwargs)
        dynamodb = boto3.resource("dynamodb", **session_kwargs)
        self.faces_table = dynamodb.Table(FACES_TABLE)

    def build_database(self) -> Dict[str, List[float]]:
        """
        Rebuild embeddings by iterating through all user images in S3.
        """
        paginator = self.s3.get_paginator("list_objects_v2")
        embeddings: Dict[str, List[float]] = {}
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=f"{self.USERS_PREFIX}/"):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith("/"):
                    continue
                user_id = Path(key).parent.name
                image_bytes = self._download_image_bytes(key)
                if not image_bytes:
                    continue
                vector = self._encode_face(image_bytes)
                if vector is None:
                    continue
                embeddings[user_id] = vector

        if not embeddings:
            raise RuntimeError("No embeddings generated from S3 source.")

        self.save(embeddings)
        return embeddings

    def load(self) -> Dict[str, List[float]]:
        """
        Load embeddings from DynamoDB into memory for the recognizer.
        """
        items = self._scan_faces_table()
        embeddings: Dict[str, List[float]] = {}
        for item in items:
            face_id = item.get("face_id")
            embedding_data = item.get("embedding")
            # Skip items that don't have proper embedding data
            if not face_id or not embedding_data:
                print(f"[WARNING] Skipping item without embedding: {face_id}")
                continue
            vector = [float(value) for value in embedding_data]
            embeddings[face_id] = vector
        return embeddings

    def save(self, embeddings: Dict[str, List[float]]) -> None:
        """
        Persist a batch of embeddings to DynamoDB.
        """
        timestamp = datetime.utcnow().isoformat()
        with self.faces_table.batch_writer() as batch:
            for face_id, vector in embeddings.items():
                batch.put_item(
                    Item={
                        "face_id": face_id,
                        "embedding": [Decimal(str(value)) for value in vector],
                        "updated_at": timestamp,
                    }
                )

    def upsert_embedding(self, face_id: str, vector: List[float]) -> None:
        self.faces_table.put_item(
            Item={
                "face_id": face_id,
                "embedding": [Decimal(str(value)) for value in vector],
                "updated_at": datetime.utcnow().isoformat(),
            }
        )

    def store_user_image(self, user_id: str, image_bytes: bytes, extension: str = "jpg") -> str:
        """
        Upload the captured face image to S3 and return the object key.
        """
        key = f"{self.USERS_PREFIX}/{user_id}/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{extension}"
        self.s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=image_bytes,
            ContentType=f"image/{extension}",
            CacheControl="no-store",
        )
        return key

    def _scan_faces_table(self) -> List[dict]:
        items: List[dict] = []
        response = self.faces_table.scan()
        items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = self.faces_table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
        return items

    def _download_image_bytes(self, key: str) -> Optional[bytes]:
        try:
            response = self.s3.get_object(Bucket=S3_BUCKET, Key=key)
        except self.s3.exceptions.NoSuchKey:
            return None
        return response["Body"].read()

    def _encode_face(self, image_bytes: bytes) -> Optional[List[float]]:
        image_stream = io.BytesIO(image_bytes)
        image = face_recognition.load_image_file(image_stream)
        face_locations = face_recognition.face_locations(image)
        if not face_locations:
            return None
        encodings = face_recognition.face_encodings(image, face_locations)
        if not encodings:
            return None
        return encodings[0].tolist()
