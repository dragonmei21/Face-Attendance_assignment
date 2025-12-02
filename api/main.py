# api/main.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI

from core.system import ClassAttendanceSystem
from .models.schemas import HealthResponse
from .routes import register, recognize, logs, users

app = FastAPI(
    title="Face Attendance API",
    version="1.0.0",
    description="API layer on top of the local face attendance system.",
)

# Global system instance
system = ClassAttendanceSystem(
    users_dir="data/users",
    embeddings_file="data/known_faces.pkl",
    logs_file="data/attendance.csv",
    threshold=0.6,
)

startup_time = datetime.utcnow()


@app.on_event("startup")
async def on_startup():
    """
    Optionally try to load embeddings on startup.
    If they don't exist yet, it's fine – they will be built 
    on /register_face.
    """
    try:
        system._ensure_recognizer()
    except Exception:
        # No embeddings yet, ignore
        pass


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Return system status and uptime, and whether embeddings are loaded.
    """
    now = datetime.utcnow()
    uptime = (now - startup_time).total_seconds()

    embeddings_loaded = system.recognizer is not None
    known_users = len(system.recognizer.known_ids) if embeddings_loaded else 0

    return HealthResponse(
        status="ok",
        uptime_seconds=uptime,
        embeddings_loaded=embeddings_loaded,
        known_users=known_users,
    )


# Include routers from routes package
app.include_router(
    register.router,
    prefix="",
    tags=["register"],
)
app.include_router(
    recognize.router,
    prefix="",
    tags=["recognize"],
)
app.include_router(
    logs.router,
    prefix="",
    tags=["attendance"],
)
app.include_router(
    users.router,
    prefix="",
    tags=["users"],
)
