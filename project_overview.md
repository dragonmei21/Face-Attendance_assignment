## Overview

The Face Recognition Attendance System is built in three phases:

1. **Local Prototype (Phase 1)**: Python-based system using OpenCV and face_recognition library
2. **API Layer (Phase 2)**: FastAPI wrapper around core functionality
3. **Cloud Deployment (Phase 3)**: AWS-based scalable architecture

The system uses facial embeddings (128-dimensional vectors) to identify users and automatically logs attendance events. The architecture is modular, allowing each component to be developed, tested, and deployed independently.

## Architecture

### Phase 1: Local Prototype Architecture

```
┌─────────────────┐
│  User Photos    │
│  (data/users/)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Embedding Builder      │
│  (build_embeddings.py)  │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Embedding Database     │
│  (known_faces.pkl)      │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐      ┌──────────────────┐
│  Recognition Engine     │◄─────│  Test Images or  │
│  (recognize.py)         │      │  Webcam Feed     │
└────────┬────────────────┘      └──────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Attendance Logger      │
│  (attendance.py)        │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Storage                │
│  (CSV or SQLite)        │
└─────────────────────────┘
```

### Phase 3: Cloud Architecture

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
│   Storage Layer      │  │   Storage Layer      │
│  ┌────────────────┐  │  │  ┌────────────────┐  │
│  │  S3 Bucket     │  │  │  │  DynamoDB      │  │
│  │  - User Photos │  │  │  │  - Embeddings  │  │
│  │  - Uploads     │  │  │  │  - Attendance  │  │
│  └────────────────┘  │  │  └────────────────┘  │
└──────────────────────┘  └──────────────────────┘
```

## Components and Interfaces

### 1. Embedding Builder Module (`embeddings.py`)

**Purpose**: Generate and manage facial embeddings from user photos

**Key Functions**:
- `build_embedding_database()`: Scans data/users/, detects faces, generates embeddings
- `load_embeddings()`: Loads embeddings from storage (pkl or DynamoDB)
- `save_embeddings(embeddings_dict)`: Persists embeddings to storage
- `add_user_embedding(user_id, image_path)`: Adds single user to database

**Dependencies**:
- face_recognition library for embedding generation
- pickle for local storage
- boto3 for DynamoDB (Phase 3)

**Interface**:
```python
class EmbeddingManager:
    def __init__(self, users_dir: str, storage_path: str):
        pass
    
    def build_database(self) -> Dict[str, List[float]]:
        """Returns dict of {user_id: embedding}"""
        pass
    
    def load(self) -> Dict[str, List[float]]:
        pass
    
    def save(self, embeddings: Dict[str, List[float]]) -> None:
        pass
```

### 2. Recognition Engine Module (`recognition.py`)

**Purpose**: Detect faces in images and match against known embeddings

**Key Functions**:
- `detect_faces(image)`: Returns list of face locations in image
- `get_embedding(face_image)`: Generates 128-d embedding for a face
- `match_embedding(embedding, known_embeddings, threshold)`: Finds best match
- `recognize_image(image_path)`: End-to-end recognition pipeline

**Algorithm**:
1. Load image using OpenCV
2. Detect face locations using HOG or CNN detector
3. Extract face region and generate embedding
4. Compute Euclidean distance to all known embeddings
5. Return user_id if distance < threshold, else "Unknown"

**Interface**:
```python
class FaceRecognizer:
    def __init__(self, embeddings: Dict[str, List[float]], threshold: float = 0.6):
        pass
    
    def recognize(self, image_path: str) -> List[Dict]:
        """Returns [{'user_id': str, 'distance': float, 'bbox': tuple}]"""
        pass
    
    def recognize_frame(self, frame: np.ndarray) -> List[Dict]:
        """For webcam/video processing"""
        pass
```

### 3. Attendance Logger Module (`attendance.py`)

**Purpose**: Manage attendance event logging with duplicate detection

**Key Functions**:
- `log_event(user_id, source)`: Writes attendance record
- `get_last_event(user_id, date)`: Retrieves most recent event for user
- `is_duplicate(user_id, timestamp, interval_minutes)`: Checks for duplicates
- `get_attendance_report(start_date, end_date)`: Generates reports

**Logic**:
- Detection → check-in (if not duplicate)
- Subsequent detections within 5 minutes → ignored

**Interface**:
```python
class AttendanceLogger:
    def __init__(self, storage_type: str = "csv", storage_path: str = "attendance.csv"):
        pass
    
    def log(self, user_id: str, source: str = "camera") -> bool:
        """Returns True if logged, False if duplicate"""
        pass
    
    def get_records(self, filters: Dict) -> List[Dict]:
        pass
```

### 4. Webcam Module (`webcam.py`)

**Purpose**: Real-time face recognition from webcam feed

**Key Functions**:
- `start_webcam_recognition(recognizer, logger, frame_skip)`: Main loop
- `process_frame(frame)`: Runs recognition on single frame
- `display_results(frame, results)`: Draws bounding boxes and labels

**Configuration**:
- Process every Nth frame (default: 5) for performance
- Display live feed with recognition results
- Auto-log attendance when face detected

### 5. Unified Class Wrapper (`ClassAttendanceSystem`)

**Purpose**: High-level API for all system functionality

**Interface**:
```python
class ClassAttendanceSystem:
    def __init__(
        self,
        users_dir: str = "data/users",
        db_file: str = "known_faces.pkl",
        logs_file: str = "attendance.csv",
        threshold: float = 0.6
    ):
        self.embedding_manager = EmbeddingManager(users_dir, db_file)
        self.recognizer = None
        self.logger = AttendanceLogger("csv", logs_file)
    
    def build_database(self) -> None:
        """Rebuild embedding database from user photos"""
        pass
    
    def recognize(self, image_path: str) -> List[Dict]:
        """Recognize faces in image"""
        pass
    
    def log_attendance(self, user_id: str, source: str = "manual") -> bool:
        """Manually log attendance"""
        pass
    
    def start_webcam(self) -> None:
        """Start real-time webcam recognition"""
        pass
