# FalconEye 🦅

A comprehensive AI-powered surveillance system with real-time object detection, facial recognition, and cross-platform mobile access.

## Features

### 🔍 Core Detection
- **Real-time Object Detection**: YOLO-powered detection with customizable models
- **Facial Recognition**: InsightFace integration with face registration and recognition
- **Smart Overlays**: Configurable bounding boxes with color coding
- **Multi-Camera Support**: ESP32 and Raspberry Pi camera integration

### 📱 Mobile Apps
- **iOS App**: Native SwiftUI app with local/cloud connectivity
- **Automatic Discovery**: Bonjour/mDNS local network discovery
- **Smart Routing**: Auto-switches between local LAN and Cloudflare tunnel
- **Face Management**: Register and manage known faces from mobile

### 🌐 Connectivity
- **Local Network**: Direct LAN access for fastest performance
- **Cloudflare Tunnel**: Secure remote access via `cam.falconeye.website`
- **Smart Start**: Automated startup with port conflict resolution

### 🎥 Recording & Storage
- **Automatic Clips**: Motion-triggered recording with configurable length
- **Cloud Storage**: Optional S3 integration for backup
- **Local Storage**: Efficient local clip management
- **Thumbnail Generation**: Quick preview of recorded events

### 🔔 Notifications
- **Push Notifications**: Firebase Cloud Messaging integration
- **Local Notifications**: On-device alerts and sound
- **Smart Filtering**: Reduce noise with intelligent detection thresholds

## Quick Start

### Prerequisites
- Python 3.8+
- OpenCV
- PyTorch (CPU/MPS/CUDA)
- Cloudflare account (for remote access)

### Installation

1. **Clone and setup**:
   ```bash
   git clone https://github.com/yourusername/falconeye.git
   cd falconeye
   pip install -r requirements.txt
   ```

2. **Configure**:
   ```bash
   cp config.example config.py
   # Edit config.py with your settings
   ```

3. **Start the system**:
   ```bash
   ./start_smart.sh
   ```

### iOS App Setup

1. Open `ios/FalconEye/FalconEye.xcodeproj` in Xcode
2. Configure your Apple Developer account
3. Build and install on device

## Configuration

### Camera Setup
- **ESP32**: Configure snapshot endpoint in `config.py`
- **Raspberry Pi**: Set MJPEG stream URL for real-time feed

### Cloudflare Tunnel
```yaml
# falconeye-permanent-config.yml
tunnel: your-tunnel-id
credentials-file: /path/to/credentials

ingress:
  - hostname: cam.falconeye.website
    service: http://localhost:3000
```

### Firebase (Optional)
1. Create Firebase project
2. Download `firebase-service-account.json`
3. Configure FCM in mobile app

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   iOS App       │    │   Backend API    │    │   Cameras       │
│                 │    │                  │    │                 │
│ • SwiftUI       │◄──►│ • Flask Server   │◄──►│ • ESP32         │
│ • Auto Discovery│    │ • YOLO Detection │    │ • Raspberry Pi  │
│ • Face Mgmt     │    │ • Face Recognition│   │ • MJPEG Stream  │
│ • Local/Cloud   │    │ • Bonjour mDNS   │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                       ┌────────▼────────┐
                       │  Cloudflare     │
                       │  Tunnel         │
                       │  (Remote Access)│
                       └─────────────────┘
```

## API Endpoints

### System
- `GET /system/status` - System health and configuration
- `GET /discover` - Bonjour discovery endpoint

### Cameras
- `GET /camera/snapshot/{camera_id}` - Get camera snapshot
- `GET /camera/stream/{camera_id}` - MJPEG stream

### Detection
- `GET /mobile/detections/recent` - Recent detection events
- `POST /vision/settings` - Update detection settings

### Faces
- `GET /faces/status` - Face recognition status
- `POST /faces/register` - Register new face
- `DELETE /faces/delete/{face_id}` - Remove face

## Development

### Backend
```bash
# Development mode with auto-reload
python backend.py

# Debug mode
FLASK_DEBUG=1 python backend.py
```

### iOS
- Open in Xcode 15+
- Target iOS 18.5+
- Uses SwiftUI and Combine

## Troubleshooting

### Common Issues

**Local discovery not working**:
- Ensure backend is running with Bonjour enabled
- Check Local Network permissions on iOS
- Verify firewall settings

**Cloudflare tunnel errors**:
- Check tunnel configuration
- Verify DNS settings
- Run diagnostics: `./start_smart.sh`

**Camera offline**:
- Verify camera IP addresses
- Check network connectivity
- Test snapshot endpoints manually

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- YOLO for object detection
- InsightFace for facial recognition
- Cloudflare for tunnel infrastructure
- Firebase for push notifications