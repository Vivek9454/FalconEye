#!/bin/bash

# FalconEye Screenshot Integration Script
# This script helps you copy screenshots from Downloads to the proper documentation structure

echo "🦅 FalconEye Screenshot Integration"
echo "=================================="

# Create screenshots directory if it doesn't exist
mkdir -p docs/screenshots

# Check if Downloads/Screenshots Falconeye exists
SCREENSHOTS_DIR="$HOME/Downloads/Screenshots Falconeye"
if [ ! -d "$SCREENSHOTS_DIR" ]; then
    echo "❌ Screenshots directory not found at: $SCREENSHOTS_DIR"
    echo "Please ensure your screenshots are in: ~/Downloads/Screenshots Falconeye/"
    exit 1
fi

echo "📁 Found screenshots directory: $SCREENSHOTS_DIR"
echo "📋 Files found:"
ls -la "$SCREENSHOTS_DIR"

echo ""
echo "🔄 Copying screenshots to docs/screenshots/..."

# Copy all images to the docs/screenshots directory
cp "$SCREENSHOTS_DIR"/*.{png,jpg,jpeg,PNG,JPG,JPEG} docs/screenshots/ 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Screenshots copied successfully!"
    echo ""
    echo "📸 Screenshots in docs/screenshots/:"
    ls -la docs/screenshots/
    
    echo ""
    echo "📝 Next steps:"
    echo "1. Review the copied screenshots"
    echo "2. Rename files if needed to match the naming convention"
    echo "3. Run: git add docs/screenshots/"
    echo "4. Run: git commit -m 'Add project screenshots and demos'"
    echo "5. Run: git push origin main"
    
else
    echo "❌ No image files found or copy failed"
    echo "Please check that you have image files in: $SCREENSHOTS_DIR"
fi

echo ""
echo "🎯 Naming Convention Examples:"
echo "- dashboard-overview.png"
echo "- ios-app-home.png"
echo "- object-detection-demo.png"
echo "- face-recognition-demo.png"
echo "- system-configuration.png"