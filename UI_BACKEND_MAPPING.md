# FalconEye UI to Backend API Mapping

This document maps all UI components and user flows to their corresponding backend endpoints and functionality.

## Overview
FalconEye is a mobile-first security system with a web dashboard that communicates with a Python Flask backend. The system provides real-time camera monitoring, object detection, clip recording, and push notifications.

## Architecture

```
Mobile Web App (Frontend)
    ↓ HTTP/HTTPS
Flask Backend (Python)
    ↓
- ESP32 Camera (RTSP/HTTP)
- YOLO Object Detection
- AWS S3 Storage
- Firebase Cloud Messaging
```

## UI Components & Backend Mapping

### 1. Authentication Flow

#### Login Screen (`/login`)
- **UI**: Simple login form with username/password
- **Backend**: `POST /auth/login`
- **Request**: `{"username": "user", "password": "pass"}`
- **Response**: `{"status": "ok", "device": "macbook"}`
- **Error**: `{"status": "error"}` (401)

#### Session Management
- **UI**: Automatic redirect to dashboard on successful login
- **Backend**: Flask session management
- **Storage**: Server-side session with user validation

### 2. Dashboard Navigation

#### Main Dashboard (`/`)
- **UI**: Tab-based navigation (Live, Clips, Status, Settings)
- **Backend**: `GET /` (renders dashboard template)
- **Data**: System status, recent clips, camera info

#### Tab Switching
- **UI**: JavaScript tab switching
- **Backend**: Client-side only (no API calls)
- **State**: Maintained in browser localStorage

### 3. Live Stream Tab

#### Live Camera Feed
- **UI**: `<img id="liveimg" src="/camera/snapshot/cam1">`
- **Backend**: `GET /camera/snapshot/cam1`
- **Response**: JPEG image with object detection annotations
- **Refresh**: Auto-refresh every 2 seconds when streaming

#### Quality Controls
- **UI**: High/Medium/Low quality buttons
- **Backend**: `GET /camera/snapshot/cam1?quality={level}`
- **Parameters**: `quality=high|medium|low`
- **Storage**: Preference saved in localStorage

#### Stream Controls
- **UI**: Play/Pause, Snapshot, Fullscreen buttons
- **Backend**: 
  - Snapshot: `GET /camera/snapshot/cam1`
  - Stream toggle: Client-side interval management
- **State**: Managed in JavaScript

#### Quick Actions
- **UI**: Snapshot, Test Alert, View Clips, Settings buttons
- **Backend**:
  - Snapshot: `GET /camera/snapshot/cam1`
  - Test Alert: `POST /mobile/test-push`
  - Navigation: Client-side tab switching

### 4. Clips Tab

#### Clips List
- **UI**: Date-filtered grid of video clips
- **Backend**: `GET /?date={YYYY-MM-DD}`
- **Data**: Rendered in dashboard template with metadata

#### Date Filtering
- **UI**: Date dropdown selector
- **Backend**: `GET /?date={selected_date}`
- **Available Dates**: Generated from clip metadata

#### Clip Playback
- **UI**: HTML5 video elements
- **Backend**: `GET /clips/{filename}`
- **Response**: MP4 video file with range request support
- **Headers**: `Accept-Ranges: bytes`, `Content-Type: video/mp4`

#### Upload Status
- **UI**: Status badges (☁️ Uploaded, ❌ Failed, ⏳ Pending)
- **Backend**: Metadata includes `uploaded_to_s3` boolean
- **Update**: Real-time via S3 upload callback

#### Download
- **UI**: Download button for each clip
- **Backend**: `GET /clips/{filename}` with download headers
- **Headers**: `Content-Disposition: attachment`

### 5. Status Tab

#### System Status
- **UI**: Device info, GPU status, online indicator
- **Backend**: `GET /system/status`
- **Response**: Device info, GPU availability, system metrics

#### Quick Stats
- **UI**: Performance metrics display
- **Backend**: Static data in dashboard template
- **Data**: FPS info, storage info, notification status

#### Mobile Features
- **UI**: Feature list display
- **Backend**: Static data in dashboard template
- **Data**: Responsive design, touch controls, bandwidth optimization

### 6. Settings Tab

#### FCM Token Management
- **UI**: Token input field with register/unregister buttons
- **Backend**:
  - Register: `POST /fcm/register`
  - Unregister: `POST /fcm/unregister`
  - Test: `POST /mobile/test-push`
- **Request**: `{"token": "fcm_token_string"}`
- **Response**: `{"status": "success", "message": "..."}`

