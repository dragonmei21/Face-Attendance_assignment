## Phase 1: Local Prototype - Core Functionality

- [ ] 1. Set up project structure and environment
  - Create directory structure: face_attendance/data/users/, data/test_images/, src/
  - Create requirements.txt with face_recognition, opencv-python, numpy
  - Set up virtual environment with Python 3.x
  - Create __init__.py files for proper package structure
  - _Requirements: 1.1, 1.3_

- [ ] 2. Implement embedding builder module
  - [ ] 2.1 Create EmbeddingManager class in src/embeddings.py
    - Implement __init__ to accept users_dir and storage_path parameters
    - Implement build_database() to scan user folders and generate embeddings
    - Implement load() to read embeddings from pickle file
    - Implement save() to persist embeddings to pickle file
    - Add error handling for missing folders and invalid images
    - _Requirements: 1.1, 1.2, 1.3, 1.5_
  
  - [ ] 2.2 Create build_embeddings.py script
    - Import EmbeddingManager class
    - Scan data/users/ directory for user folders
    - For each user folder, process all images and generate embeddings
    - Save all embeddings to known_faces.pkl
    - Print progress and summary of processed users
    - _Requirements: 1.1, 1.3_

- [ ] 3. Implement face recognition module
  - [ ] 3.1 Create FaceRecognizer class in src/recognition.py
    - Implement __init__ to load embeddings and set threshold
    - Implement detect_faces() using face_recognition library
    - Implement get_embedding() to generate 128-d vector from face
    - Implement match_embedding() with nearest-neighbor distance calculation
    - Implement recognize() method for image file input
    - Implement recognize_frame() method for numpy array input
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  
  - [ ] 3.2 Create recognize.py script for testing
    - Accept image path as command line argument
    - Load embeddings from known_faces.pkl
    - Run recognition and print results with user_id and distance
    - Display "Unknown" for unrecognized faces
    - _Requirements: 2.1, 2.4, 2.5_

- [ ] 4. Implement attendance logging module
  - [ ] 4.1 Create AttendanceLogger class in src/attendance.py
    - Implement __init__ to configure storage type (CSV or SQLite)
    - Implement log() method to write attendance records
    - Implement is_duplicate() to check for recent detections (5 min window)
    - Implement get_last_event() to retrieve most recent record for a user
    - Implement get_records() with filtering by date range and user_id
    - Create CSV file with headers: timestamp, user_id, source
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 5. Implement unified class wrapper
  - [ ] 5.1 Create ClassAttendanceSystem in src/utils.py
    - Implement __init__ with configurable paths and threshold
    - Initialize EmbeddingManager, FaceRecognizer, and AttendanceLogger
    - Implement build_database() wrapper method
    - Implement recognize() wrapper method
    - Implement log_attendance() wrapper method
    - Add configuration validation and error handling
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 6. Implement webcam recognition module
  - [ ] 6.1 Create webcam.py script
    - Import OpenCV for video capture
    - Implement start_webcam_recognition() with frame skip parameter
    - Implement process_frame() to run recognition every Nth frame
    - Implement display_results() to draw bounding boxes and labels
    - Add keyboard controls (q to quit, s to save frame)
    - Auto-log attendance when face is recognized
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 7. Create sample data and test the system
  - [ ] 7.1 Add sample user photos
    - Create folders for 3 test users in data/users/
    - Add 2-3 clear face photos per user
    - Ensure photos meet quality requirements (clear, well-lit, straight angle)
    - _Requirements: 1.4_
  
  - [ ] 7.2 Test embedding generation
    - Run build_embeddings.py script
    - Verify known_faces.pkl is created
    - Check that all users are processed successfully
    - _Requirements: 1.1, 1.2, 1.3_
  
  - [ ] 7.3 Test recognition with test images
    - Add test images to data/test_images/
    - Run recognize.py on test images
    - Verify correct user identification and distance scores
    - Test with unknown faces to verify "Unknown" response
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  
  - [ ] 7.4 Test attendance logging
    - Run recognition multiple times for same user
    - Verify first detection logs attendance
    - Verify duplicate detections within 5 minutes are ignored
    - Check attendance.csv for correct records
    - _Requirements: 3.1, 3.2, 3.3_

## Phase 2: API Layer

- [ ] 8. Set up FastAPI project structure
  - [ ] 8.1 Create API directory structure
    - Create src/api/ directory with __init__.py
    - Create src/api/main.py for FastAPI app
    - Create src/api/routes/ for endpoint modules
    - Create src/api/models/ for Pydantic schemas
    - Update requirements.txt with fastapi, uvicorn, python-multipart
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 9. Implement API endpoints
  - [ ] 9.1 Create POST /register_face endpoint in src/api/routes/register.py
    - Accept user_id and image file upload
    - Save image to data/users/{user_id}/ directory
    - Trigger embedding generation for new user
    - Return success/failure response
    - _Requirements: 6.1_
  
  - [ ] 9.2 Create POST /recognize endpoint in src/api/routes/recognize.py
    - Accept image file upload
    - Run face recognition on uploaded image
    - Return list of recognized users with confidence scores
    - Handle multiple faces in single image
    - _Requirements: 6.2_
  
  - [ ] 9.3 Create GET /attendance endpoint in src/api/routes/logs.py
    - Accept query parameters: start_date, end_date, user_id
    - Retrieve attendance records from storage
    - Return filtered records as JSON
    - _Requirements: 6.3_
  
  - [ ] 9.4 Create GET /users endpoint in src/api/routes/users.py
    - List all registered users
    - Include photo count for each user
    - Return users list as JSON
    - _Requirements: 6.4_
  
  - [ ] 9.5 Create GET /health endpoint in src/api/main.py
    - Return system status and uptime
    - Check if embedding database is loaded
    - Return health check response
    - _Requirements: 6.5_

