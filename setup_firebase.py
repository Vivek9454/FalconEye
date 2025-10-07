#!/usr/bin/env python3
"""
Firebase Setup Helper
Helps you configure Firebase for FalconEye
"""

import os
import re

def setup_firebase():
    print("🔥 FalconEye Firebase Setup Helper")
    print("=" * 50)
    
    print("\n📋 Step 1: Create Firebase Project")
    print("1. Go to: https://console.firebase.google.com/")
    print("2. Click 'Create a project'")
    print("3. Project name: falconeye-security")
    print("4. Enable Analytics (recommended)")
    
    print("\n📋 Step 2: Enable Cloud Messaging")
    print("1. In Firebase dashboard, click 'Build' → 'Cloud Messaging'")
    print("2. Click 'Get started'")
    
    print("\n📋 Step 3: Add Android App")
    print("1. Click Android icon (📱) or 'Add app'")
    print("2. Package name: com.falconeye")
    print("3. App nickname: FalconEye Security")
    print("4. Download google-services.json")
    print("5. Save to: android_app/app/google-services.json")
    
    print("\n📋 Step 4: Get Server Key")
    print("1. Click gear icon (⚙️) → 'Project settings'")
    print("2. Go to 'Cloud Messaging' tab")
    print("3. Copy the 'Server key' (starts with AAAA...)")
    
    # Get server key from user
    print("\n🔑 Enter your Firebase Server Key:")
    print("(It should start with 'AAAA...' and be about 150+ characters)")
    server_key = input("Server Key: ").strip()
    
    if not server_key.startswith("AAAA"):
        print("❌ Invalid server key format. Should start with 'AAAA...'")
        return
    
    if len(server_key) < 100:
        print("❌ Server key seems too short. Please check and try again.")
        return
    
    # Update backend.py
    try:
        with open("backend.py", "r") as f:
            content = f.read()
        
        # Replace the placeholder
        content = re.sub(
            r'FCM_SERVER_KEY = "YOUR_ACTUAL_FIREBASE_SERVER_KEY_HERE"',
            f'FCM_SERVER_KEY = "{server_key}"',
            content
        )
        
        with open("backend.py", "w") as f:
            f.write(content)
        
        print("✅ Updated backend.py with your server key")
        
    except Exception as e:
        print(f"❌ Error updating backend.py: {e}")
        return
    
    print("\n🔄 Restarting backend...")
    os.system("pkill -f 'python backend.py' 2>/dev/null")
    os.system("source venv/bin/activate && python backend.py &")
    
    print("\n⏳ Waiting for backend to start...")
    import time
    time.sleep(3)
    
    # Test the setup
    try:
        import requests
        response = requests.get("http://localhost:3000/fcm/status")
        if response.status_code == 200:
            data = response.json()
            if data.get("fcm_enabled"):
                print("🎉 Firebase setup successful!")
                print("✅ FCM is now enabled")
                print("📱 You can now build and test the Android app")
            else:
                print("❌ Firebase still not enabled. Check your server key.")
        else:
            print("❌ Backend not responding. Please restart manually.")
    except Exception as e:
        print(f"❌ Error testing setup: {e}")
    
    print("\n📱 Next Steps:")
    print("1. Build Android app: cd android_app && ./gradlew assembleDebug")
    print("2. Install on device: adb install app/build/outputs/apk/debug/app-debug.apk")
    print("3. Test push notifications")
    print("4. Test object detection alerts")

if __name__ == "__main__":
    setup_firebase()





























