# api/models/schemas.py
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class RegisterResponse(BaseModel):
    success: bool
    message: str


class RecognizeResult(BaseModel):
    user_id: str
    distance: float = Field(..., ge=0)
    bbox: Optional[List[int]] = None   # [top, right, bottom, left]


class RecognizeResponse(BaseModel):
    results: List[RecognizeResult]


class AttendanceRecord(BaseModel):
    timestamp: str
    user_id: str
    source: str


class AttendanceResponse(BaseModel):
    records: List[AttendanceRecord]


class UserInfo(BaseModel):
    user_id: str
    photo_count: int = Field(..., ge=0)


class UsersResponse(BaseModel):
    users: List[UserInfo]


class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    embeddings_loaded: bool
    known_users: int