- [ ] 10. Create Pydantic models and integrate with core modules
  - [ ] 10.1 Define request/response schemas in src/api/models/
    - Create RegisterRequest, RecognizeResponse schemas
    - Create AttendanceRecord, UserInfo schemas
    - Add validation rules for all fields
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  
  - [ ] 10.2 Wire API endpoints to core modules
    - Import ClassAttendanceSystem in main.py
    - Initialize system on app startup
    - Connect endpoints to system methods
    - Add error handling and logging
    - _Requirements: 5.1, 5.2, 5.3, 6.1, 6.2, 6.3_

- [ ] 11. Test API locally
  - [ ] 11.1 Start FastAPI server and test endpoints
    - Run uvicorn server locally
    - Test POST /register_face with sample images
    - Test POST /recognize with test images
    - Test GET /attendance with various filters
    - Test GET /users and GET /health endpoints
    - Verify all responses match expected schemas
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

## Phase 3: Cloud Deployment (AWS)

- [ ] 12. Set up AWS S3 for photo storage
  - [ ] 12.1 Create S3 bucket and configure structure
    - Create S3 bucket with appropriate naming
    - Set up folder structure: users/, uploads/
    - Configure bucket permissions and CORS
    - Update requirements.txt with boto3
    - _Requirements: 7.1_
  
  - [ ] 12.2 Modify EmbeddingManager to use S3
    - Add S3 client initialization
    - Implement upload_photo() to save images to S3
    - Implement download_photo() to retrieve images from S3
    - Update build_database() to work with S3 paths
    - _Requirements: 7.1_

- [ ] 13. Set up DynamoDB for embeddings and attendance
  - [ ] 13.1 Create DynamoDB tables
    - Create user_embeddings table with user_id as partition key
    - Create attendance_records table with timestamp as partition key and user_id as sort key
    - Add GSI on date field for attendance_records
    - Configure on-demand pricing
    - _Requirements: 7.2, 7.3_
  
  - [ ] 13.2 Modify storage modules to use DynamoDB
    - Update EmbeddingManager to read/write from user_embeddings table
    - Update AttendanceLogger to write to attendance_records table
    - Implement batch operations for efficiency
    - Add retry logic for throttling
    - _Requirements: 7.2, 7.3_

- [ ] 14. Deploy FastAPI backend to EC2
  - [ ] 14.1 Set up EC2 instance
    - Launch EC2 instance (t3.medium or t3.large)
    - Configure security groups for HTTP/HTTPS access
    - Install Python, dependencies, and system packages
    - Set up environment variables for AWS credentials
    - _Requirements: 7.4_
  
  - [ ] 14.2 Deploy application to EC2
    - Copy application code to EC2 instance
    - Install all Python dependencies
    - Configure uvicorn to run as systemd service
    - Set up nginx as reverse proxy
    - Test API endpoints from public URL
    - _Requirements: 7.4_

- [ ] 15. Create web dashboard frontend
  - [ ] 15.1 Build static web application
    - Create HTML/CSS/JavaScript dashboard
    - Implement image upload interface
    - Create attendance records table with filtering
    - Add user management panel
    - Implement real-time status display
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  
  - [ ] 15.2 Deploy frontend to S3 with CloudFront
    - Create S3 bucket for static website hosting
    - Upload frontend files to S3
    - Configure CloudFront distribution
    - Set up HTTPS with SSL certificate
    - Update API calls to use EC2 backend URL
    - _Requirements: 7.5, 8.1, 8.2, 8.3, 8.4_

- [ ] 16. Add webcam support to web dashboard
  - [ ] 16.1 Implement browser-based webcam capture
    - Add WebRTC video capture in frontend
    - Implement frame capture and upload to API
    - Display recognition results in real-time
    - Add start/stop controls for webcam
    - _Requirements: 8.5_

- [ ] 17. End-to-end testing and optimization
  - [ ] 17.1 Test complete cloud system
    - Test user registration through web interface
    - Test recognition with uploaded images
    - Test webcam-based recognition
    - Verify attendance logging and retrieval
    - Test with multiple concurrent users
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2, 8.3, 8.4, 8.5_
  
  - [ ] 17.2 Performance optimization
    - Measure API response times
    - Optimize embedding cache on EC2
    - Tune recognition threshold for accuracy
    - Monitor DynamoDB and S3 usage
    - Implement CloudWatch logging and monitoring
    - _Requirements: 7.4_
