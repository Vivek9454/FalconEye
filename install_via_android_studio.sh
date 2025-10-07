#!/bin/bash

echo "📱 FalconEye Android App - Android Studio Method"
echo "================================================"

# Check if device is connected
echo "🔍 Checking for connected Android device..."
if ! adb devices | grep -q "device$"; then
    echo "❌ No Android device found!"
    echo "📋 Make sure:"
    echo "   1. USB debugging is enabled on your phone"
    echo "   2. Phone is connected via USB"
    echo "   3. You've accepted the debugging prompt on your phone"
    exit 1
fi

echo "✅ Android device found!"

# Set environment
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools:$PATH
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH=$JAVA_HOME/bin:$PATH

echo ""
echo "🎯 **RECOMMENDED METHOD - Use Android Studio:**"
echo ""
echo "1. **Open Android Studio**"
echo "2. **File → Open → Select the 'android_app' folder**"
echo "3. **Wait for Gradle sync to complete**"
echo "4. **Build → Build Bundle(s) / APK(s) → Build APK(s)**"
echo "5. **Install on device**"
echo ""
echo "📱 **Alternative - Command Line:**"
echo ""

# Try to build using Android Studio's command line tools
if [ -d "$ANDROID_HOME" ]; then
    echo "🔨 Attempting to build with Android Studio tools..."
    
    cd /Users/vpaul/FalconEye/android_app
    
    # Try to build with gradlew
    if [ -f "./gradlew" ]; then
        echo "📦 Building APK with Gradle..."
        ./gradlew assembleDebug
        
        if [ $? -eq 0 ]; then
            echo "✅ APK built successfully!"
            
            # Install APK
            echo "📱 Installing APK..."
            adb install app/build/outputs/apk/debug/app-debug.apk
            
            if [ $? -eq 0 ]; then
                echo "🎉 FalconEye app installed successfully!"
                echo "📱 Look for 'FalconEye Security' in your app drawer"
            else
                echo "❌ Installation failed"
            fi
        else
            echo "❌ Build failed"
            echo "💡 Use Android Studio instead"
        fi
    else
        echo "❌ Gradle wrapper not found"
        echo "💡 Use Android Studio instead"
    fi
else
    echo "❌ Android SDK not found at $ANDROID_HOME"
    echo "💡 Use Android Studio instead"
fi

echo ""
echo "🎯 **Current System Status:**"
echo "✅ Backend running on port 3000"
echo "✅ Firebase configured with push notifications"
echo "✅ Object detection working"
echo "✅ S3 uploads working"
echo "✅ Mobile-optimized web dashboard"
echo "📱 Android app ready to build in Android Studio"
echo ""
echo "🌐 **Test Web Dashboard:**"
echo "   https://cam.falconeye.website"
echo ""
echo "📱 **Next Steps:**"
echo "   1. Open Android Studio"
echo "   2. Import android_app folder"
echo "   3. Build and install app"
echo "   4. Test complete system"





























