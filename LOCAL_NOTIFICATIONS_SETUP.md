# FalconEye Local Notifications Setup

This guide explains how to set up and use FalconEye with local push notifications instead of Firebase.

## Overview

The local notification system works by:
1. **Backend**: Detects objects using YOLO and triggers local notifications
2. **iOS App**: Registers with the backend and polls for new detections
3. **Notifications**: When objects are detected, the app shows local push notifications

## What Changed

### Backend Changes
- ✅ Removed Firebase FCM dependencies
- ✅ Created `local_notification_service.py` for local notifications
- ✅ Updated `backend.py` to use local notification service
- ✅ Maintained all existing API endpoints for compatibility

### iOS App Changes
- ✅ Removed Firebase SDK dependencies
- ✅ Created `LocalNotificationManager.swift` for local notifications
- ✅ Updated `FalconEyeApp.swift` to use local notification manager
- ✅ Updated `SettingsView.swift` to show local notification status
- ✅ Removed `GoogleService-Info.plist` and Firebase configuration

## Setup Instructions

### 1. Backend Setup

The backend is already configured to use local notifications. No additional setup required.

```bash
# Start the backend
cd /Users/vpaul/FalconEye
python backend.py
```

### 2. iOS App Setup

#### Option A: Use the build script (Recommended)
```bash
cd /Users/vpaul/Downloads/FalconEye
./build_local_notifications.sh
```

#### Option B: Manual setup
1. Open `FalconEye.xcodeproj` in Xcode
2. Remove Firebase dependencies from the project
3. Remove Firebase imports from Swift files
4. Build and run the app

### 3. Testing

#### Test the backend:
```bash
cd /Users/vpaul/FalconEye
python test_local_notifications.py
```

#### Test the iOS app:
1. Run the app on simulator or device
2. Grant notification permissions when prompted
3. Go to Settings tab
4. Tap "Test Notification" to test local notifications
5. Tap "Security Alert" to test security notifications

## How It Works

### Object Detection Flow
1. **Camera captures frame** → Backend processes with YOLO
2. **Objects detected** → Backend calls `send_security_alert()`
3. **Local notification service** → Stores notification for iOS app
4. **iOS app polls backend** → Checks for recent detections every 5 seconds
5. **New detection found** → iOS app shows local push notification

### Notification Types
- **Security Alerts**: Triggered when surveillance objects are detected (person, vehicle, etc.)
- **Test Notifications**: Manual test notifications from the app
- **System Notifications**: Backend status and connection notifications

## Configuration

### Backend Configuration
The local notification service is configured in `local_notification_service.py`:
- Polling interval: 5 seconds (configurable in `LocalNotificationManager.swift`)
- Detection cooldown: 10 seconds (configurable in backend)
- Notification sound: Default system sound

### iOS App Configuration
The local notification manager is configured in `LocalNotificationManager.swift`:
- Auto-registration: Device automatically registers with backend
- Permission handling: Requests notification permissions on first launch
- Polling: Checks for new detections every 5 seconds when app is active

## Troubleshooting

### Common Issues

1. **Notifications not working**
   - Check that notification permissions are granted
   - Verify backend is running and accessible
   - Check device registration status in Settings tab

2. **Backend connection failed**
   - Ensure backend is running on `http://localhost:3000`
   - Check network connectivity
   - Verify API endpoints are responding

3. **Build errors**
   - Clean build folder in Xcode (Cmd+Shift+K)
   - Remove derived data
   - Check that all Firebase references are removed

### Debug Information

The iOS app provides debug information in the Settings tab:
- Permission status
- Device registration status
- Last notification received
- Polling status

## API Endpoints

The backend maintains the same API endpoints for compatibility:

- `POST /fcm/register` - Register device (now uses local notifications)
- `POST /fcm/unregister` - Unregister device
- `POST /fcm/test` - Send test notification
- `GET /fcm/status` - Get notification service status

## Benefits of Local Notifications

1. **No external dependencies** - No Firebase account or configuration needed
2. **Privacy** - All data stays local, no cloud services
3. **Reliability** - No dependency on external services
4. **Simplicity** - Easier setup and maintenance
5. **Cost** - No Firebase usage costs

## Future Enhancements

Potential improvements to the local notification system:
- WebSocket support for real-time notifications
- Push notification service for remote notifications
- Notification history and management
- Custom notification sounds and actions
- Notification scheduling and rules

## Support

If you encounter any issues:
1. Check the debug information in the iOS app Settings tab
2. Run the test script to verify backend functionality
3. Check the backend logs for error messages
4. Ensure all dependencies are properly installed
