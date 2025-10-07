#!/bin/bash

# Simple script to start both backend and Cloudflare
echo "🚀 Starting FalconEye Backend and Cloudflare..."

# Kill any existing processes
pkill -f "python backend.py" 2>/dev/null
pkill cloudflared 2>/dev/null
sleep 2

# Start backend in background
echo "🐍 Starting backend..."
source venv/bin/activate
python backend.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 5

# Start Cloudflare in background
echo "🌐 Starting Cloudflare tunnel..."
cloudflared tunnel --config falconeye-permanent-config.yml run falconeye-permanent-enhanced &
TUNNEL_PID=$!

echo ""
echo "✅ Both services started!"
echo "📱 Local Dashboard: http://localhost:3000"
echo "🌐 Remote Dashboard: https://cam.falconeye.website"
echo ""
echo "🛑 To stop: Press Ctrl+C or run 'pkill -f python backend.py && pkill cloudflared'"
echo ""

# Keep script running
wait
