from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from aws.config import ATTENDANCE_TABLE, get_boto3_session_kwargs


class AttendanceLogger:
    """
    Stores attendance events inside the DynamoDB Attendance table.
    session_id is derived from the current UTC date so we keep at most one
    entry per user per day (similar to the former duplicate-prevention logic).
    """

    def __init__(self) -> None:
        session_kwargs = get_boto3_session_kwargs()
        dynamodb = boto3.resource("dynamodb", **session_kwargs)
        self.table = dynamodb.Table(ATTENDANCE_TABLE)

    def log(self, user_id: str, source: str = "camera") -> bool:
        timestamp = datetime.utcnow()
        session_id = timestamp.strftime("%Y%m%d")
        iso_timestamp = timestamp.isoformat()
        try:
            self.table.put_item(
                Item={
                    "session_id": session_id,
                    "face_id": user_id,
                    "timestamp": iso_timestamp,
                    "source": source,
                },
                ConditionExpression="attribute_not_exists(face_id)",
            )
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                # Already logged for this session (day)
                return False
            raise

    def get_last_event(self, user_id: str) -> Optional[Dict]:
        records = self.get_records({"user_id": user_id})
        if not records:
            return None
        return max(records, key=lambda row: row["timestamp"])

    def get_records(self, filters: Optional[Dict] = None) -> List[Dict]:
        filters = filters or {}
        items: List[Dict] = []
        response = self.table.scan()
        items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = self.table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        def _match(item: Dict) -> bool:
            if filters.get("user_id") and item.get("face_id") != filters["user_id"]:
                return False
            if filters.get("start_date") and item.get("timestamp", "") < filters["start_date"]:
                return False
            if filters.get("end_date") and item.get("timestamp", "") > filters["end_date"]:
                return False
            return True

        return [
            {
                "timestamp": item.get("timestamp"),
                "user_id": item.get("face_id"),
                "source": item.get("source"),
                "session_id": item.get("session_id"),
            }
            for item in items
            if _match(item)
        ]
