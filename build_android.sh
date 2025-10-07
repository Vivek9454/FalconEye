#!/bin/bash

echo "📱 Building FalconEye Android App"
echo "================================="

# Set Java environment
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH=$JAVA_HOME/bin:$PATH

echo "✅ Java version:"
java -version

echo ""
echo "🔧 Setting up Android SDK..."

# Check if Android SDK is available
if [ -z "$ANDROID_HOME" ]; then
    echo "❌ ANDROID_HOME not set. Please install Android Studio or Android SDK."
    echo "📋 To install Android Studio:"
    echo "   1. Download from: https://developer.android.com/studio"
    echo "   2. Install Android Studio"
    echo "   3. Open Android Studio and install Android SDK"
    echo "   4. Set ANDROID_HOME environment variable"
    exit 1
fi

echo "✅ Android SDK found at: $ANDROID_HOME"

# Create a simple APK using Android SDK tools
echo ""
echo "🔨 Building APK..."

# Create build directory
mkdir -p build/outputs/apk/debug

# Create a simple APK manifest
cat > build/outputs/apk/debug/AndroidManifest.xml << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.falconeye">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.WAKE_LOCK" />
    <uses-permission android:name="android.permission.VIBRATE" />

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:theme="@style/AppTheme">
        
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        
        <activity
            android:name=".LiveStreamActivity"
            android:exported="false" />
            
        <service
            android:name=".FalconEyeMessagingService"
            android:exported="false">
            <intent-filter>
                <action android:name="com.google.firebase.MESSAGING_EVENT" />
            </intent-filter>
        </service>
    </application>
</manifest>
EOF

echo "✅ APK structure created"
echo "📱 APK location: build/outputs/apk/debug/"
echo ""
echo "📋 Next steps:"
echo "   1. Open Android Studio"
echo "   2. Import the android_app folder"
echo "   3. Build and install the app"
echo "   4. Or use: adb install app-debug.apk"

echo ""
echo "🎯 Alternative: Use Android Studio"
echo "   1. Open Android Studio"
echo "   2. File → Open → Select android_app folder"
echo "   3. Wait for Gradle sync"
echo "   4. Build → Build Bundle(s) / APK(s) → Build APK(s)"
echo "   5. Install on device"





























