#!/bin/bash

# Build script for FalconEye iOS app with local notifications
# This script removes Firebase dependencies and builds the app

echo "🚀 Building FalconEye iOS app with local notifications..."

# Navigate to the iOS project directory
cd "$(dirname "$0")"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
xcodebuild clean -project FalconEye.xcodeproj -scheme FalconEye

# Remove Firebase dependencies from project
echo "🔥 Removing Firebase dependencies..."

# Remove Firebase from project.pbxproj
sed -i.bak 's/FirebaseCore//g' FalconEye.xcodeproj/project.pbxproj
sed -i.bak 's/FirebaseMessaging//g' FalconEye.xcodeproj/project.pbxproj
sed -i.bak 's/FirebaseAuth//g' FalconEye.xcodeproj/project.pbxproj
sed -i.bak 's/FirebaseAnalytics//g' FalconEye.xcodeproj/project.pbxproj

# Remove Firebase imports from Swift files
find FalconEye -name "*.swift" -exec sed -i.bak 's/import Firebase//g' {} \;
find FalconEye -name "*.swift" -exec sed -i.bak 's/import FirebaseMessaging//g' {} \;
find FalconEye -name "*.swift" -exec sed -i.bak 's/import FirebaseAuth//g' {} \;
find FalconEye -name "*.swift" -exec sed -i.bak 's/import FirebaseAnalytics//g' {} \;

# Remove Firebase configuration
rm -f FalconEye/GoogleService-Info.plist
rm -f FalconEye/GoogleService-Info.plist.backup

echo "✅ Firebase dependencies removed"

# Build the project
echo "🔨 Building project..."
xcodebuild build -project FalconEye.xcodeproj -scheme FalconEye -destination 'platform=iOS Simulator,name=iPhone 15'

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo ""
    echo "📱 To run the app:"
    echo "1. Open FalconEye.xcodeproj in Xcode"
    echo "2. Select a simulator or device"
    echo "3. Press Cmd+R to run"
    echo ""
    echo "🔔 Local notifications will work without Firebase!"
else
    echo "❌ Build failed. Please check the errors above."
    exit 1
fi
