# FCM Setup Guide for FalconEye iOS App

## Current Status ✅
- Backend FCM is already configured and working
- iOS app has FCM integration code ready (currently simulated)
- GoogleService-Info.plist is present
- Backend shows "No tokens registered" (expected until iOS app registers)
- App builds successfully with simulated FCM

## What You Need to Do:

### Step 1: Add Firebase SDK to Xcode Project
1. **Open your project in Xcode**
2. **Go to File → Add Package Dependencies**
3. **Enter this URL**: `https://github.com/firebase/firebase-ios-sdk.git`
4. **Click Add Package**
5. **Select these packages**:
   - ✅ FirebaseAuth
   - ✅ FirebaseMessaging
   - ✅ FirebaseAnalytics
6. **Click Add Package**

### Step 2: Enable Push Notifications Capability
1. **In Xcode, select your project**
2. **Go to Signing & Capabilities**
3. **Click + Capability**
4. **Add Push Notifications**

### Step 3: Uncomment Firebase Code
After adding Firebase SDK, uncomment these lines in your code:

**In `FalconEyeApp.swift`:**
```swift
import Firebase  // Uncomment this line

init() {
    FirebaseApp.configure()  // Uncomment this line
    // ... rest of init
}
```

**In `NotificationManager.swift`:**
```swift
import Firebase
import FirebaseMessaging  // Uncomment these lines

private func setupFirebase() {
    FirebaseApp.configure()  // Uncomment this line
    
    Messaging.messaging().delegate = self  // Uncomment this line
    
    Messaging.messaging().token { [weak self] token, error in  // Uncomment this block
        if let error = error {
            print("❌ FCM Token Error: \(error)")
        } else if let token = token {
            print("✅ FCM Token: \(token)")
            DispatchQueue.main.async {
                self?.fcmToken = token
                self?.registerFCMToken()
            }
        }
    }
}

// Uncomment the entire FCM Delegate extension:
extension NotificationManager: MessagingDelegate {
    func messaging(_ messaging: Messaging, didReceiveRegistrationToken fcmToken: String?) {
        print("🔄 FCM Registration token: \(fcmToken ?? "nil")")
        
        DispatchQueue.main.async {
            self.fcmToken = fcmToken
            if fcmToken != nil {
                self.registerFCMToken()
            }
        }
    }
}
```

### Step 4: Test the Setup
1. **Build and run the app**
2. **Go to Settings → Push Notifications**
3. **Tap "Request Permission" if needed**
4. **Check if FCM token appears**
5. **Test with "Test Notification" button**

## Backend FCM Endpoints Available:
- `POST /fcm/register` - Register FCM token
- `POST /fcm/unregister` - Unregister FCM token  
- `POST /fcm/test` - Send test notification
- `GET /fcm/status` - Check FCM status

## Expected Flow:
1. **App launches** → Firebase configures → FCM token generated
2. **Token automatically sent** to backend via `/fcm/register`
3. **Backend can now send** push notifications to your device
4. **When person detected** → Backend sends notification to all registered devices

## Current Simulation:
- App currently uses a simulated FCM token: `simulated-fcm-token-12345`
- This allows testing the notification UI without Firebase SDK
- Backend will receive this simulated token for testing

## Troubleshooting:
- If "No tokens registered" persists, check iOS console logs for FCM errors
- Make sure Push Notifications capability is enabled
- Verify GoogleService-Info.plist is properly added to project
- Check that Firebase SDK is properly linked in project settings
