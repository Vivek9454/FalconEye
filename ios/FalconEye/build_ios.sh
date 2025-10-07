#!/bin/bash

# FalconEye iOS Build Script
echo "🚀 Building FalconEye iOS App"
echo "=============================="

# Check if Xcode is installed
if ! command -v xcodebuild &> /dev/null; then
    echo "❌ Xcode is not installed or not in PATH"
    exit 1
fi

# Navigate to project directory
cd "$(dirname "$0")"

# Clean build folder
echo "🧹 Cleaning build folder..."
xcodebuild clean -project FalconEye.xcodeproj -scheme FalconEye

# Build for iOS Simulator
echo "🔨 Building for iOS Simulator..."
xcodebuild build \
    -project FalconEye.xcodeproj \
    -scheme FalconEye \
    -destination 'platform=iOS Simulator,name=iPhone 15 Pro' \
    -configuration Debug

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo ""
    echo "📱 To run the app:"
    echo "1. Open FalconEye.xcodeproj in Xcode"
    echo "2. Select iPhone 15 Pro simulator"
    echo "3. Press ⌘+R to run"
    echo ""
    echo "🌐 Make sure FalconEye backend is running on localhost:3000"
else
    echo "❌ Build failed!"
    exit 1
fi
