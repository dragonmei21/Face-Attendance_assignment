"""
DynamoDB-based attendance logger for the Face Attendance System.

This module provides a logger that stores attendance records in AWS DynamoDB
instead of local CSV files. It maintains the same interface as AttendanceLogger
for seamless integration.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError


class DynamoDBLogger:
    """
    Attendance logger backed by AWS DynamoDB.
    
    Attributes:
        table_name: Name of the DynamoDB table
        region: AWS region (default: us-east-1)
    """

    def __init__(
        self,
        table_name: str = "attendance_records",
        region: str = "us-east-1",
        create_table: bool = False,
    ) -> None:
        """
        Initialize the DynamoDB logger.
        
        Args:
            table_name: Name of the DynamoDB table to use
            region: AWS region for DynamoDB
            create_table: If True, create the table if it doesn't exist
        """
        self.table_name = table_name
        self.region = region
        
        # Initialize DynamoDB client and resource
        self.dynamodb = boto3.resource("dynamodb", region_name=region)
        self.table = self.dynamodb.Table(table_name)
        
        if create_table:
            self._ensure_table_exists()

    def _ensure_table_exists(self) -> None:
        """Create the DynamoDB table if it doesn't exist."""
        try:
            # Check if table exists
            self.table.load()
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                # Create the table
                self.dynamodb.create_table(
                    TableName=self.table_name,
                    KeySchema=[
                        {"AttributeName": "user_id", "KeyType": "HASH"},
                        {"AttributeName": "timestamp", "KeyType": "RANGE"},
                    ],
                    AttributeDefinitions=[
                        {"AttributeName": "user_id", "AttributeType": "S"},
                        {"AttributeName": "timestamp", "AttributeType": "S"},
                    ],
                    BillingMode="PAY_PER_REQUEST",
                )
                # Wait for table to be created
                self.table.wait_until_exists()
            else:
                raise

    def log(self, user_id: str, source: str = "camera") -> bool:
        """
        Log an attendance record for a user.
        
        Args:
            user_id: ID of the user
            source: Source of the log (e.g., 'camera', 'web-ui', 'manual')
            
        Returns:
            True if the record was logged, False if it's a duplicate
        """
        if self.is_duplicate(user_id):
            return False

        timestamp = datetime.utcnow().isoformat()
        
        try:
            self.table.put_item(
                Item={
                    "user_id": user_id,
                    "timestamp": timestamp,
                    "source": source,
                }
            )
            return True
        except ClientError as e:
            raise RuntimeError(f"Failed to write to DynamoDB: {e}")

    def is_duplicate(self, user_id: str, interval_minutes: int = 5) -> bool:
        """
        Check if there's a recent attendance record for the user.
        
        Args:
            user_id: ID of the user
            interval_minutes: Minimum interval between records (default: 5 minutes)
            
        Returns:
            True if a record exists within the interval, False otherwise
        """
        last_event = self.get_last_event(user_id)
        if not last_event:
            return False
        last_time = datetime.fromisoformat(last_event["timestamp"])
        return datetime.utcnow() - last_time < timedelta(minutes=interval_minutes)

    def get_last_event(self, user_id: str) -> Optional[Dict]:
        """
        Get the most recent attendance record for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary with the last event or None if no events exist
        """
        records = self.get_records({"user_id": user_id})
        return records[-1] if records else None

    def get_records(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Get attendance records matching the given filters.
        
        Args:
            filters: Dictionary with optional keys:
                - user_id: Filter by specific user
                - start_date: Filter records after this ISO timestamp
                - end_date: Filter records before this ISO timestamp
                
        Returns:
            List of attendance records
        """
        filters = filters or {}
        rows: List[Dict] = []

        try:
            if "user_id" in filters:
                # Query by user_id (partition key)
                response = self.table.query(
                    KeyConditionExpression="user_id = :user_id",
                    ExpressionAttributeValues={":user_id": filters["user_id"]},
                )
                items = response.get("Items", [])
            else:
                # Scan the entire table (less efficient)
                response = self.table.scan()
                items = response.get("Items", [])

            # Apply date range filters
            for item in items:
                if filters.get("start_date"):
                    if item["timestamp"] < filters["start_date"]:
                        continue
                if filters.get("end_date"):
                    if item["timestamp"] > filters["end_date"]:
                        continue
                rows.append(item)

            # Sort by timestamp in ascending order
            rows.sort(key=lambda x: x["timestamp"])
            return rows

        except ClientError as e:
            raise RuntimeError(f"Failed to query DynamoDB: {e}")
