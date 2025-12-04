"""
AWS Lambda function for Cloud Computing course attendance gating.
Ensures attendance can only be logged during scheduled class times.

Schedule:
- Thursday: 14:40 - 18:40
- Friday: 08:00 - 11:00

Deploy: zip this file with dependencies and upload to Lambda console.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

# Initialize DynamoDB resource
REGION = os.getenv("AWS_REGION", "eu-north-1")
ATTENDANCE_TABLE_NAME = os.getenv("ATTENDANCE_TABLE", "Attendance")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
attendance_table = dynamodb.Table(ATTENDANCE_TABLE_NAME)

COURSE_NAME = "Cloud Computing"

# Schedule: weekday -> list of time windows
# Weekday: 0=Monday, 1=Tuesday, ..., 4=Thursday, 5=Friday
SCHEDULE = {
    3: [{"start": "14:40", "end": "18:40"}],  # Thursday
    4: [{"start": "08:00", "end": "11:00"}],  # Friday
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for course-specific attendance logging.
    
    Expected request body:
    {
        "face_id": "user_name",
        "source": "web-ui"  (optional)
    }
    """
    # Parse request body
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Invalid JSON in request body"}),
        }

    face_id = body.get("face_id")
    source = body.get("source", "web-ui")

    if not face_id:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "face_id is required"}),
        }

    # Get current time
    now = datetime.now(timezone.utc)
    weekday = now.weekday()
    current_time = now.strftime("%H:%M")

    # Check if current time falls within a valid class window
    valid = False
    session_start = None
    session_end = None

    if weekday in SCHEDULE:
        for slot in SCHEDULE[weekday]:
            if slot["start"] <= current_time <= slot["end"]:
                valid = True
                session_start = f"{now.date()} {slot['start']}"
                session_end = f"{now.date()} {slot['end']}"
                break

    if not valid:
        return {
            "statusCode": 403,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": f"Attendance for {COURSE_NAME} can only be logged during class hours.",
                "schedule": "Thursday 14:40-18:40, Friday 08:00-11:00"
            }),
        }

    # Prepare attendance record
    session_id = now.strftime("%Y%m%d")
    timestamp = now.isoformat()

    try:
        # Write to DynamoDB with conditional check to prevent duplicates
        attendance_table.put_item(
            Item={
                "session_id": session_id,
                "face_id": face_id,
                "timestamp": timestamp,
                "source": source,
                "course_name": COURSE_NAME,
                "session_start": session_start,
                "session_end": session_end,
            },
            ConditionExpression="attribute_not_exists(face_id)",
        )
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "message": f"Attendance logged for {COURSE_NAME}",
                "face_id": face_id,
                "session_id": session_id,
                "course": COURSE_NAME,
            }),
        }

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        
        if error_code == "ConditionalCheckFailedException":
            # Already logged for this session
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "message": "Already logged for this session",
                    "face_id": face_id,
                }),
            }
        
        # Other DynamoDB errors
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Failed to log attendance",
                "details": str(e),
            }),
        }