```

### 6. FastAPI Backend (`api/main.py`)

**Purpose**: REST API for web/mobile access

**Endpoints**:
```python
POST /register_face
    Body: {user_id: str, image: File}
    Response: {success: bool, message: str}

POST /recognize
    Body: {image: File}
    Response: {results: [{user_id: str, confidence: float}]}

GET /attendance
    Query: {start_date: str, end_date: str, user_id: str}
    Response: {records: [{timestamp, user_id, source}]}

GET /users
    Response: {users: [{user_id: str, photo_count: int}]}

GET /health
    Response: {status: str, uptime: int}
```

**Dependencies**:
- FastAPI framework
- Pydantic for request/response models
- boto3 for AWS integration (Phase 3)

## Data Models

### Embedding Database (Local - pickle)

```python
{
    "volodymyr": [0.123, -0.456, ..., 0.789],  # 128 floats
    "ivar": [0.234, -0.567, ..., 0.890],
    "magga": [0.345, -0.678, ..., 0.901]
}
```

### Embedding Database (Cloud - DynamoDB)

**Table: user_embeddings**
```
{
    "user_id": "volodymyr",  # Partition Key
    "embedding": [0.123, -0.456, ..., 0.789],
    "photos": ["s3://bucket/users/volodymyr/img1.jpg"],
    "created_at": "2025-01-21T10:00:00Z",
    "updated_at": "2025-01-21T10:00:00Z"
}
```

### Attendance Records (CSV)

```csv
timestamp,user_id,source
2025-01-21T09:00:15,volodymyr,camera1
2025-01-21T09:05:23,ivar,camera1
```

### Attendance Records (DynamoDB)

**Table: attendance_records**
```
{
    "timestamp": 1737450015,  # Partition Key (Unix timestamp)
    "user_id": "volodymyr",   # Sort Key
    "source": "camera1",
    "date": "2025-01-21"      # GSI for date-based queries
}
```

## Error Handling

### Face Detection Errors
- **No face detected**: Return empty results, log warning
- **Multiple faces**: Process all faces, return multiple results
- **Poor quality image**: Log warning about low confidence, proceed with recognition

### Recognition Errors
- **Embedding generation fails**: Skip that image, log error, continue with others
- **No match found**: Return "Unknown" with distance value
- **Corrupted embedding database**: Rebuild from source photos

### Storage Errors
- **File I/O errors**: Retry with exponential backoff, fallback to memory cache
- **DynamoDB throttling**: Implement retry logic with jitter
- **S3 upload failures**: Queue for retry, maintain local backup

### API Errors
- **Invalid image format**: Return 400 with clear error message
- **Missing user_id**: Return 400 with validation error
- **Service unavailable**: Return 503 with retry-after header

### Error Response Format
```python
{
    "success": false,
    "error": {
        "code": "FACE_NOT_DETECTED",
        "message": "No face found in the provided image",
        "details": {...}
    }
}
```

## Testing Strategy

### Unit Tests
- **Embedding generation**: Test with known face images, verify 128-d output
- **Distance calculation**: Test with identical/different embeddings
- **Duplicate detection**: Test with various time intervals
- **Threshold logic**: Test boundary conditions (0.59, 0.60, 0.61)

### Integration Tests
- **End-to-end recognition**: Upload photo → recognize → log attendance
- **Database rebuild**: Add new user → rebuild → verify recognition
- **API endpoints**: Test all REST endpoints with valid/invalid inputs

### System Tests
- **Multi-user recognition**: Test with 10+ users simultaneously
- **Performance**: Measure recognition time per image
- **Accuracy**: Test with different lighting, angles, distances
- **False positives**: Test with unknown faces, verify "Unknown" response

### Test Data
- Create test dataset with:
  - 5 known users (3 photos each)
  - 10 test images per user (various conditions)
  - 5 unknown person images
  - Edge cases: side profile, poor lighting, partial occlusion

### Acceptance Testing
- Each team member tests with their own photos
- Verify check-in logging and duplicate detection
- Test webcam mode in real classroom setting
- Validate dashboard displays correct data

## Performance Considerations

### Local Prototype
- **Recognition time**: ~1-2 seconds per image on CPU
- **Embedding generation**: ~0.5 seconds per face
- **Database size**: ~1KB per user (128 floats × 8 bytes)
- **Webcam frame rate**: Process every 5th frame for ~6 FPS effective rate

### Cloud Deployment
- **EC2 instance**: t3.medium or t3.large (GPU optional for scale)
- **DynamoDB**: On-demand pricing, auto-scaling
- **S3**: Standard storage class for photos
- **API response time**: Target <500ms for recognition
- **Concurrent users**: Support 50+ simultaneous recognition requests

### Optimization Strategies
- Cache embeddings in memory on EC2
- Use CNN face detector for better accuracy (slower) or HOG for speed
- Batch process multiple faces in single image
- Implement CDN caching for static assets
- Use DynamoDB DAX for read-heavy workloads
