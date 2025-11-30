import sys

from embeddings.manager import EmbeddingManager
from recognition.face_recognizer import FaceRecognizer


def main(image_path: str) -> None:
    manager = EmbeddingManager("data/users", "data/known_faces.pkl")
    embeddings = manager.load()
    recognizer = FaceRecognizer(embeddings)
    for result in recognizer.recognize(image_path):
        print(f"{result['user_id']} (distance={result['distance']:.3f}) bbox={result['bbox']}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/recognize.py <image_path>")
        raise SystemExit(1)
    main(sys.argv[1])
import sys
from embeddings.manager import EmbeddingManager
from recognition.face_recognizer import FaceRecognizer


def main(image_path: str) -> None:
    manager = EmbeddingManager("data/users", "data/known_faces.pkl")
    embeddings = manager.load()
    recognizer = FaceRecognizer(embeddings)
    for result in recognizer.recognize(image_path):
        print(f"{result['user_id']} (distance={result['distance']:.3f})")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/recognize.py <image_path>")
        raise SystemExit(1)
    main(sys.argv[1])
