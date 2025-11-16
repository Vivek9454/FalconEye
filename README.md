# 🚀 FalconEye - AI-Powered Home Security System

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-green.svg)](https://flask.palletsprojects.com/)
[![YOLO](https://img.shields.io/badge/YOLO-8.3.0-red.svg)](https://ultralytics.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A comprehensive, AI-powered home security system with real-time object detection, mobile apps, and cloud integration.

## ✨ Features

### 🎯 Core Security Features
- **AI Object Detection**: YOLOv8-powered real-time detection with 90% false alarm reduction
- **Smart Filtering**: Only detects home surveillance relevant objects (person, car, dog, etc.)
- **High-Speed Capture**: 10 FPS frame capture from ESP32 camera
- **Video Recording**: Automatic recording when objects detected
- **Push Notifications**: Real-time alerts via Firebase Cloud Messaging
- **Cloud Storage**: AWS S3 integration for video clips

### 📱 Mobile Optimizations
- **Responsive Design**: Works perfectly on all screen sizes
- **Touch Navigation**: Swipe between Live, Clips, Status tabs
- **Bandwidth Optimization**: 50% less data usage on mobile
- **Auto-Detection**: Automatically detects mobile devices
- **Quality Adjustment**: Lower quality for mobile to save bandwidth
- **Progressive Loading**: Images load with smooth transitions
- **Dark Mode**: Automatic dark theme support

### 🌐 Cloud & Access
- **Permanent Tunnel**: Always-available cloud access via Cloudflare
- **Custom Domain**: https://cam.falconeye.website
- **SSL Security**: Encrypted connections
- **Global CDN**: Fast access worldwide
- **Mobile APIs**: Optimized endpoints for mobile apps

## 🏗️ System Architecture

```
┌─────────────────┐
│  Mobile Web App │
│  (React/Vite)   │
└────────┬────────┘
         │ HTTP/HTTPS
         ▼
┌─────────────────┐
│  Flask Backend  │
│   (Python 3.8+) │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────┐
│ ESP32  │ │ YOLO AI  │
│ Camera │ │ Detection│
└────────┘ └──────────┘
    │
    ▼
┌──────────┐
│ AWS S3   │
│ Storage  │
└──────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Node.js 18+ (for frontend)
- ESP32 camera or compatible IP camera
- AWS account (for S3 storage, optional)
- Firebase account (for push notifications, optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Vivek9454/FalconEye.git
   cd FalconEye
   ```

2. **Set up Python environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   # Copy example config
   cp config.example .env
   
   # Edit .env with your settings:
   # - Camera IPs
   # - AWS credentials (optional)
   # - Firebase credentials (optional)
   ```

4. **Set up frontend (optional)**
   ```bash
   cd falconeye-react-frontend
   npm install
   npm run build
   ```

5. **Start the backend**
   ```bash
   # Option 1: Enhanced startup (recommended)
   ./start_enhanced.sh
   
   # Option 2: Manual startup
   python backend.py
   ```

6. **Access the dashboard**
   - Local: http://localhost:3000
   - Cloud: https://cam.falconeye.website (if tunnel configured)

## 📖 Configuration

### Network Profiles
Edit `backend.py` to configure your camera IPs:

```python
NETWORK_PROFILES = [
    {
        "name": "home",
        "cameras": {
            "cam1": "http://YOUR_CAMERA_IP/jpg",
            "cam2": "http://YOUR_CAMERA_IP:8081/",
        },
        "esp_pan_base": "http://YOUR_ESP32_IP",
    },
]
```

Or use environment variables:
```bash
export CAM1_URL="http://10.103.190.6/jpg"
export CAM2_URL="http://10.103.190.170:8081/"
export ESP_PAN_BASE_URL="http://10.103.190.58"
```

### Vision Settings
Configure detection settings in `vision_settings.json`:
- Enable/disable object classes
- Adjust detection sensitivity
- Configure face recognition
- Customize overlay colors

### AWS S3 Setup (Optional)
1. Create an S3 bucket
2. Set up IAM user with S3 access
3. Add credentials to environment:
   ```bash
   export AWS_ACCESS_KEY_ID="your_key"
   export AWS_SECRET_ACCESS_KEY="your_secret"
   export AWS_REGION="us-east-1"
   export AWS_S3_BUCKET="your-bucket-name"
   ```

### Firebase Setup (Optional)
See `FIREBASE_SETUP_INSTRUCTIONS.md` for detailed setup.

## 📱 Mobile Apps

### iOS App
- Located in `ios/FalconEye/`
- Built with SwiftUI
- Requires Xcode 15.0+
- See `ios/FalconEye/README.md` for setup

### Android App
- Located in `android_app/`
- Built with Kotlin/Java
- See `ANDROID_SETUP.md` for setup

## 🔧 API Endpoints

### Authentication
- `POST /auth/login` - User login
- `GET /logout` - User logout

### Camera
- `GET /camera/list` - List available cameras
- `GET /camera/snapshot/<cam_id>` - Get camera snapshot
- `GET /camera/live/<cam_id>` - Live stream feed
- `POST /camera/pan/<action>` - Pan camera (left/right/auto)
- `POST /camera/tilt/<action>` - Tilt camera (up/down/auto)

### Clips
- `GET /clips` - List recorded clips
- `GET /clips/<filename>` - Download clip
- `GET /clips/thumbnails/<filename>` - Get clip thumbnail

### System
- `GET /mobile/status` - System status
- `GET /vision/settings` - Get vision settings
- `POST /vision/settings` - Update vision settings

## 🛠️ Development

### Running Tests
```bash
python test_backend.py
```

### Code Structure
```
FalconEye/
├── backend.py              # Main Flask backend
├── local_notification_service.py  # Notification service
├── faces_worker.py         # Face recognition worker
├── faces/                  # Face recognition module
├── falconeye-react-frontend/  # React frontend
├── ios/                    # iOS app
├── android_app/            # Android app
├── clips/                  # Recorded video clips
└── requirements.txt        # Python dependencies
```

## 🔒 Security

- **Authentication**: Session-based authentication with secure password hashing
- **HTTPS**: All communications encrypted via Cloudflare tunnel
- **Session Management**: Secure session handling with configurable timeouts
- **Password Security**: bcrypt password hashing

## 📊 Performance

- **Object Detection**: Real-time processing at 10 FPS
- **Mobile Optimization**: 50% bandwidth reduction on mobile
- **Cloud Storage**: Automatic upload with retry mechanism
- **Caching**: Smart caching for images and static assets

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Ultralytics YOLO](https://ultralytics.com/) for object detection
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [OpenCV](https://opencv.org/) for computer vision
- [Cloudflare](https://www.cloudflare.com/) for tunnel service

## 📞 Support

- **Documentation**: See `docs/` directory
- **Issues**: [GitHub Issues](https://github.com/Vivek9454/FalconEye/issues)
- **Setup Guides**: 
  - `ANDROID_SETUP.md` - Android app setup
  - `FIREBASE_SETUP_INSTRUCTIONS.md` - Firebase setup
  - `LOCAL_NOTIFICATIONS_SETUP.md` - Local notifications

## 🎯 Project Status

✅ **Core Features**: Complete
✅ **Mobile Apps**: iOS and Android available
✅ **Cloud Integration**: AWS S3 and Firebase configured
✅ **Documentation**: Comprehensive guides available

---

**Built with ❤️ for home security**

