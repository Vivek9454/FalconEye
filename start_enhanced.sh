#!/bin/bash

# FalconEye Enhanced Startup Script
# Includes all mobile optimizations and permanent tunnel

echo "🚀 Starting FalconEye Enhanced System..."
echo "📱 Mobile-optimized with permanent Cloudflare tunnel"
echo "=================================================="

# Kill any existing processes
echo "🔄 Stopping existing processes..."
pkill -f "python backend.py" 2>/dev/null
pkill cloudflared 2>/dev/null
sleep 2

# Start the enhanced backend
echo "🐍 Starting enhanced backend with mobile optimizations..."
source venv/bin/activate
python backend.py &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to initialize..."
sleep 5

# Check if backend is running
if ps -p $BACKEND_PID > /dev/null; then
    echo "✅ Backend started successfully (PID: $BACKEND_PID)"
else
    echo "❌ Backend failed to start"
    exit 1
fi

# Test backend
echo "🧪 Testing backend..."
if curl -s http://localhost:3000/system/status > /dev/null; then
    echo "✅ Backend is responding"
else
    echo "❌ Backend is not responding"
    exit 1
fi

# Start permanent Cloudflare tunnel
echo "🌐 Starting permanent Cloudflare tunnel..."
cloudflared tunnel --config falconeye-permanent-config.yml run falconeye-permanent-enhanced &
TUNNEL_PID=$!

# Wait for tunnel to start
echo "⏳ Waiting for tunnel to initialize..."
sleep 10

# Test the tunnel
echo "🧪 Testing tunnel..."
if curl -s -I https://cam.falconeye.website > /dev/null; then
    echo "✅ Tunnel is working - https://cam.falconeye.website"
else
    echo "⚠️  Tunnel may still be initializing..."
fi

echo ""
echo "🎉 FalconEye Enhanced System is running!"
echo "=================================================="
echo "📱 Mobile Dashboard: https://cam.falconeye.website"
echo "🖥️  Local Dashboard: http://localhost:3000"
echo "📊 System Status: http://localhost:3000/system/status"
echo "📱 Mobile APIs:"
echo "   • /mobile/status - Mobile system status"
echo "   • /mobile/clips/summary - Optimized clips overview"
echo "   • /mobile/camera/info - Camera information"
echo ""
echo "🔧 Features Active:"
echo "   ✅ High-speed frame capture (10 FPS)"
echo "   ✅ Mobile-optimized streaming (3.3 FPS mobile, 5 FPS desktop)"
echo "   ✅ Object detection filtering (home surveillance only)"
echo "   ✅ Touch-friendly interface with swipe navigation"
echo "   ✅ Bandwidth optimization (50% less data on mobile)"
echo "   ✅ Responsive design for all screen sizes"
echo "   ✅ Push notifications"
echo "   ✅ AWS S3 video upload"
echo "   ✅ Permanent Cloudflare tunnel"
echo ""
echo "📱 Mobile Features:"
echo "   • Swipe between Live, Clips, Status tabs"
echo "   • Touch-friendly controls (44px minimum)"
echo "   • Auto-refresh every 30 seconds"
echo "   • Progressive image loading"
echo "   • Dark mode support"
echo "   • Landscape orientation support"
echo ""
echo "🛑 To stop: Press Ctrl+C or run 'pkill -f python backend.py && pkill cloudflared'"
echo ""

# Keep script running and show logs
echo "📋 System Logs:"
echo "=================================================="
tail -f /dev/null &
wait





























