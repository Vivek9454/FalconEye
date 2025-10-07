#!/usr/bin/env python3
"""
Simple Firebase Setup using Project ID
This approach doesn't require downloading the private key
"""

import requests
import json

def test_firebase_simple():
    print("🔥 Testing Firebase with Project ID")
    print("=" * 40)
    
    # Test if we can use the project ID approach
    project_id = "falconeye-security"
    service_account_email = "firebase-adminsdk-fbsvc@falconeye-security.iam.gserviceaccount.com"
    
    print(f"📊 Project ID: {project_id}")
    print(f"📧 Service Account: {service_account_email}")
    
    # Test backend status
    try:
        response = requests.get("http://localhost:3000/fcm/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend is running")
            print(f"📊 FCM Status: {data}")
            
            if data.get("fcm_enabled"):
                print("✅ Firebase is properly configured!")
                print("🎉 You can now test push notifications")
            else:
                print("❌ Firebase not configured")
                print("📝 Need to get the private key from Firebase Console")
        else:
            print(f"❌ Backend error: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
    
    print("\n" + "=" * 40)
    print("📋 Next Steps:")
    print("1. Look for 'Keys' or 'Download' button in Firebase Console")
    print("2. Download the JSON key file")
    print("3. Extract the 'private_key' field")
    print("4. Update FCM_SERVER_KEY in backend.py")
    print("5. Test with this script again")

if __name__ == "__main__":
    test_firebase_simple()





























