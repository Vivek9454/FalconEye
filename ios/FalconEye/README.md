# FalconEye iOS App

A comprehensive iOS security monitoring application built with SwiftUI, featuring real-time camera feeds, AI-powered object detection, and push notifications.

## Features

### 🔐 Authentication
- Secure login system with session management
- Remember me functionality
- Automatic session timeout

### 📹 Live Camera Feeds
- Dual camera support (ESP32 and Pi Zero)
- Real-time streaming with automatic refresh
- Full-screen camera view
- Connection status monitoring

### 🎥 Security Clips
- Browse recorded security clips by date
- Video playback with native AVPlayer
- Clip metadata display (duration, size, detected objects)
- Cloud upload status indicators

### 👁️ AI Detections
- Real-time object detection alerts
- Detection history with confidence scores
- Object classification (person, car, truck, etc.)
- Visual detection cards with timestamps

### ⚙️ Settings & Notifications
- System status monitoring
- Push notification management
- Camera status indicators
- Feature toggle display
- FCM token management

### 🎨 Modern UI Design
- iOS 18 liquid glass design language
- Light and dark mode support
- Smooth animations and transitions
- Responsive layout for all device sizes

## Technical Architecture

### SwiftUI + MVVM
- **Models**: Data structures for API communication
- **Views**: SwiftUI views with modern design
- **ViewModels**: ObservableObject classes for state management
- **Services**: API service, authentication, notifications

### Key Components
- `APIService`: Handles all backend communication
- `AuthenticationManager`: Manages user sessions
- `NotificationManager`: Firebase Cloud Messaging integration
- `CameraManager`: Real-time camera feed management

### Dependencies
- Firebase SDK for push notifications
- AVKit for video playback
- URLSession for API communication
- Combine for reactive programming

## Setup Instructions

### 1. Prerequisites
- Xcode 15.0+
- iOS 17.0+
- FalconEye backend running on localhost:3000

### 2. Firebase Configuration
1. Replace `GoogleService-Info.plist` with your Firebase project configuration
2. Update Firebase project settings in the Firebase console
3. Enable Cloud Messaging for push notifications

### 3. Backend Integration
The app connects to the FalconEye backend with the following endpoints:
- `/auth/login` - User authentication
- `/mobile/status` - System status
- `/camera/snapshot/{id}` - Camera snapshots
- `/mobile/clips/summary` - Clips overview
- `/mobile/detections/recent` - Recent detections
- `/fcm/register` - FCM token registration

### 4. Build and Run
1. Open `FalconEye.xcodeproj` in Xcode
2. Select your target device or simulator
3. Build and run the project (⌘+R)

## App Structure

```
FalconEye/
├── Models/
│   └── DataModels.swift          # API data structures
├── Services/
│   ├── APIService.swift          # Backend communication
│   ├── AuthenticationManager.swift
│   ├── NotificationManager.swift
│   └── CameraManager.swift       # Camera feed management
├── Views/
│   ├── LoginView.swift           # Authentication screen
│   ├── CameraView.swift          # Live camera feeds
│   ├── ClipsView.swift           # Security clips browser
│   ├── DetectionsView.swift      # AI detection alerts
│   └── SettingsView.swift        # App settings
├── Assets.xcassets/              # App icons and images
├── FalconEyeApp.swift           # Main app entry point
├── ContentView.swift            # Root navigation
└── Info.plist                   # App configuration
```

## Security Features

### Real-time Monitoring
- Live camera feeds with 2-second refresh rate
- Automatic connection status monitoring
- Error handling and retry mechanisms

### AI-Powered Detection
- YOLO object detection integration
- Surveillance object filtering
- Confidence score display
- Detection history tracking

### Push Notifications
- Firebase Cloud Messaging integration
- Real-time security alerts
- Test notification functionality
- Token management and registration

## Customization

### UI Themes
The app supports both light and dark modes with:
- Dynamic color schemes
- Glass morphism effects
- Smooth transitions
- Accessibility support

### Camera Configuration
Update camera URLs in `APIService.swift`:
```swift
private let baseURL = "http://localhost:3000"
```

### Notification Settings
Configure Firebase in `NotificationManager.swift` and update the FCM server key in your backend.

## Troubleshooting

### Connection Issues
- Ensure FalconEye backend is running on localhost:3000
- Check network connectivity
- Verify API endpoints are accessible

### Camera Feed Problems
- Verify camera URLs are correct
- Check camera hardware status
- Review backend camera configuration

### Push Notifications
- Ensure Firebase is properly configured
- Check notification permissions
- Verify FCM token registration

## License

This project is part of the FalconEye Security System. All rights reserved.

## Support

For technical support or feature requests, please contact the development team.
