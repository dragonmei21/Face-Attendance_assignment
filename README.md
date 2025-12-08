# Face Recognition Attendance System

An AI-powered attendance tracking system that uses facial recognition to automatically log student attendance. Built with Python, FastAPI, and deployed on AWS cloud infrastructure.

## 🎯 Features

- **Real-time Face Recognition**: Webcam-based attendance tracking with instant recognition
- **Web-based Interface**: Modern, responsive UI for enrollment and attendance viewing
- **Cloud Deployment**: Scalable AWS architecture with Lambda, DynamoDB, EC2, and S3
- **Course-Specific Attendance**: Time-window restrictions for scheduled classes
- **Automatic Duplicate Detection**: Prevents multiple check-ins within a time window
- **CSV Export**: Download attendance reports for specific courses and dates

## 🏗️ Architecture

### Cloud Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      Frontend Layer                       │
│  ┌────────────┐              ┌─────────────────┐        │
│  │  S3 Static │◄─────────────│  CloudFront CDN │        │
│  │  Website   │              │  (HTTPS)        │        │
│  └────────────┘              └─────────────────┘        │
└────────────────────────┬─────────────────────────────────┘
                         │
                         │ HTTPS API Calls
                         ▼
┌──────────────────────────────────────────────────────────┐
│                     Compute Layer                         │
│  ┌────────────────────────────────────────────────┐     │
│  │  EC2 Instance (FastAPI)                        │     │
│  │  ┌──────────────┐  ┌──────────────────────┐   │     │
│  │  │ Face         │  │ Recognition Engine   │   │     │
│  │  │ Detection    │→ │ (embedding matching) │   │     │
│  │  └──────────────┘  └──────────────────────┘   │     │
│  │  ┌──────────────┐  ┌──────────────────────┐   │     │
│  │  │ Embedding    │  │ Attendance Logic     │   │     │
│  │  │ Generation   │  │                      │   │     │
│  │  └──────────────┘  └──────────────────────┘   │     │
│  └────────────────────────────────────────────────┘     │
└────────────┬──────────────────────┬──────────────────────┘
             │                      │
             ▼                      ▼
┌──────────────────────┐  ┌──────────────────────┐
│   Storage Layer      │  │   Lambda Function    │
│  ┌────────────────┐  │  │  ┌────────────────┐  │
│  │  S3 Bucket     │  │  │  │  Time Window   │  │
│  │  - User Photos │  │  │  │  Validation    │  │
│  │  - Embeddings  │  │  │  └────────────────┘  │
│  └────────────────┘  │  │  └────────────────┘  │
│  ┌────────────────┐  │  │                      │
│  │  DynamoDB      │  │  │                      │
│  │  - Attendance  │  │  │                      │
│  │  - Embeddings  │  │  │                      │
│  └────────────────┘  │  │                      │
└──────────────────────┘  └──────────────────────┘
```

## ☁️ Cloud Deployment

### AWS Services Used

1. **EC2 Instance**: Hosts the FastAPI backend server
   - Instance type: t3.medium or t3.large
   - Runs uvicorn server with nginx reverse proxy
   - Handles face recognition and embedding generation

2. **DynamoDB**: NoSQL database for attendance records and embeddings
   - `Attendance` table: Stores attendance logs with course information
   - `FacesTable`: Stores user embeddings (optional, can use local pickle files)
   - On-demand billing for scalability

3. **S3 Bucket**: Object storage for user photos and static website
   - Stores uploaded user images
   - Hosts static web UI files
   - Configured with CloudFront CDN for fast global access

4. **AWS Lambda**: Serverless function for course-specific attendance gating
   - Enforces time-window restrictions (e.g., only during class hours)
   - Integrated with API Gateway for HTTP access
   - Prevents duplicate check-ins per session

5. **API Gateway**: REST API endpoint for Lambda function
   - Provides HTTPS endpoint for attendance logging
   - CORS enabled for browser access

### Deployment Steps

#### 1. EC2 Setup

```bash
# Launch EC2 instance (Ubuntu 22.04 LTS recommended)
# Configure security group: Allow HTTP (80), HTTPS (443), SSH (22)

