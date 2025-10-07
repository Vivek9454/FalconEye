# 🔥 Firebase Setup Instructions

## 📋 **Complete Firebase Configuration**

### **Step 1: Create Firebase Project**

1. **Go to Firebase Console:**
   - Visit: https://console.firebase.google.com/
   - Click "Create a project"

2. **Project Details:**
   ```
   Project name: falconeye-security
   Project ID: falconeye-security
   Analytics: Enable (recommended)
   ```

3. **Complete setup** and continue

### **Step 2: Enable Cloud Messaging**

1. **In Firebase dashboard:**
   - Click "Build" → "Cloud Messaging"
   - Click "Get started"

2. **FCM is now enabled** for your project

### **Step 3: Add Android App**

1. **Add Android app:**
   - Click Android icon (📱) or "Add app"
   - Select Android

2. **Android app configuration:**
   ```
   Android package name: com.falconeye
   App nickname: FalconEye Security
   Debug signing certificate SHA-1: (leave empty for now)
   ```

3. **Download google-services.json:**
   - Click "Download google-services.json"
   - Save to: `android_app/app/google-services.json`

### **Step 4: Get Server Key**

1. **Project Settings:**
   - Click gear icon (⚙️) → "Project settings"
   - Go to "Cloud Messaging" tab

2. **Copy Server Key:**
   - Find "Server key" section
   - Copy the key (starts with `AAAA...`)

3. **Update backend.py:**
   ```python
   FCM_SERVER_KEY = "YOUR_ACTUAL_SERVER_KEY_HERE"
   ```

### **Step 5: Test Configuration**

1. **Restart backend:**
   ```bash
   pkill -f "python backend.py"
   source venv/bin/activate && python backend.py &
   ```

2. **Test FCM status:**
   ```bash
   curl http://localhost:3000/fcm/status
   ```

3. **Expected response:**
   ```json
   {
     "fcm_enabled": true,
     "registered_tokens": 0,
     "last_notification": "N/A"
   }
   ```

## 🔧 **Troubleshooting**

### **Common Issues:**

**1. Server Key Not Working:**
- Make sure you copied the entire key
- Check for extra spaces or characters
- Verify the key starts with `AAAA`

**2. google-services.json Issues:**
- Make sure file is in `android_app/app/` folder
- Check file name is exactly `google-services.json`
- Verify JSON format is valid

**3. FCM Not Enabled:**
- Go to Firebase Console → Cloud Messaging
- Click "Get started" if not already enabled

### **Test Commands:**

```bash
# Check FCM status
curl http://localhost:3000/fcm/status

# Test notification (after registering device)
curl -X POST http://localhost:3000/fcm/test \
  -H "Content-Type: application/json" \
  -d '{"token": "test_token"}'
```

## 📱 **Android App Setup**

### **1. Update google-services.json:**
- Replace placeholder with your actual file
- Place in `android_app/app/` folder

### **2. Build Android App:**
```bash
cd android_app
./gradlew assembleDebug
```

### **3. Install on Device:**
```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

## 🎯 **Complete Integration Test**

### **1. Backend Test:**
```bash
# Check system status
curl http://localhost:3000/mobile/status

# Check FCM status
curl http://localhost:3000/fcm/status
```

### **2. Android App Test:**
1. Install app on Android device
2. Open app and check system status
3. Register device token
4. Test push notifications

### **3. End-to-End Test:**
1. Walk in front of camera
2. Check if notification is received on Android
3. Verify detected objects are shown

## ✅ **Success Indicators**

- **Backend**: `fcm_enabled: true` in status
- **Android**: App shows "System Online"
- **Notifications**: Test notification received
- **Detection**: Real-time alerts working

## 🚀 **Next Steps**

Once Firebase is configured:

1. **Test the complete system**
2. **Build and install Android app**
3. **Test push notifications**
4. **Verify object detection alerts**

Your FalconEye system will then have complete push notification support! 🎉





























