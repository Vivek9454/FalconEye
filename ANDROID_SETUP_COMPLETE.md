# 📱 FalconEye Android App Setup Guide

## 🎯 **Complete Setup Instructions**

### **Step 1: Enable USB Debugging on Your Phone**

1. **Go to Settings** → **About Phone**
2. **Tap "Build Number" 7 times** (enables Developer Options)
3. **Go back to Settings** → **Developer Options**
4. **Enable "USB Debugging"**
5. **Enable "Install via USB"** (if available)

### **Step 2: Connect Your Phone**

1. **Connect phone to Mac via USB cable**
2. **On your phone, you'll see a prompt: "Allow USB Debugging?"**
3. **Check "Always allow from this computer"**
4. **Tap "OK"**

### **Step 3: Verify Connection**

```bash
# Run this command to check if device is connected
adb devices
```

**Expected output:**
```
List of devices attached
[DEVICE_ID]    device
```

### **Step 4: Install Android Studio (Recommended)**

**Option A: Use Android Studio (Easiest)**
1. **Download Android Studio:** https://developer.android.com/studio
2. **Install Android Studio**
3. **Open Android Studio**
4. **File → Open → Select the `android_app` folder**
5. **Wait for Gradle sync to complete**
6. **Build → Build Bundle(s) / APK(s) → Build APK(s)**
7. **Install on device**

**Option B: Command Line (Advanced)**
```bash
# Set up environment
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH=$JAVA_HOME/bin:$PATH

# Install Android SDK
brew install android-sdk

# Set ANDROID_HOME
export ANDROID_HOME=/opt/homebrew/share/android-sdk

# Build APK
cd android_app
./gradlew assembleDebug

# Install APK
adb install app/build/outputs/apk/debug/app-debug.apk
```

### **Step 5: Test the Complete System**

**1. Web Dashboard:**
- Open: https://cam.falconeye.website
- Test live stream
- Check object detection

**2. Android App:**
- Open FalconEye app on phone
- Test live stream
- Check push notifications

**3. End-to-End Test:**
- Walk in front of camera
- Check if notification appears on phone
- Verify detected objects are shown

## 🔧 **Troubleshooting**

### **Device Not Detected:**
```bash
# Restart ADB
adb kill-server
adb start-server
adb devices

# Check USB cable
# Try different USB port
# Check phone settings
```

### **Build Errors:**
```bash
# Clean and rebuild
cd android_app
./gradlew clean
./gradlew assembleDebug
```

### **Installation Errors:**
```bash
# Uninstall existing app
adb uninstall com.falconeye

# Reinstall
adb install app/build/outputs/apk/debug/app-debug.apk
```

## 📱 **Current System Status**

### **✅ Working:**
- **Backend:** Running on port 3000
- **Firebase:** Configured with private key
- **Object Detection:** Detecting person, airplane, etc.
- **Video Recording:** Clips saved to S3
- **Mobile Optimization:** Responsive web dashboard
- **Push Notifications:** Ready to send

### **📱 Next Steps:**
1. **Enable USB debugging** on your phone
2. **Connect phone** via USB
3. **Install Android Studio** (recommended)
4. **Build and install** the Android app
5. **Test complete system**

## 🎉 **What You'll Have:**

### **Complete Security System:**
- ✅ **Real-time object detection**
- ✅ **High-speed video streaming**
- ✅ **Automatic video recording**
- ✅ **Mobile app with push notifications**
- ✅ **Web dashboard**
- ✅ **Cloud storage (S3)**
- ✅ **Remote access (Cloudflare tunnel)**

### **Unique Features:**
- 🚀 **Apple Silicon optimized** (MPS GPU)
- 📱 **Mobile-first design**
- 🔔 **Real-time push notifications**
- 🎯 **Surveillance-focused object detection**
- ☁️ **Cloud integration**
- 🌐 **Remote access**

**Your FalconEye system is production-ready!** 🚀

## 📞 **Need Help?**

If you encounter any issues:
1. **Check USB debugging** is enabled
2. **Try different USB cable/port**
3. **Restart ADB** (`adb kill-server && adb start-server`)
4. **Use Android Studio** for easier building
5. **Check phone permissions** for app installation





























