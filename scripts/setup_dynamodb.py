#!/usr/bin/env python3
"""
Setup script to initialize DynamoDB for the Face Attendance System.

Usage:
    python scripts/setup_dynamodb.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from configs.dynamodb_config import create_attendance_table, get_table_info
from dotenv import load_dotenv


def main():
    """Set up DynamoDB for the Face Attendance System."""
    # Load environment variables
    load_dotenv()
    
    table_name = os.getenv("DYNAMODB_TABLE_NAME", "attendance_records")
    region = os.getenv("DYNAMODB_REGION", "us-east-1")
    
    print("🚀 Setting up DynamoDB for Face Attendance System")
    print(f"   Region: {region}")
    print(f"   Table: {table_name}")
    print()
    
    # Create the table
    result = create_attendance_table(table_name=table_name, region=region)
    
    if result["status"] == "created":
        print(f"✅ {result['message']}")
    elif result["status"] == "exists":
        print(f"ℹ️  {result['message']}")
    else:
        print(f"❌ Error: {result['message']}")
        sys.exit(1)
    
    print()
    
    # Get table info
    info = get_table_info(table_name=table_name, region=region)
    if info["status"] == "success":
        print("📊 Table Information:")
        print(f"   Name: {info['table_name']}")
        print(f"   Status: {info['table_status']}")
        print(f"   Item Count: {info['item_count']}")
        print(f"   Size: {info['table_size_bytes']} bytes")
        print(f"   ARN: {info['arn']}")
    else:
        print(f"❌ Error getting table info: {info['message']}")
        sys.exit(1)
    
    print()
    print("✅ DynamoDB setup complete!")


if __name__ == "__main__":
    main()