# SSH into instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Install dependencies
sudo apt update
sudo apt install -y python3-pip python3-venv nginx

# Clone repository
git clone <your-repo-url>
cd "Face Rcognition Cloud Computing"

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Configure AWS credentials (via IAM role or environment variables)
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=eu-north-1
```

#### 2. Configure Nginx

Create `/etc/nginx/sites-available/face-attendance`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable and start:

```bash
sudo ln -s /etc/nginx/sites-available/face-attendance /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 3. Run FastAPI as Systemd Service

Create `/etc/systemd/system/face-attendance.service`:

```ini
[Unit]
Description=Face Attendance API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/Face-Rcognition-Cloud-Computing
Environment="PATH=/home/ubuntu/Face-Rcognition-Cloud-Computing/venv/bin"
ExecStart=/home/ubuntu/Face-Rcognition-Cloud-Computing/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable face-attendance
sudo systemctl start face-attendance
```

#### 4. DynamoDB Setup

```bash
# Run setup script
python scripts/setup_dynamodb.py

# Or manually create tables via AWS Console:
# - Table: Attendance
#   Partition Key: session_id (String)
#   Sort Key: face_id (String)
#   Attributes: timestamp, source, course_name, session_start, session_end
```

#### 5. Lambda Function Deployment

Follow the detailed guide in [`lambda/README.md`](lambda/README.md):

1. Create IAM role with DynamoDB write permissions
2. Create Lambda function (Python 3.11)
3. Upload `lambda/cloud_computing_attendance.py` code
4. Configure environment variables:
   - `AWS_REGION`: eu-north-1
   - `ATTENDANCE_TABLE`: Attendance
5. Create API Gateway trigger
6. Enable CORS
7. Update frontend with API Gateway URL

#### 6. S3 Static Website Hosting (Optional)

```bash
# Create S3 bucket
aws s3 mb s3://your-bucket-name

# Upload web UI files
aws s3 sync webui/ s3://your-bucket-name --acl public-read

# Configure static website hosting
aws s3 website s3://your-bucket-name --index-document index.html
```

## 🚀 Setting Up for Your School

### Step 1: Configure Course Schedule

Edit `lambda/cloud_computing_attendance.py` to set your class times:

```python
SCHEDULE = {
    0: [{"start": "09:00", "end": "12:00"}],  # Monday
    2: [{"start": "14:00", "end": "17:00"}],  # Wednesday
    # Add more days as needed
}
```

Redeploy the Lambda function after changes.

### Step 2: Update Environment Variables

Set these on your EC2 instance or in your deployment:

```bash
export AWS_REGION=your-region
export S3_BUCKET=your-bucket-name
export FACES_TABLE=FacesTable
export ATTENDANCE_TABLE=Attendance
```

### Step 3: Customize Web UI

Edit `webui/index.html` and `webui/static/app.js`:

- Update school logo: Replace `webui/static/esade-logo.png`
- Change branding text: Edit hero section in `index.html`
- Update Lambda endpoint: Set `LAMBDA_ENDPOINT` in `app.js`

### Step 4: Initial User Enrollment

1. Access the web interface at `http://your-ec2-ip` or your domain
2. Stand in front of the camera
3. Enter your name when prompted
4. Click "Enroll" to add yourself to the system

### Step 5: Build Embeddings Database

```bash
# Run embedding builder script
python scripts/build_embeddings.py

# This processes all images in data/users/ and creates known_faces.pkl
```

## 📖 Usage

### Web Interface

1. **Check-in**: Stand in front of the camera - attendance is logged automatically if recognized
2. **Enroll New User**: 
   - Stand in front of camera
   - Enter name when prompted
   - Click "Enroll"
3. **View Attendance**: Access `/attendance` endpoint or download CSV reports

### API Endpoints

