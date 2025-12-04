# Lambda Function Deployment Guide

## Overview

This Lambda function enforces time-window restrictions for Cloud Computing course attendance. It only logs attendance during scheduled class times:

- **Thursday:** 14:40 - 18:40
- **Friday:** 08:00 - 11:00

## Prerequisites

1. AWS Account with permissions to create Lambda functions, API Gateway, and IAM roles
2. AWS CLI configured locally (optional, for CLI deployment)

## Deployment Steps

### Option 1: AWS Console (Recommended for beginners)

#### 1. Create IAM Role for Lambda

1. Go to AWS IAM Console → **Roles** → **Create role**
2. Select **AWS service** → **Lambda**
3. Attach policy: **AmazonDynamoDBFullAccess** (or create a custom policy with `dynamodb:PutItem` on your `Attendance` table)
4. Name the role: `CloudComputingAttendanceLambdaRole`
5. Create role

#### 2. Create the Lambda Function

1. Go to AWS Lambda Console → **Create function**
2. Choose **Author from scratch**
3. Configuration:
   - **Function name:** `CloudComputingAttendanceGate`
   - **Runtime:** Python 3.11
   - **Architecture:** x86_64
   - **Execution role:** Use existing role → Select `CloudComputingAttendanceLambdaRole`
4. Click **Create function**

#### 3. Upload Function Code

1. In the Lambda function page, scroll to **Code source**
2. Copy the entire contents of `cloud_computing_attendance.py`
3. Paste it into the `lambda_function.py` editor
4. Click **Deploy**

#### 4. Configure Environment Variables

1. Go to **Configuration** tab → **Environment variables** → **Edit**
2. Add:
   - `AWS_REGION`: `eu-north-1` (or your region)
   - `ATTENDANCE_TABLE`: `Attendance`
3. Save

#### 5. Create API Gateway Trigger

1. In the Lambda function page, click **Add trigger**
2. Select **API Gateway**
3. Configuration:
   - **API type:** REST API
   - **Security:** Open (or API key if you want auth)
   - **API name:** `CloudComputingAttendanceAPI`
   - **Deployment stage:** `prod`
4. Click **Add**
5. Copy the **API endpoint URL** (e.g., `https://abc123.execute-api.eu-north-1.amazonaws.com/prod/CloudComputingAttendanceGate`)

#### 6. Enable CORS (Important for browser access)

1. Go to API Gateway Console
2. Find your `CloudComputingAttendanceAPI`
3. Select the `POST` method under `/CloudComputingAttendanceGate`
4. Click **Actions** → **Enable CORS**
5. Enable CORS and confirm
6. Click **Actions** → **Deploy API** → Select `prod` stage

#### 7. Update Frontend

1. Open `webui/static/app.js`
2. Find the line:
   ```javascript
   const LAMBDA_ENDPOINT = "YOUR_LAMBDA_API_GATEWAY_URL_HERE";
   ```
3. Replace with your actual API Gateway URL:
   ```javascript
   const LAMBDA_ENDPOINT = "https://abc123.execute-api.eu-north-1.amazonaws.com/prod/CloudComputingAttendanceGate";
   ```
4. Save, commit, push to GitHub
5. Pull on EC2 and restart the service:
   ```bash
   cd ~/Face-Attendance_assignment
   git pull
   sudo systemctl restart face-attendance
   ```

### Option 2: AWS CLI Deployment

#### 1. Package the Lambda

```bash
cd lambda
zip function.zip cloud_computing_attendance.py
```

#### 2. Create the Lambda function

```bash
aws lambda create-function \
  --function-name CloudComputingAttendanceGate \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/CloudComputingAttendanceLambdaRole \
  --handler cloud_computing_attendance.lambda_handler \
  --zip-file fileb://function.zip \
  --environment Variables="{AWS_REGION=eu-north-1,ATTENDANCE_TABLE=Attendance}" \
  --region eu-north-1
```

#### 3. Create API Gateway and integrate

(Follow AWS documentation for REST API creation via CLI, or use the Console approach for simplicity)

## Testing

### Test in Lambda Console

1. Go to Lambda function → **Test** tab
2. Create a new test event with:
   ```json
   {
     "body": "{\"face_id\": \"TestUser\", \"source\": \"web-ui\"}"
   }
   ```
3. Click **Test**
4. **Expected behavior:**
   - If tested during class hours (Thu 14:40-18:40 or Fri 08:00-11:00): Status 200, attendance logged
   - If tested outside class hours: Status 403, error message

### Test from Browser

1. Open your web UI at `https://face.13.51.34.225.nip.io` (or your domain)
2. Stand in front of camera during class hours
3. Get recognized
4. Check browser console (F12) for:
   ```
   ✓ Cloud Computing attendance logged: Attendance logged for Cloud Computing
   ```
5. Verify in DynamoDB `Attendance` table:
   - New item with `course_name: "Cloud Computing"`
   - `session_start` and `session_end` populated

## Security Considerations

1. **API Key (Optional):** Add an API key to API Gateway to prevent abuse
2. **IAM Permissions:** Use least-privilege principle - only grant `dynamodb:PutItem` on the `Attendance` table
3. **Rate Limiting:** Configure API Gateway throttling to prevent spam
4. **Logging:** Enable CloudWatch Logs for debugging

## Troubleshooting

### "403 Forbidden" in browser

- Check CORS is enabled in API Gateway
- Verify the API endpoint URL is correct in `app.js`

### "500 Internal Server Error"

- Check Lambda CloudWatch Logs for Python errors
- Verify environment variables are set correctly
- Ensure IAM role has DynamoDB permissions

### Attendance not logging

- Check the Lambda execution time matches your local timezone
- Lambda uses UTC by default - you may need to adjust the schedule or convert timezones

### Testing outside class hours

- Temporarily modify the `SCHEDULE` dict in the Lambda code to include current time
- Or wait until actual class time to test

## Updating the Schedule

To change class times, modify `SCHEDULE` in `cloud_computing_attendance.py`:

```python
SCHEDULE = {
    3: [{"start": "14:40", "end": "18:40"}],  # Thursday (0=Mon, 3=Thu)
    4: [{"start": "08:00", "end": "11:00"}],  # Friday (4=Fri)
}
```

Redeploy the Lambda code after changes.

## Cost Estimate

- **Lambda:** ~$0.20/million requests (first 1M requests/month free)
- **API Gateway:** ~$3.50/million requests (first 1M requests/month free)
- **DynamoDB writes:** Covered by on-demand pricing or free tier

For a single course with ~50 students checking in twice/week: **< $0.01/month** (essentially free).

