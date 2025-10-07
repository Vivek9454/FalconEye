# 🚀 FalconEye Enhanced - Mobile-Optimized Home Security System

A comprehensive home security system with AI-powered object detection, mobile optimization, and permanent cloud access.

## ✨ Features

### 🎯 Core Security Features
- **AI Object Detection**: YOLO-powered real-time detection
- **Smart Filtering**: Only detects home surveillance relevant objects
- **High-Speed Capture**: 10 FPS frame capture from ESP32 camera
- **Video Recording**: Automatic recording when objects detected
- **Push Notifications**: Real-time alerts via Firebase
- **Cloud Storage**: AWS S3 integration for video clips

### 📱 Mobile Optimizations
- **Responsive Design**: Works perfectly on all screen sizes
- **Touch Navigation**: Swipe between Live, Clips, Status tabs
- **Bandwidth Optimization**: 50% less data usage on mobile
- **Auto-Detection**: Automatically detects mobile devices
- **Quality Adjustment**: Lower quality for mobile to save bandwidth
- **Touch-Friendly**: 44px minimum touch targets
- **Swipe Gestures**: Navigate with finger swipes
- **Progressive Loading**: Images load with smooth transitions
- **Dark Mode**: Automatic dark theme support
- **Landscape Support**: Optimized for both orientations

### 🌐 Cloud & Access
- **Permanent Tunnel**: Always-available cloud access
- **Custom Domain**: https://cam.falconeye.website
- **SSL Security**: Encrypted connections
- **Global CDN**: Fast access worldwide
- **Mobile APIs**: Optimized endpoints for mobile apps

## 🚀 Quick Start

### Option 1: Enhanced Startup (Recommended)
```bash
./start_enhanced.sh
```

### Option 2: Manual Startup
```bash
# Start backend
source venv/bin/activate
python backend.py &

# Start tunnel
cloudflared tunnel --config falconeye-permanent-config.yml run falconeye-permanent-enhanced
```

## 📱 Mobile Access

**🌐 Public URL**: https://cam.falconeye.website
**🖥️ Local URL**: http://localhost:3000

### Mobile Features
- **Live Stream**: Real-time camera feed with object detection
- **Clips**: Browse recorded videos by date
- **Status**: System information and statistics
- **Swipe Navigation**: Swipe left/right between tabs
- **Touch Controls**: Large, finger-friendly buttons

## 🔧 Mobile APIs

### System Status
```bash
curl https://cam.falconeye.website/mobile/status
```

### Clips Summary
```bash
curl https://cam.falconeye.website/mobile/clips/summary
```

### Camera Info
```bash
curl https://cam.falconeye.website/mobile/camera/info
```

## 🎯 Object Detection

### Detected Objects (Home Surveillance Only)
- **People & Animals**: person, cat, dog, bird, horse, cow, elephant, bear, zebra, giraffe
- **Vehicles**: car, truck, bus, motorcycle, bicycle, boat, airplane, train
- **Suspicious Items**: backpack, handbag, suitcase, bottle, wine glass, cup, fork, knife, spoon, bowl
- **Electronics**: laptop, mouse, remote, keyboard, cell phone, book, scissors, teddy bear, hair drier, toothbrush

### Filtered Out (Not Detected)
- Furniture: chair, table, lamp, couch, bed
- Kitchen items: refrigerator, oven, microwave, toaster
- Random objects: clock, vase, plant, etc.

## ⚡ Performance

### Desktop Performance
- **Live Stream**: 5 FPS, 85% JPEG quality
- **Frame Capture**: 10 FPS from ESP32
- **Object Detection**: Real-time with YOLO
- **Video Recording**: 15-second clips at 10 FPS

### Mobile Performance
- **Live Stream**: 3.3 FPS, 70% JPEG quality
- **Bandwidth**: 50% less data usage
- **Resolution**: Max 640px width
- **Touch Response**: <100ms

## 🛠️ Technical Details

### Backend Technologies
- **Python 3.13**: Core application
- **Flask**: Web framework
- **YOLO (Ultralytics)**: Object detection
- **OpenCV**: Image processing
- **PyTorch**: AI framework (MPS for Apple Silicon)
- **Boto3**: AWS S3 integration
- **Requests**: HTTP client

### Mobile Optimizations
- **Viewport Meta Tag**: Proper mobile scaling
- **CSS Grid**: Responsive layouts
- **Touch Events**: Swipe gestures
- **Progressive Enhancement**: Graceful degradation
- **Bandwidth Detection**: Automatic quality adjustment
- **Caching**: Optimized for mobile browsers

### Cloud Infrastructure
- **Cloudflare Tunnel**: Secure cloud access
- **Custom Domain**: cam.falconeye.website
- **SSL/TLS**: Encrypted connections
- **Global CDN**: Worldwide distribution
- **AWS S3**: Video storage

## 📊 System Requirements

### Minimum Requirements
- **Python**: 3.8+
- **RAM**: 4GB
- **Storage**: 10GB free space
- **Network**: Stable internet connection

### Recommended
- **Python**: 3.13+
- **RAM**: 8GB+
- **Storage**: 50GB+ free space
- **GPU**: Apple Silicon (M1/M2) or NVIDIA GPU
- **Network**: High-speed internet

## 🔒 Security Features

- **Authentication**: Password-protected access
- **HTTPS**: Encrypted connections
- **Tunnel Security**: Cloudflare protection
- **Object Filtering**: Only relevant detections
- **Data Privacy**: Local processing, cloud storage

## 📱 Mobile Browser Support

- **iOS Safari**: 14+
- **Chrome Mobile**: 90+
- **Firefox Mobile**: 88+
- **Samsung Internet**: 13+
- **Edge Mobile**: 90+

## 🚨 Troubleshooting

### Common Issues

**Tunnel Not Working**
```bash
# Check tunnel status
ps aux | grep cloudflared

# Restart tunnel
pkill cloudflared
cloudflared tunnel --config falconeye-permanent-config.yml run falconeye-permanent-enhanced
```

**Mobile Not Optimized**
```bash
# Check mobile detection
curl -H "User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)" https://cam.falconeye.website/mobile/status
```

**Object Detection Issues**
```bash
# Check detection logs
tail -f /dev/null | grep "Detected:"
```

## 📈 Performance Monitoring

### Backend Logs
```bash
# View real-time logs
tail -f /dev/null | grep -E "(Detected|CAPTURE|LIVE STREAM)"
```

### Mobile Performance
- Check `/mobile/status` for system info
- Monitor bandwidth usage in browser dev tools
- Test touch responsiveness

## 🔄 Updates

### Updating the System
```bash
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
./start_enhanced.sh
```

### Configuration Changes
- Edit `falconeye-permanent-config.yml` for tunnel settings
- Edit `backend.py` for detection parameters
- Restart system after changes

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review system logs
3. Test mobile APIs
4. Verify tunnel connectivity

## 🎉 Success!

Your FalconEye Enhanced system is now running with:
- ✅ Mobile-optimized interface
- ✅ Permanent cloud access
- ✅ Smart object detection
- ✅ High-performance streaming
- ✅ Touch-friendly controls
- ✅ Bandwidth optimization

**Access your system at: https://cam.falconeye.website** 📱✨





























