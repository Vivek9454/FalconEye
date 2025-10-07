# 🔔 FalconEye Push Notifications Setup Guide

## 🚀 Complete Push Notification System

This guide will help you set up push notifications for your FalconEye security system with both backend and iOS app.

## 📋 Prerequisites

- Xcode 16+ (you mentioned you have version 26)
- iOS device or simulator
- Firebase project
- Python 3.8+

## 🔧 Backend Setup

### 1. Install Dependencies

```bash
cd /Users/vpaul/FalconEye
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Firebase

1. **Get Firebase Server Key:**
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Select your project: `falconeye-security`
   - Go to Project Settings > Cloud Messaging
   - Copy the "Server key"

2. **Update Configuration:**
   ```bash
   # Edit firebase_config.json
   nano firebase_config.json
   ```
   
   Replace `YOUR_FIREBASE_SERVER_KEY_HERE` with your actual server key.

### 3. Test Backend

```bash
# Start the backend
python backend.py

# In another terminal, test notifications
python test_notifications.py
```

## 📱 iOS App Setup

### 1. Update Xcode Project

1. **Open the project:**
   ```bash
   cd /Users/vpaul/Downloads/FalconEye
   open FalconEye.xcodeproj
   ```

2. **Add Firebase SDK:**
   - File > Add Package Dependencies
   - Add: `https://github.com/firebase/firebase-ios-sdk`
   - Select: FirebaseMessaging, FirebaseAnalytics

3. **Update Bundle ID:**
   - Make sure Bundle ID matches: `com.falconeye.security`

4. **Add Push Notifications Capability:**
   - Select your target
   - Signing & Capabilities
   - Add "Push Notifications"

### 2. Configure GoogleService-Info.plist

The correct `GoogleService-Info.plist` is already copied to the project.

### 3. Build and Run

```bash
# Build the project
xcodebuild -project FalconEye.xcodeproj -scheme FalconEye -destination 'platform=iOS Simulator,name=iPhone 15' build

# Or run directly in Xcode
```

## 🧪 Testing

### 1. Test Backend Notifications

```bash
# Test notification service
python test_notifications.py

# Expected output:
# ✅ Status: {"service": "firebase_fcm", "registered_tokens": 1, ...}
# ✅ Registration: {"status": "success", "message": "Token registered"}
# ✅ Test notification: {"status": "success", "message": "Test notification sent"}
```

### 2. Test iOS App

1. **Launch the app**
2. **Go to Settings tab**
3. **Check notification status:**
   - Permission should show "Granted"
   - FCM Registration should show "Registered"
   - Status should show "Successfully registered"

4. **Test notifications:**
   - Tap "Test Notification" (sends via backend)
   - Tap "Local Test" (sends local notification)

## 🔍 Troubleshooting

### Backend Issues

**Problem: "No Firebase config found"**
```bash
# Make sure firebase_config.json exists and has correct server key
cat firebase_config.json
```

**Problem: "Failed to send notification"**
- Check Firebase server key is correct
- Verify project ID matches
- Check network connectivity

### iOS Issues

**Problem: "Firebase not configured"**
- Make sure GoogleService-Info.plist is in the project
- Check Bundle ID matches Firebase project
- Clean and rebuild project

**Problem: "FCM token error"**
- Check Push Notifications capability is enabled
- Verify provisioning profile includes push notifications
- Try on physical device instead of simulator

**Problem: "Backend registration failed"**
- Check backend is running
- Verify network connectivity
- Check API endpoints are correct

## 📊 Monitoring

### Backend Status
```bash
curl http://localhost:3000/fcm/status
```

### iOS Debug Info
- Go to Settings > Push Notifications
- Tap "Debug Info" to see detailed status
- Check Xcode console for logs

## 🎯 Expected Behavior

1. **App Launch:**
   - Firebase initializes
   - Permission request appears
   - FCM token generated
   - Token registered with backend

2. **Security Alert:**
   - Object detected by camera
   - Backend sends push notification
   - iOS app receives and displays notification

3. **Test Notifications:**
   - Backend test: Sends via FCM
   - Local test: Sends local notification
   - Both should appear on device

## 🔧 Advanced Configuration

### Custom Notification Sounds
```swift
// In NewNotificationManager.swift
content.sound = UNNotificationSound(named: "custom_sound.wav")
```

### Rich Notifications
```swift
// Add image attachments
content.attachments = [UNNotificationAttachment(identifier: "image", url: imageURL, options: nil)]
```

### Notification Categories
```swift
// Define notification actions
let category = UNNotificationCategory(identifier: "SECURITY_ALERT", actions: [], intentIdentifiers: [], options: [])
UNUserNotificationCenter.current().setNotificationCategories([category])
```

## 📝 Notes

- The new system uses Firebase Cloud Messaging (FCM) instead of direct APNs
- FCM handles both iOS and Android notifications
- Backend automatically manages token registration
- iOS app shows detailed registration status
- All notification functions are backward compatible

## 🆘 Support

If you encounter issues:

1. Check the debug info in iOS app settings
2. Review backend logs for error messages
3. Verify Firebase configuration
4. Test with both local and cloud backend URLs
5. Try on physical device for full functionality

---

**🎉 You're all set! Your FalconEye system now has working push notifications!**
