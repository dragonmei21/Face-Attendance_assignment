from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


class AttendanceLogger:
    def __init__(self, storage_type: str = "csv", storage_path: str = "data/attendance.csv") -> None:
        if storage_type != "csv":
            raise ValueError("Only CSV storage is supported in Phase 1.")
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("timestamp,user_id,source\n")

    def log(self, user_id: str, source: str = "camera") -> bool:
        timestamp = datetime.utcnow().isoformat()
        if self.is_duplicate(user_id):
            return False
        with self.storage_path.open("a", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow([timestamp, user_id, source])
        return True

    def is_duplicate(self, user_id: str, interval_minutes: int = 5) -> bool:
        last_event = self.get_last_event(user_id)
        if not last_event:
            return False
        last_time = datetime.fromisoformat(last_event["timestamp"])
        return datetime.utcnow() - last_time < timedelta(minutes=interval_minutes)

    def get_last_event(self, user_id: str) -> Optional[Dict]:
        records = self.get_records({"user_id": user_id})
        return records[-1] if records else None

    def get_records(self, filters: Optional[Dict] = None) -> List[Dict]:
        filters = filters or {}
        rows: List[Dict] = []
        with self.storage_path.open("r", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                user = row.get("user_id")
                if not user:
                    continue
                if filters.get("user_id") and user != filters["user_id"]:
                    continue
                if filters.get("start_date"):
                    if row["timestamp"] < filters["start_date"]:
                        continue
                if filters.get("end_date"):
                    if row["timestamp"] > filters["end_date"]:
                        continue
                rows.append(row)
        return rows
