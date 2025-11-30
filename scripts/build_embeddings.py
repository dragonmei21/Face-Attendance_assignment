from embeddings.manager import EmbeddingManager


def main() -> None:
    manager = EmbeddingManager(users_dir="data/users", storage_path="data/known_faces.pkl")
    embeddings = manager.build_database()
    print(f"Built embeddings for {len(embeddings)} users.")


if __name__ == "__main__":
    main()
from embeddings.manager import EmbeddingManager


def main() -> None:
    manager = EmbeddingManager(users_dir="data/users", storage_path="data/known_faces.pkl")
    embeddings = manager.build_database()
    print(f"Built embeddings for {len(embeddings)} users.")


if __name__ == "__main__":
    main()
