# api/routes/logs.py
from __future__ import annotations

from typing import Optional, Dict, Any

from fastapi import APIRouter, Query, HTTPException

from api.context import system
from api.models.schemas import AttendanceResponse, AttendanceRecord

router = APIRouter()


@router.get("/attendance", response_model=AttendanceResponse)
async def get_attendance(
    user_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, description="ISO timestamp or date"),
    end_date: Optional[str] = Query(None, description="ISO timestamp or date"),
) -> AttendanceResponse:
    filters: Dict[str, Any] = {}
    if user_id:
        filters["user_id"] = user_id
    if start_date:
        filters["start_date"] = start_date
    if end_date:
        filters["end_date"] = end_date

    try:
        rows = system.logger.get_records(filters)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch attendance records: {e}")

    records = [AttendanceRecord(**row) for row in rows]
    return AttendanceResponse(records=records)
