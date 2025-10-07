#!/bin/bash

# FalconEye Android App Installation Script
echo "🦅 Installing FalconEye Android App..."

# Check if adb is available
if ! command -v adb &> /dev/null; then
    echo "❌ ADB not found. Please install Android SDK platform-tools"
    echo "   Or install via: brew install android-platform-tools"
    exit 1
fi

# Check if device is connected
if ! adb devices | grep -q "device$"; then
    echo "❌ No Android device connected"
    echo "   Please:"
    echo "   1. Enable Developer Options on your phone"
    echo "   2. Enable USB Debugging"
    echo "   3. Connect your phone via USB"
    echo "   4. Run this script again"
    exit 1
fi

# Install the APK
echo "📱 Installing APK..."
adb install -r android_app/app/build/outputs/apk/debug/app-debug.apk

if [ $? -eq 0 ]; then
    echo "✅ FalconEye app installed successfully!"
    echo ""
    echo "🎯 Next steps:"
    echo "   1. Open the FalconEye app on your phone"
    echo "   2. The app will automatically register for notifications"
    echo "   3. Go to http://localhost:3000 in your browser"
    echo "   4. Click 'Test Alert' to test notifications"
    echo ""
    echo "📱 Your phone should now receive security alerts!"
else
    echo "❌ Installation failed"
    exit 1
fi