#### Bandwidth Preference
- **UI**: Quality selection buttons
- **Backend**: Client-side localStorage management
- **Storage**: `streamQuality` preference

#### Theme Toggle
- **UI**: Light/Dark theme button
- **Backend**: Client-side localStorage management
- **Storage**: `theme` preference

### 7. Push Notifications

#### Notification Display
- **UI**: Toast notifications for real-time updates
- **Backend**: FCM integration with `send_push_notification()`
- **Triggers**: Object detection, system alerts, test notifications

#### Test Notifications
- **UI**: Test Alert button in Quick Actions
- **Backend**: `POST /mobile/test-push`
- **Request**: `{"test": true}`
- **Response**: `{"status": "success", "message": "Test notification sent"}`

## API Endpoints Reference

### Core Endpoints
```
GET  /                    # Main dashboard
GET  /login              # Login page
POST /auth/login         # Authentication
GET  /logout             # Logout

GET  /camera/snapshot/cam1    # Camera snapshot
GET  /camera/live/cam1        # Live stream
GET  /clips/{filename}        # Video clip download

GET  /system/status      # System status
GET  /mobile/status      # Mobile-optimized status
```

### Mobile-Specific Endpoints
```
GET  /mobile/clips/summary     # Clips summary by date
GET  /mobile/camera/info       # Camera information
GET  /mobile/detections/recent # Recent detections
POST /mobile/test-push         # Test push notification
```

### FCM Endpoints
```
POST /fcm/register      # Register FCM token
POST /fcm/unregister    # Unregister FCM token
```

## Data Flow Examples

### 1. User Login Flow
```
1. User visits /login
2. Enters credentials
3. POST /auth/login
4. Backend validates credentials
5. Session created
6. Redirect to dashboard
7. GET / (dashboard with data)
```

### 2. Live Stream Flow
```
1. User clicks Live tab
2. JavaScript shows live-tab content
3. GET /camera/snapshot/cam1
4. Image displayed with annotations
5. Auto-refresh every 2 seconds
6. Quality changes update URL parameters
```

### 3. Clip Viewing Flow
```
1. User clicks Clips tab
2. GET /?date={selected_date}
3. Backend renders clips with metadata
4. User clicks video
5. GET /clips/{filename}
6. Video streams with range requests
7. Upload status updated via metadata
```

### 4. Push Notification Flow
```
1. Object detected by YOLO
2. send_push_notification() called
3. FCM sends to registered tokens
4. Mobile device receives notification
5. User taps notification
6. App opens to relevant screen
```

## Error Handling

### Network Errors
- **UI**: Toast notifications with error messages
- **Backend**: HTTP status codes and error responses
- **Fallback**: Placeholder images and graceful degradation

### Authentication Errors
- **UI**: Login form with error messages
- **Backend**: 401 responses with error details
- **Redirect**: Automatic redirect to login on auth failure

### Camera Errors
- **UI**: Test image with "Camera Offline" message
- **Backend**: create_test_image() fallback
- **Status**: Visual indicators for camera status

## Performance Optimizations

### Image Optimization
- **Format**: JPEG with quality compression
- **Size**: Responsive sizing based on device
- **Caching**: Browser caching with cache headers

### Video Optimization
- **Format**: MP4 with H.264 encoding
- **Streaming**: Range request support
- **Quality**: Multiple quality levels

### Mobile Optimizations
- **Bandwidth**: Quality selection based on connection
- **Touch**: Large touch targets and gestures
- **Responsive**: CSS Grid and Flexbox layouts

## Security Considerations

### Authentication
- **Session**: Server-side session management
- **Passwords**: bcrypt hashing
- **Tokens**: Secure FCM token storage

### Data Protection
- **HTTPS**: All communications encrypted
- **CORS**: Proper cross-origin headers
- **Validation**: Input validation and sanitization

### Privacy
- **Local Storage**: No sensitive data in localStorage
- **Cookies**: Secure session cookies only
- **Logs**: No sensitive data in logs

## Development Notes

### Frontend
- **Framework**: Vanilla JavaScript with modern ES6+
- **Styling**: CSS Grid, Flexbox, CSS Variables
- **State**: localStorage for preferences
- **Responsive**: Mobile-first design approach

### Backend
- **Framework**: Flask with Jinja2 templates
- **Detection**: YOLOv8 with OpenCV
- **Storage**: Local filesystem + AWS S3
- **Notifications**: Firebase Cloud Messaging

### Integration
- **Real-time**: Polling-based updates
- **Async**: Background tasks for heavy operations
- **Monitoring**: Comprehensive logging and status reporting
