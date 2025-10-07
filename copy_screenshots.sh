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

echo ""
echo "🔄 Copying screenshots to docs/screenshots/..."

# Copy all images from subdirectories to the docs/screenshots directory
find "$SCREENSHOTS_DIR" -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.PNG" -o -name "*.JPG" -o -name "*.JPEG" | while read file; do
    filename=$(basename "$file")
    # Create a cleaner filename
    clean_name=$(echo "$filename" | tr ' ' '-' | tr '[:upper:]' '[:lower:]')
    cp "$file" "docs/screenshots/$clean_name"
    echo "📸 Copied: $filename -> $clean_name"
done

if [ $? -eq 0 ]; then
    echo "✅ Screenshots copied successfully!"
    echo ""
    echo "📸 Screenshots in docs/screenshots/:"
    ls -la docs/screenshots/
    
    echo ""
    echo "📝 Next steps:"
    echo "1. Review the copied screenshots"
    echo "2. Rename files if needed to match the naming convention:"
    echo "   - dashboard-overview.png"
    echo "   - ios-app-home.png" 
    echo "   - object-detection-demo.png"
    echo "   - face-recognition-demo.png"
    echo "   - system-configuration.png"
    echo "   - push-notification.png"
    echo "3. Run: git add docs/screenshots/"
    echo "4. Run: git commit -m '📸 Add project screenshots and live demos'"
    echo "5. Run: git push origin main"
    
    echo ""
    echo "🎯 Pro Tip: The README.md already references these image names:"
    echo "- docs/screenshots/dashboard-overview.png"
    echo "- docs/screenshots/ios-app-home.png"
    echo "- docs/screenshots/object-detection-demo.png"
    echo "- docs/screenshots/face-recognition-demo.png"
    echo "- docs/screenshots/system-configuration.png"
    echo "- docs/screenshots/push-notification.png"
    
else
    echo "❌ No image files found or copy failed"
    echo "Please check that you have image files in: $SCREENSHOTS_DIR"
fi

echo ""
echo "🌟 Your open-source project will look amazing with these screenshots!"