# 📱 FalconEye Android App Setup Guide

## 🚀 Complete Mobile Security System

This guide will help you set up the complete FalconEye system with Android app and push notifications.

## 📋 Prerequisites

### 1. **Firebase Project Setup**
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project: `falconeye-security`
3. Enable Authentication and Cloud Messaging
4. Add Android app with package name: `com.falconeye`
5. Download `google-services.json` and replace the placeholder

### 2. **Android Development Environment**
- Android Studio (latest version)
- Android SDK 24+ (API level 24+)
- Java 8 or higher

## 🔧 Setup Steps

### **Step 1: Firebase Configuration**

1. **Create Firebase Project:**
   ```
   Project Name: falconeye-security
   Project ID: falconeye-security
   ```

2. **Enable Services:**
   - Authentication
   - Cloud Messaging
   - Analytics (optional)

3. **Add Android App:**
   - Package name: `com.falconeye`
   - App nickname: `FalconEye Security`
   - Download `google-services.json`

4. **Get Server Key:**
   - Go to Project Settings > Cloud Messaging
   - Copy the "Server key"
   - Update `backend.py` with your key:
   ```python
   FCM_SERVER_KEY = "YOUR_ACTUAL_FIREBASE_SERVER_KEY"
   ```

### **Step 2: Android App Setup**

1. **Open Android Studio**
2. **Import Project:**
   - Open the `android_app` folder
   - Let Gradle sync complete

3. **Update Configuration:**
   - Replace `google-services.json` with your actual file
   - Update `SERVER_URL` in `MainActivity.java` if needed

4. **Build and Run:**
   ```bash
   ./gradlew assembleDebug
   ```

### **Step 3: Backend Integration**

1. **Update Firebase Key:**
   ```python
   # In backend.py
   FCM_SERVER_KEY = "YOUR_ACTUAL_FIREBASE_SERVER_KEY"
   ```

2. **Restart Backend:**
   ```bash
   ./start_enhanced.sh
   ```

3. **Test Integration:**
   ```bash
   curl -X POST https://cam.falconeye.website/fcm/test \
     -H "Content-Type: application/json" \
     -d '{"token": "YOUR_DEVICE_TOKEN"}'
   ```

## 📱 App Features

### **Main Screen**
- **System Status**: Real-time connection status
- **Live Stream**: Tap to view live camera feed
- **Recorded Clips**: Browse security recordings
- **Settings**: Configure notifications and preferences

### **Live Stream Screen**
- **Real-time Video**: Live camera feed with object detection
- **Touch Controls**: Tap to refresh, swipe gestures
- **Mobile Optimized**: Automatic quality adjustment
- **Snapshot**: Take instant photos

### **Push Notifications**
- **Security Alerts**: Real-time notifications for detected objects
- **Rich Notifications**: Shows detected objects and timestamps
- **Custom Sounds**: Distinctive alert sounds
- **Action Buttons**: Quick access to live stream

## 🔧 API Endpoints

### **FCM Token Management**
```bash
# Register device token
POST /fcm/register
{
  "token": "device_fcm_token"
}

# Unregister device token
POST /fcm/unregister
{
  "token": "device_fcm_token"
}

# Send test notification
POST /fcm/test
{
  "token": "device_fcm_token"
}

# Get FCM status
GET /fcm/status
```

### **Mobile APIs**
```bash
# System status
GET /mobile/status

# Clips summary
GET /mobile/clips/summary

# Camera information
GET /mobile/camera/info
```

## 🎯 Testing the Complete System

### **1. Test Backend**
```bash
curl https://cam.falconeye.website/mobile/status
```

### **2. Test Android App**
1. Install app on Android device
2. Open app and check system status
3. Tap "Live Stream" to view camera
4. Check notifications are working

### **3. Test Push Notifications**
1. Register device token via app
2. Send test notification:
   ```bash
   curl -X POST https://cam.falconeye.website/fcm/test \
     -H "Content-Type: application/json" \
     -d '{"token": "YOUR_DEVICE_TOKEN"}'
   ```

### **4. Test Object Detection**
1. Walk in front of camera
2. Check if notification is received
3. Verify detected objects are shown

## 🚀 Advanced Features

### **Custom Notifications**
The app supports rich notifications with:
- Detected object information
- Timestamps
- Custom sounds
- Action buttons

### **Mobile Optimization**
- Automatic quality adjustment
- Bandwidth optimization
- Touch-friendly interface
- Swipe navigation

### **Real-time Updates**
- Live stream with 2-second refresh
- Real-time system status
- Instant notifications

## 🔧 Troubleshooting

### **Common Issues**

**1. Notifications Not Working**
- Check Firebase configuration
- Verify server key is correct
- Check device token registration

**2. Live Stream Not Loading**
- Check internet connection
- Verify server is running
- Check camera URL

**3. App Crashes**
- Check Android version (24+)
- Verify all dependencies
- Check logs in Android Studio

### **Debug Commands**
```bash
# Check FCM status
curl https://cam.falconeye.website/fcm/status

# Test notification
curl -X POST https://cam.falconeye.website/fcm/test \
  -H "Content-Type: application/json" \
  -d '{"token": "test_token"}'

# Check system status
curl https://cam.falconeye.website/mobile/status
```

## 📊 Project Value

### **For Final Year Project:**

**Technical Complexity:**
- **Android Development**: Native app with Firebase integration
- **Real-time Communication**: WebSocket-like live streaming
- **Push Notifications**: FCM integration with rich notifications
- **Mobile Optimization**: Adaptive quality and bandwidth management
- **API Integration**: RESTful APIs for mobile app

**Innovation Points:**
- **Smart Notifications**: Only relevant security alerts
- **Mobile-First Design**: Optimized for mobile devices
- **Real-time Processing**: Live streaming with object detection
- **Cross-Platform**: Web dashboard + Android app

**Market Differentiation:**
- **Complete Solution**: Backend + Web + Mobile
- **User-Friendly**: Intuitive mobile interface
- **Cost-Effective**: Uses ESP32 instead of expensive cameras
- **Scalable**: Easy to add more cameras and features

## 🎉 Success!

Your FalconEye system now includes:
- ✅ **Backend**: Python Flask with AI detection
- ✅ **Web Dashboard**: Mobile-optimized interface
- ✅ **Android App**: Native mobile application
- ✅ **Push Notifications**: Real-time alerts
- ✅ **Cloud Access**: Permanent tunnel with custom domain
- ✅ **Complete Integration**: All components working together

**Access your complete system:**
- **Web**: https://cam.falconeye.website
- **Android**: Install the APK on your device
- **API**: Full REST API for mobile integration

This is now a comprehensive, production-ready home security system! 🚀📱✨





























