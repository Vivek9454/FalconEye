# FalconEye iOS App Setup Guide

## Quick Start

### 1. Prerequisites
- **Xcode 15.0+** (Download from Mac App Store)
- **iOS 17.0+** target device or simulator
- **FalconEye backend** running on localhost:3000
- **Firebase project** configured for push notifications

### 2. Open the Project
```bash
cd /Users/vpaul/Downloads/FalconEye
open FalconEye.xcodeproj
```

### 3. Configure Firebase
1. Replace `FalconEye/GoogleService-Info.plist` with your Firebase configuration
2. Update the bundle identifier in Xcode project settings
3. Enable Cloud Messaging in Firebase console

### 4. Build and Run
1. Select iPhone 15 Pro simulator (or your preferred device)
2. Press `⌘+R` to build and run
3. The app will connect to your FalconEye backend automatically

## Detailed Setup

### Firebase Configuration

#### Step 1: Create Firebase Project
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project named "FalconEye Security"
3. Enable Google Analytics (optional)

#### Step 2: Add iOS App
1. Click "Add app" → iOS
2. Bundle ID: `com.falconeye.security`
3. Download `GoogleService-Info.plist`
4. Replace the existing file in the project

#### Step 3: Enable Cloud Messaging
1. In Firebase Console → Project Settings → Cloud Messaging
2. Generate a new server key
3. Update the FCM server key in your backend

### Backend Integration

#### API Endpoints
The iOS app connects to these backend endpoints:
- `GET /mobile/status` - System status
- `POST /auth/login` - User authentication
- `GET /camera/snapshot/{id}` - Camera snapshots
- `GET /mobile/clips/summary` - Clips overview
- `GET /mobile/detections/recent` - Recent detections
- `POST /fcm/register` - FCM token registration

#### Network Configuration
- Default backend URL: `http://localhost:3000`
- Update in `APIService.swift` if using different host/port
- Ensure backend allows CORS for mobile requests

### App Features

#### 🔐 Authentication
- **Username**: admin
- **Password**: password123
- Session management with remember me option
- Automatic logout after inactivity

#### 📹 Camera Feeds
- **cam1**: ESP32 camera (http://192.168.31.99/jpg)
- **cam2**: Pi Zero MJPEG stream (http://192.168.31.253:8081/)
- Real-time updates every 2 seconds
- Full-screen viewing capability

#### 🎥 Security Clips
- Browse clips by date
- Video playback with native player
- Metadata display (duration, size, objects)
- Cloud upload status

#### 👁️ AI Detections
- Real-time object detection alerts
- Detection history with confidence scores
- Object classification and filtering
- Visual detection cards

#### ⚙️ Settings
- System status monitoring
- Push notification management
- Camera status indicators
- Feature toggle display

### Troubleshooting

#### Connection Issues
```bash
# Check if backend is running
curl http://localhost:3000/mobile/status

# Expected response:
# {"status":"online","cameras":{"cam1":true,"cam2":true},...}
```

#### Camera Feed Problems
1. Verify camera URLs in backend configuration
2. Check camera hardware status
3. Ensure cameras are accessible from iOS device/simulator
4. Review backend logs for connection errors

#### Push Notifications
1. Check notification permissions in iOS Settings
2. Verify FCM token registration in backend logs
3. Test with "Send Test" button in Settings
4. Ensure Firebase project is properly configured

#### Build Errors
1. Clean build folder: `⌘+Shift+K`
2. Reset simulator: Device → Erase All Content and Settings
3. Check iOS deployment target (17.0+)
4. Verify all dependencies are properly linked

### Development Tips

#### Testing on Device
1. Connect iPhone via USB
2. Select your device in Xcode
3. Trust developer certificate on device
4. Build and run directly on device

#### Simulator Testing
- Use iPhone 15 Pro simulator for best experience
- Test both light and dark modes
- Rotate device to test landscape orientation
- Use different network conditions

#### Debugging
- Check Xcode console for API errors
- Use Network Inspector for API calls
- Monitor memory usage in Debug Navigator
- Test with slow network conditions

### Customization

#### UI Themes
Modify colors in individual view files:
- Primary: `.green`
- Secondary: `.blue`
- Accent: `.purple`
- Error: `.red`

#### Camera Configuration
Update camera URLs in `APIService.swift`:
```swift
private let baseURL = "http://your-backend-url:port"
```

#### Notification Settings
Configure push notification behavior in `NotificationManager.swift`

### Performance Optimization

#### Memory Management
- Camera images are automatically refreshed
- Video clips are streamed, not stored locally
- Detection history is limited to recent items

#### Network Efficiency
- API calls are cached where appropriate
- Camera feeds refresh every 2 seconds
- Automatic retry on connection failures

### Security Considerations

#### Data Protection
- No sensitive data stored locally
- API communication over HTTP (configure HTTPS for production)
- Session management with automatic timeout

#### Privacy
- Camera access only for viewing feeds
- No local video storage
- Push notifications for security alerts only

## Support

For technical support:
1. Check this setup guide
2. Review Xcode console logs
3. Verify backend connectivity
4. Test with different devices/simulators

## Next Steps

1. **Deploy to App Store**: Configure production settings
2. **Add More Features**: Customize based on requirements
3. **Performance Tuning**: Optimize for production use
4. **Security Hardening**: Implement additional security measures
