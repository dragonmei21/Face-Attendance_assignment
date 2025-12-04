from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Query
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .context import system, startup_time
from .models.schemas import HealthResponse
from .routes import register, recognize, logs, users

app = FastAPI(
    title="Face Attendance API",
    version="1.0.0",
    description="API layer on top of the local face attendance system.",
)

UI_ROOT = Path("webui")
STATIC_DIR = UI_ROOT / "static"
INDEX_FILE = UI_ROOT / "index.html"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


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


@app.get("/", response_class=HTMLResponse)
async def index():
    if not INDEX_FILE.exists():
        raise HTTPException(status_code=404, detail="UI not found. Build assets first.")
    return FileResponse(INDEX_FILE)


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


@app.post("/recognize")
async def recognize_face(image: UploadFile = File(...)):
    content = await image.read()
    try:
        rgb_frame, _ = _decode_image(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        results = system.recognize_frame(rgb_frame)
    except Exception as exc:
        import traceback
        traceback.print_exc()  # Print full error to terminal
        raise HTTPException(status_code=500, detail=str(exc))

    recognized = any(face["user_id"] != "Unknown" for face in results)
    return {"results": results, "recognized": recognized}


@app.post("/enroll")
async def enroll(name: str = Form(...), image: UploadFile = File(...)):
    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Name is required for enrollment")

    content = await image.read()
    try:
        _, bgr_frame = _decode_image(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        system.enroll_user(clean_name, bgr_frame)
        system.log_attendance(clean_name, source="web-ui")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        import traceback
        traceback.print_exc()  # Print full error to terminal
        raise HTTPException(status_code=500, detail=str(exc))

    return {"status": "ok", "message": f"Enrolled {clean_name}"}


@app.get("/download/cloud-computing")
async def download_cloud_computing_csv(session_date: Optional[str] = Query(None, description="Session date in YYYYMMDD format")):
    """
    Export Cloud Computing attendance for a given date (YYYYMMDD) or all sessions.
    Only returns records logged via the Lambda (with course_name set).
    Returns a CSV file with attendance records.
    """
    # Build filters - only Cloud Computing course attendance
    filters = {"course_name": "Cloud Computing"}
    if session_date:
        filters["session_id"] = session_date
    
    # Get records from DynamoDB
    try:
        records = system.logger.get_records(filters)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch records: {str(exc)}")
    
    # Build CSV in memory
    output = io.StringIO()
    fieldnames = ["session_id", "face_id", "timestamp", "source", "course_name", "session_start", "session_end"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for record in records:
        writer.writerow({
            "session_id": record.get("session_id", ""),
            "face_id": record.get("user_id", ""),
            "timestamp": record.get("timestamp", ""),
            "source": record.get("source", ""),
            "course_name": record.get("course_name", ""),
            "session_start": record.get("session_start", ""),
            "session_end": record.get("session_end", ""),
        })
    
    output.seek(0)
    filename = f"CloudComputing_Attendance_{session_date or 'all'}.csv"
    
    # Return as streaming response
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def _decode_image(data: bytes):
    array = np.frombuffer(data, dtype=np.uint8)
    bgr = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("Unable to decode image data")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return rgb, bgr


# Include routers from routes package
app.include_router(register.router, prefix="", tags=["register"])
app.include_router(recognize.router, prefix="", tags=["recognize"])
app.include_router(logs.router, prefix="", tags=["attendance"])
app.include_router(users.router, prefix="", tags=["users"])