```bash
# Health check
GET /health

# Recognize face in uploaded image
POST /recognize
Content-Type: multipart/form-data
Body: image file

# Enroll new user
POST /enroll
Content-Type: multipart/form-data
Body: name (string), image (file)

# Get attendance records
GET /attendance?start_date=2025-01-01&end_date=2025-01-31&user_id=John

# Download Cloud Computing attendance CSV
GET /download/cloud-computing?session_date=20250115
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Build embeddings from user photos
python scripts/build_embeddings.py

# Run API server locally
uvicorn api.main:app --reload

# Access at http://localhost:8000
```

## 🔧 Configuration

### Recognition Threshold

Adjust in `core/system.py`:

```python
system = ClassAttendanceSystem(threshold=0.5)  # Lower = more lenient
```

### Storage Backend

Switch between CSV and DynamoDB in `attendance/logger.py`:

```python
# CSV (local)
logger = AttendanceLogger(storage_path="data/attendance.csv")

# DynamoDB (cloud)
from attendance.dynamodb_logger import DynamoDBLogger
logger = DynamoDBLogger(table_name="Attendance", region="eu-north-1")
```

## 📁 Project Structure

```
.
├── api/                    # FastAPI application
│   ├── main.py            # Main API entry point
│   ├── routes/            # API endpoint modules
│   └── models/            # Pydantic schemas
├── attendance/            # Attendance logging modules
│   ├── logger.py         # CSV logger
│   └── dynamodb_logger.py # DynamoDB logger
├── embeddings/            # Face embedding management
│   └── manager.py        # Embedding generation and storage
├── recognition/          # Face recognition engine
│   └── face_recognizer.py
├── lambda/               # AWS Lambda function
│   └── cloud_computing_attendance.py
├── webui/                # Frontend web interface
│   ├── index.html
│   └── static/
├── scripts/              # Utility scripts
│   ├── build_embeddings.py
│   └── setup_dynamodb.py
└── data/                 # User photos and data
    ├── users/           # User photo directories
    └── known_faces.pkl  # Embeddings database
```

## 🔐 Security Considerations

- **API Authentication**: Consider adding API keys to API Gateway
- **IAM Permissions**: Use least-privilege IAM roles
- **HTTPS**: Configure SSL certificate for production (Let's Encrypt recommended)
- **Rate Limiting**: Configure API Gateway throttling
- **CORS**: Only allow requests from your domain

## 💰 Cost Estimate

For a typical school deployment:

- **EC2 (t3.medium)**: ~$30/month
- **DynamoDB**: < $1/month (on-demand pricing)
- **S3**: < $1/month (standard storage)
- **Lambda**: < $0.01/month (first 1M requests free)
- **API Gateway**: < $0.01/month (first 1M requests free)

**Total**: ~$32/month for a single course with 50-100 students

## 🐛 Troubleshooting

### Face Not Recognized

- Ensure good lighting and clear face visibility
- Check that user is enrolled with multiple clear photos
- Lower recognition threshold if too strict

### Lambda Returns 403

- Verify current time is within scheduled class hours
- Check timezone settings (Lambda uses UTC)
- Review schedule configuration in Lambda code

### DynamoDB Access Denied

- Verify IAM role has DynamoDB permissions
- Check AWS credentials are configured correctly
- Ensure table names match environment variables

### EC2 Service Not Starting

```bash
# Check service status
sudo systemctl status face-attendance

# View logs
sudo journalctl -u face-attendance -f

# Check for port conflicts
sudo netstat -tulpn | grep 8000
```

## 📚 Documentation

- [DynamoDB Setup Guide](DYNAMODB_SETUP.md)
- [Lambda Deployment Guide](lambda/README.md)
- [Project Overview](project_overview.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is open source and available for educational use.

## 🙏 Acknowledgments

Built using:
- [face_recognition](https://github.com/ageitgey/face_recognition) library
- [FastAPI](https://fastapi.tiangolo.com/) web framework
- [AWS](https://aws.amazon.com/) cloud services

---

**Note**: This system is designed for educational purposes. Ensure compliance with privacy regulations (GDPR, FERPA, etc.) when deploying in production environments.

