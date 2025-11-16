# Changelog

All notable changes to FalconEye will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Quick Start demo script (`run_demo.py`)
- Model download script (`scripts/download_models.sh`)
- Smoke tests (`tests/test_smoke.py`)
- GitHub Actions CI/CD workflow
- Docker support (Dockerfile and docker-compose.yml)
- Comprehensive security documentation (SECURITY.md)
- Production deployment guide (PRODUCTION.md)
- Code of Conduct
- GitHub issue and PR templates
- Environment variable configuration (.env.example)
- Migration script from config.py to .env

### Changed
- Updated all Python dependencies to latest stable versions
- Improved security: environment variables preferred over config.py
- Enhanced authentication with timing attack prevention
- Added security headers middleware
- Improved session security configuration
- Updated README with professional formatting and screenshots
- Removed emojis for professional appearance

### Security
- Removed firebase_config.json from repository
- Enhanced .gitignore to prevent secrets from being committed
- Added comprehensive secrets management documentation
- Implemented secure session handling

## [1.0.0] - 2024

### Added
- Core AI object detection with YOLOv8
- Real-time camera streaming
- Face recognition with InsightFace
- Video clip recording and management
- AWS S3 cloud storage integration
- Firebase Cloud Messaging for push notifications
- Web dashboard with responsive design
- iOS mobile application
- Android mobile application
- Multi-camera support
- Cloudflare tunnel for remote access
- Authentication system
- Vision settings configuration
- Mobile-optimized APIs

### Technical Details
- Flask backend with RESTful API
- React frontend with TypeScript
- SwiftUI iOS app
- Kotlin/Java Android app
- YOLOv8 object detection models
- InsightFace for face recognition
- OpenCV for image processing
- Real-time video processing at 10 FPS

