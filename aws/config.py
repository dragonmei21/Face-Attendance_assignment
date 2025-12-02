from __future__ import annotations

import os

AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")
S3_BUCKET = os.getenv("S3_BUCKET", "facerecognition")
FACES_TABLE = os.getenv("FACES_TABLE", "FacesTable")
ATTENDANCE_TABLE = os.getenv("ATTENDANCE_TABLE", "Attendance")

def get_boto3_session_kwargs() -> dict:
    """
    Provide common keyword arguments when instantiating boto3 clients/resources.
    Currently only region, but hook for future credentials/profile injection.
    """
    return {"region_name": AWS_REGION}

