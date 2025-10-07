# Cloudflare Tunnel Setup for FalconEye

## Step 1: Get Your Cloudflare Tunnel Domain

1. **Start your backend server** (if not already running):
   ```bash
   cd /Users/vpaul/FalconEye
   python3 backend.py
   ```

2. **Look for the Cloudflare tunnel URL** in the terminal output. It will look like:
   ```
   https://your-random-subdomain.trycloudflare.com
   ```

3. **Copy the tunnel URL** (e.g., `https://abc123.trycloudflare.com`)

## Step 2: Update the iOS App

1. **Open the NetworkManager.swift file**:
   ```
   /Users/vpaul/Downloads/FalconEye/FalconEye/Services/NetworkManager.swift
   ```

2. **Replace the placeholder URL** on line 12:
   ```swift
   private let cloudflareBaseURL = "https://your-tunnel-domain.trycloudflare.com" // TODO: Replace with your actual Cloudflare tunnel domain
   ```
   
   With your actual tunnel URL:
   ```swift
   private let cloudflareBaseURL = "https://abc123.trycloudflare.com" // Your actual tunnel domain
   ```

3. **Save the file and rebuild the app**:
   ```bash
   xcodebuild build -project FalconEye.xcodeproj -scheme FalconEye -destination 'platform=iOS,id=00008140-0010192C36F2801C' -configuration Debug
   xcrun devicectl device install app --device 93BFA7B4-A31E-5B13-B58A-D6C73DF05391 /Users/vpaul/Library/Developer/Xcode/DerivedData/FalconEye-cgzabvohvqjcaidjxuersnlkjtem/Build/Products/Debug-iphoneos/FalconEye.app
   ```

## How It Works

### Local Network Detection
- **When on WiFi**: The app automatically detects if it can reach `http://192.168.31.233:3000`
- **If reachable**: Uses local network for faster, more reliable connection
- **If not reachable**: Falls back to Cloudflare tunnel

### Cloudflare Tunnel
- **When on cellular data**: Automatically uses your Cloudflare tunnel URL
- **When on other WiFi networks**: Uses Cloudflare tunnel if local server is unreachable

### Visual Indicators
- **Green dot + "Local"**: Connected to local network
- **Blue dot + "Cloud"**: Connected via Cloudflare tunnel
- **Settings page**: Shows current connection type and server URL

## Testing

1. **Test local connection**:
   - Connect to your home WiFi
   - Open the app - should show "Local" with green dot
   - Check Settings > Network Status

2. **Test cloud connection**:
   - Switch to cellular data or different WiFi
   - Open the app - should show "Cloud" with blue dot
   - Check Settings > Network Status

## Troubleshooting

- **If app shows "Cloud" on local network**: Check if your backend server is running
- **If app can't connect**: Verify the Cloudflare tunnel URL is correct
- **Manual refresh**: Use the "Refresh Network Status" button in Settings
