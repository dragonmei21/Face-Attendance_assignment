# api/routes/register.py
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from api.main import system, DATA_USERS_DIR  # or adjust import if needed
from api.models.schemas import RegisterResponse

# If DATA_USERS_DIR isn't in main yet, define here:
DATA_USERS_DIR = Path("data/users")
DATA_USERS_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter()


@router.post("/register_face", response_model=RegisterResponse)
async def register_face(
    user_id: str = Form(...),
    image: UploadFile = File(...),
) -> RegisterResponse:
    if not user_id.strip():
        raise HTTPException(status_code=400, detail="user_id must not be empty")

    ext = image.filename.split(".")[-1].lower()
    if ext not in {"jpg", "jpeg", "png"}:
        raise HTTPException(status_code=400, detail="Image must be jpg, jpeg, or png")

    user_dir = DATA_USERS_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4()}.{ext}"
    image_path = user_dir / filename

    try:
        with image_path.open("wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save image: {e}")

    # Rebuild embeddings using core system
    try:
        system.build_database()
    except Exception as e:
        image_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to rebuild embeddings: {e}")

    return RegisterResponse(success=True, message=f"Face registered for user '{user_id}'")
