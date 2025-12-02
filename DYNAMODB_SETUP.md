# DynamoDB Integration Guide

This guide explains how to use AWS DynamoDB as the storage backend for attendance records in the Face Attendance System.

## Overview

The Face Attendance System now supports both:
- **CSV Storage** (default): Local file-based storage
- **DynamoDB**: AWS managed database service for scalable cloud storage

## Prerequisites

1. **AWS Account**: You need an active AWS account
2. **AWS Credentials**: Configure your AWS credentials locally
3. **boto3**: Already included in `requirements.txt`

## AWS Credentials Setup

### Option 1: AWS CLI Configuration (Recommended)

```bash
# Install AWS CLI if not already installed
brew install awscli

# Configure your credentials
aws configure

# You'll be prompted for:
# AWS Access Key ID: [your_access_key]
# AWS Secret Access Key: [your_secret_key]
# Default region name: us-east-1
# Default output format: json
```

### Option 2: Environment Variables

Create a `.env` file in the project root:

```bash
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
DYNAMODB_REGION=us-east-1
DYNAMODB_TABLE_NAME=attendance_records
STORAGE_TYPE=dynamodb
```

Or copy and modify the template:

```bash
cp .env.example.dynamodb .env
```

## Setting Up DynamoDB

### 1. Create the DynamoDB Table

Run the setup script:

```bash
python scripts/setup_dynamodb.py
```

This will:
- Create the `attendance_records` table if it doesn't exist
- Configure the table with the correct schema
- Display table information

### 2. Manual Table Creation (Alternative)

If you prefer to create the table manually via AWS Console:

1. Go to [AWS DynamoDB Console](https://console.aws.amazon.com/dynamodb/)
2. Click "Create table"
3. Table name: `attendance_records`
4. Partition key: `user_id` (String)
5. Sort key: `timestamp` (String)
6. Billing mode: Pay-per-request (recommended for variable workloads)
7. Click "Create"

## Initializing the System with DynamoDB

### Option 1: Modify `api/main.py`

```python
from core.system import ClassAttendanceSystem

system = ClassAttendanceSystem(
    users_dir="data/users",
    embeddings_file="data/known_faces.pkl",
    threshold=0.5,
    storage_type="dynamodb",
    dynamodb_table="attendance_records",
    dynamodb_region="us-east-1",
)
```

### Option 2: Use Environment Variables

Set the following environment variables before running:

```bash
export STORAGE_TYPE=dynamodb
export DYNAMODB_TABLE_NAME=attendance_records
export DYNAMODB_REGION=us-east-1
```

Then initialize with defaults:

```python
from core.system import ClassAttendanceSystem

system = ClassAttendanceSystem(
    users_dir="data/users",
    embeddings_file="data/known_faces.pkl",
)
```

## API Changes

All API endpoints remain the same. The storage mechanism is transparent:

### Get Attendance Records

```bash
curl "http://localhost:8000/attendance"

# Filter by user
curl "http://localhost:8000/attendance?user_id=john_doe"

# Filter by date range
curl "http://localhost:8000/attendance?start_date=2025-12-01T00:00:00&end_date=2025-12-02T23:59:59"
```

### Log Attendance

```bash
curl -X POST "http://localhost:8000/enroll" \
  -F "name=john_doe" \
  -F "image=@face.jpg"
```

## Usage Examples

### In Python Code

```python
from attendance.dynamodb_logger import DynamoDBLogger

# Initialize the logger
logger = DynamoDBLogger(
    table_name="attendance_records",
    region="us-east-1",
)

# Log an attendance record
logger.log("user_123", source="camera")

# Get last event for a user
last_event = logger.get_last_event("user_123")
print(last_event)

# Get all records for a user
records = logger.get_records({"user_id": "user_123"})
for record in records:
    print(record)

# Get records in a date range
records = logger.get_records({
    "start_date": "2025-12-01T00:00:00",
    "end_date": "2025-12-02T23:59:59",
})
```

### Configuration Management

```python
from configs.dynamodb_config import (
    create_attendance_table,
    get_table_info,
    delete_attendance_table,
)

# Create a table
result = create_attendance_table("attendance_records")
print(result)

# Get table information
info = get_table_info("attendance_records")
print(f"Item count: {info['item_count']}")
print(f"Table size: {info['table_size_bytes']} bytes")

# Delete table (WARNING: deletes all data!)
result = delete_attendance_table("attendance_records")
```

## DynamoDB Table Schema

The `attendance_records` table uses:

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| `user_id` | String | Partition Key | Unique identifier of the user |
| `timestamp` | String | Sort Key | ISO 8601 timestamp of the record |
| `source` | String | - | Source of the log (camera, web-ui, manual) |

### Indexes

- **Primary Index**: `user_id` (Partition) + `timestamp` (Sort)
  - Enables efficient queries for a user's records
  - Supports date range queries with sort key condition expressions

## Billing and Costs

DynamoDB with **Pay-per-request** billing:
- Read: $1.25 per million read units
- Write: $6.25 per million write units

For typical attendance logging:
- 100 employees checking in once per day = ~100 writes/day
- Daily reporting = ~100 reads/day
- Estimated monthly cost: < $1

## Troubleshooting

### Table Not Found Error

```
ResourceNotFoundException: Requested resource not found
```

**Solution**: Run the setup script to create the table:

```bash
python scripts/setup_dynamodb.py
```

### Access Denied Error

```
ClientError: An error occurred (AccessDenied) when calling the PutItem operation
```

**Solution**: Check your AWS credentials and ensure they have DynamoDB permissions:

```bash
# View current credentials
aws sts get-caller-identity

# Configure credentials
aws configure
```

### Connection Timeout

```
ConnectTimeout: Connection timed out
```

**Solution**: 
1. Check your internet connection
2. Verify AWS region is correct
3. Check if DynamoDB endpoint is accessible

## Monitoring

### View Logs via AWS CLI

```bash
# List recent writes
aws dynamodb scan --table-name attendance_records --limit 10

# Query a specific user's records
aws dynamodb query \
  --table-name attendance_records \
  --key-condition-expression "user_id = :uid" \
  --expression-attribute-values '{":uid":{"S":"john_doe"}}'
```

### CloudWatch Metrics

In the AWS Console:
1. Go to CloudWatch → Dashboards
2. View DynamoDB metrics for `attendance_records`
3. Monitor read/write capacity and throttled requests

## Migration from CSV to DynamoDB

To migrate existing CSV data to DynamoDB:

```python
from attendance.logger import AttendanceLogger
from attendance.dynamodb_logger import DynamoDBLogger

# Read from CSV
csv_logger = AttendanceLogger(storage_path="data/attendance.csv")
records = csv_logger.get_records()

# Write to DynamoDB
dynamodb_logger = DynamoDBLogger(table_name="attendance_records")
for record in records:
    dynamodb_logger.table.put_item(Item=record)

print(f"Migrated {len(records)} records to DynamoDB")
```

## Performance Considerations

### Query Optimization

The system uses:
- **Query operation** for user-specific lookups: O(log n) with proper index
- **Scan operation** for full table scans (use sparingly)

### Best Practices

1. **Always filter by `user_id` when possible** to use Query instead of Scan
2. **Implement caching** for frequently accessed data
3. **Use date ranges** to limit result sets
4. **Monitor CloudWatch metrics** for throttling

## Support and Further Reading

- [AWS DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)
- [boto3 DynamoDB Resource Guide](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
