#!/bin/bash

# Stop FalconEye services and free up ports
echo "🛑 Stopping FalconEye Services"
echo "=============================="

# Kill backend processes
echo "🔄 Stopping backend..."
pkill -f "python backend.py"
if [ $? -eq 0 ]; then
    echo "✅ Backend stopped"
else
    echo "ℹ️  No backend process found"
fi

# Kill Cloudflare processes
echo "🔄 Stopping Cloudflare tunnel..."
pkill cloudflared
if [ $? -eq 0 ]; then
    echo "✅ Cloudflare tunnel stopped"
else
    echo "ℹ️  No Cloudflare process found"
fi

# Force kill any processes on port 3000
echo "🔄 Freeing up port 3000..."
PORT_PIDS=$(lsof -ti :3000 2>/dev/null)
if [ ! -z "$PORT_PIDS" ]; then
    echo "⚠️  Found processes on port 3000: $PORT_PIDS"
    kill -9 $PORT_PIDS 2>/dev/null
    echo "✅ Port 3000 freed"
else
    echo "✅ Port 3000 is already free"
fi

# Wait for ports to be released
sleep 2

echo ""
echo "✅ All FalconEye services stopped!"
echo "🚀 You can now run './start_smart.sh' to start fresh"
