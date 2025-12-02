# api/routes/recognize.py
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from api.context import system
from api.models.schemas import RecognizeResponse, RecognizeResult

router = APIRouter()


@router.post("/recognize", response_model=RecognizeResponse)
async def recognize(image: UploadFile = File(...)) -> RecognizeResponse:
    ext = image.filename.split(".")[-1].lower()
    if ext not in {"jpg", "jpeg", "png"}:
        raise HTTPException(status_code=400, detail="Image must be jpg, jpeg, or png")

    tmp_path = Path(f"/tmp/{uuid.uuid4()}.{ext}")
    try:
        with tmp_path.open("wb") as f:
            shutil.copyfileobj(image.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save temporary image: {e}")

    try:
        raw_results = system.recognize(str(tmp_path))
    except FileNotFoundError:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail="Embedding database not found. Register at least one user first.",
        )
    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Recognition failed: {e}")

    tmp_path.unlink(missing_ok=True)

    results = [
        RecognizeResult(
            user_id=r.get("user_id", "Unknown"),
            distance=float(r.get("distance", 1.0)),
            bbox=list(r.get("bbox")) if r.get("bbox") is not None else None,
        )
        for r in raw_results
    ]
    return RecognizeResponse(results=results)
