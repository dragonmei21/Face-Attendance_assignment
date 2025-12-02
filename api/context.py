from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core.system import ClassAttendanceSystem

DATA_USERS_DIR = Path("data/users")
DATA_USERS_DIR.mkdir(parents=True, exist_ok=True)

system = ClassAttendanceSystem(
    users_dir=str(DATA_USERS_DIR),
    embeddings_file="data/known_faces.pkl",
    threshold=0.5,
)

startup_time = datetime.utcnow()

