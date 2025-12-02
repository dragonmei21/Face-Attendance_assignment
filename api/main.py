from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
import uuid
import shutil

from face_attendance.class_attendance_system import ClassAttendanceSystem

app = FastAPI()

system = ClassAttendanceSystem(
    users_dir="data/users",
    embeddings_file="data/known_faces.pkl",
    logs_file="data/attendance.csv",
    threshold=0.6
)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/recognize")
async def recognize(image: UploadFile = File(...)):
    ext = image.filename.split(".")[-1].lower()
    if ext not in {"jpg", "jpeg", "png"}:
        raise HTTPException(status_code=400, detail="Invalid image format")

    temp_path = Path(f"/tmp/{uuid.uuid4()}.{ext}")
    with temp_path.open("wb") as f:
        shutil.copyfileobj(image.file, f)

    try:
        results = system.recognize(str(temp_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        temp_path.unlink(missing_ok=True)

    return {"results": results}

