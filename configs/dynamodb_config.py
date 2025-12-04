"""
DynamoDB configuration and utilities for the Face Attendance System.

This module provides utilities for setting up and managing DynamoDB tables
for attendance logging.
"""

from __future__ import annotations

import boto3
from botocore.exceptions import ClientError


def create_attendance_table(
    table_name: str = "attendance_records",
    region: str = "us-east-1",
) -> dict:
    """
    Create the DynamoDB table for attendance records if it doesn't exist.
    
    Args:
        table_name: Name of the table to create
        region: AWS region
        
    Returns:
        Dictionary with table creation status
    """
    dynamodb = boto3.resource("dynamodb", region_name=region)
    
    try:
        table = dynamodb.Table(table_name)
        table.load()
        return {
            "status": "exists",
            "message": f"Table '{table_name}' already exists",
            "table_name": table_name,
        }
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            try:
                table = dynamodb.create_table(
                    TableName=table_name,
                    KeySchema=[
                        {"AttributeName": "user_id", "KeyType": "HASH"},
                        {"AttributeName": "timestamp", "KeyType": "RANGE"},
                    ],
                    AttributeDefinitions=[
                        {"AttributeName": "user_id", "AttributeType": "S"},
                        {"AttributeName": "timestamp", "AttributeType": "S"},
                    ],
                    BillingMode="PAY_PER_REQUEST",
                    Tags=[
                        {"Key": "Application", "Value": "FaceAttendance"},
                        {"Key": "Environment", "Value": "Production"},
                    ],
                )
                # Wait for table to be created
                table.wait_until_exists()
                return {
                    "status": "created",
                    "message": f"Table '{table_name}' created successfully",
                    "table_name": table_name,
                }
            except ClientError as create_error:
                return {
                    "status": "error",
                    "message": str(create_error),
                    "table_name": table_name,
                }
        else:
            return {
                "status": "error",
                "message": str(e),
                "table_name": table_name,
            }


def delete_attendance_table(
    table_name: str = "attendance_records",
    region: str = "us-east-1",
) -> dict:
    """
    Delete the DynamoDB table for attendance records.
    
    WARNING: This will permanently delete all attendance data!
    
    Args:
        table_name: Name of the table to delete
        region: AWS region
        
    Returns:
        Dictionary with deletion status
    """
    dynamodb = boto3.resource("dynamodb", region_name=region)
    
    try:
        table = dynamodb.Table(table_name)
        table.delete()
        table.wait_until_not_exists()
        return {
            "status": "deleted",
            "message": f"Table '{table_name}' deleted successfully",
            "table_name": table_name,
        }
    except ClientError as e:
        return {
            "status": "error",
            "message": str(e),
            "table_name": table_name,
        }


def get_table_info(
    table_name: str = "attendance_records",
    region: str = "eu-north-1",
) -> dict:
    """
    Get information about the DynamoDB table.
    
    Args:
        table_name: Name of the table
        region: AWS region
        
    Returns:
        Dictionary with table information
    """
    dynamodb = boto3.resource("dynamodb", region_name=region)
    
    try:
        table = dynamodb.Table(table_name)
        table.load()
        return {
            "status": "success",
            "table_name": table.name,
            "item_count": table.item_count,
            "table_status": table.table_status,
            "table_size_bytes": table.table_size_bytes,
            "arn": table.table_arn,
        }
    except ClientError as e:
        return {
            "status": "error",
            "message": str(e),
            "table_name": table_name,
        }
