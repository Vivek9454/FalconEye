# Firebase Service Account Setup for FCM v1 API

Since Google has disabled the Legacy Server Key for new Firebase projects, we need to use the FCM v1 API with a service account key.

## Step 1: Create a Service Account

1. **Go to Firebase Console**: https://console.firebase.google.com/
2. **Select your project**: `falconeye-security`
3. **Go to Project Settings** (gear icon in the top left)
4. **Go to "Service accounts" tab**
5. **Click "Generate new private key"**
6. **Download the JSON file** (it will be named something like `falconeye-security-xxxxx.json`)

## Step 2: Place the Service Account Key

1. **Rename the downloaded file** to `firebase-service-account.json`
2. **Place it in your FalconEye project directory**: `/Users/vpaul/FalconEye/firebase-service-account.json`

## Step 3: Test the Setup

The notification service will automatically detect the service account key and use FCM v1 API.

## Alternative: Environment Variable

You can also set the path as an environment variable:

```bash
export FIREBASE_SERVICE_ACCOUNT_PATH="/path/to/your/service-account-key.json"
```

## What This Enables

- ✅ **FCM v1 API**: Modern, secure Firebase Cloud Messaging
- ✅ **Real Push Notifications**: Actual notifications sent to your iOS device
- ✅ **Better Error Handling**: More detailed error messages
- ✅ **Future-Proof**: Uses Google's current recommended approach

## Security Note

⚠️ **Keep your service account key secure!** Never commit it to version control. The key file contains sensitive credentials that should be kept private.

## Testing

Once you've placed the service account key file, restart the backend and test:

```bash
# Restart backend
pkill -f "python backend.py"
source venv/bin/activate && python backend.py &

# Test notification
curl -X POST -H "Content-Type: application/json" -d '{"token":"test_token","platform":"ios"}' http://localhost:3000/fcm/register
curl -X POST -H "Content-Type: application/json" -d '{"token":"test_token"}' http://localhost:3000/fcm/test
```

The system will automatically detect the service account key and switch from fallback mode to real FCM v1 API.

