#!/bin/bash

# Smart startup script that handles port conflicts
echo "🚀 FalconEye Smart Startup"
echo "=========================="

# Function to find available port
find_available_port() {
    local port=3000
    while lsof -i :$port >/dev/null 2>&1; do
        port=$((port + 1))
    done
    echo $port
}

# Function to kill processes on specific port
kill_port() {
    local port=$1
    local pids=$(lsof -ti :$port)
    if [ ! -z "$pids" ]; then
        echo "🔄 Killing processes on port $port: $pids"
        kill -9 $pids 2>/dev/null
        sleep 2
    fi
}

# Kill any existing FalconEye processes
echo "🔄 Stopping existing processes..."
pkill -f "python backend.py" 2>/dev/null
pkill cloudflared 2>/dev/null
sleep 3

# Check if port 3000 is still in use
if lsof -i :3000 >/dev/null 2>&1; then
    echo "⚠️  Port 3000 is still in use, finding alternative..."
    kill_port 3000
    
    # Find available port
    AVAILABLE_PORT=$(find_available_port)
    echo "✅ Using port $AVAILABLE_PORT instead"
    
    # Update backend.py to use new port
    sed -i.bak "s/port=3000/port=$AVAILABLE_PORT/g" backend.py
    sed -i.bak "s/localhost:3000/localhost:$AVAILABLE_PORT/g" backend.py
    
    # Update Cloudflare config to use new port
    sed -i.bak "s/http:\/\/localhost:3000/http:\/\/localhost:$AVAILABLE_PORT/g" falconeye-permanent-config.yml
    
    echo "📝 Updated configuration to use port $AVAILABLE_PORT"
else
    AVAILABLE_PORT=3000
    echo "✅ Port 3000 is available"
fi

# Start backend
echo "🐍 Starting backend on port $AVAILABLE_PORT..."
source venv/bin/activate
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export ORT_NUM_THREADS=1
python backend.py &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to initialize..."
sleep 5

# Check if backend started successfully
if ps -p $BACKEND_PID > /dev/null; then
    echo "✅ Backend started successfully (PID: $BACKEND_PID)"
else
    echo "❌ Backend failed to start"
    exit 1
fi

# Ensure Cloudflare DNS route is set for the tunnel to avoid 1033
echo "🔧 Ensuring Cloudflare DNS route (cam.falconeye.website → tunnel)"
if command -v cloudflared >/dev/null 2>&1; then
    echo "➡️  Binding hostname to named tunnel..."
    if ! cloudflared tunnel route dns falconeye-permanent-enhanced cam.falconeye.website; then
        echo "❌ Failed to bind DNS route via cloudflared. This can cause 1033."
        echo "   Make sure this machine is logged in (cloudflared login) and the zone falconeye.website"
        echo "   is in the same Cloudflare account as the tunnel credentials."
    fi
else
    echo "⚠️  cloudflared not found in PATH; skipping DNS route binding"
fi

# Start Cloudflare tunnel
echo "🌐 Starting Cloudflare tunnel..."
cloudflared tunnel --config falconeye-permanent-config.yml run falconeye-permanent-enhanced &
TUNNEL_PID=$!

# Wait for tunnel to start
sleep 5

# Print tunnel diagnostics
if command -v cloudflared >/dev/null 2>&1; then
    echo "🔎 Tunnel list (summary):"
    cloudflared tunnel list 2>/dev/null | sed -n '1,40p' || true
    echo "🔎 Tunnel info (routes + conns):"
    cloudflared tunnel info falconeye-permanent-enhanced 2>/dev/null | sed -n '1,120p' || true
    echo "🔎 DNS routes (filter hostname):"
    cloudflared tunnel route dns list 2>/dev/null | grep -E "cam\.falconeye\.website|Tunnel|Hostname" -n || true
fi

# Quick DNS check for the hostname's CNAME
if command -v dig >/dev/null 2>&1; then
    echo "🔍 Checking DNS CNAME for cam.falconeye.website..."
    ACTUAL_CNAME=$(dig +short cam.falconeye.website CNAME || true)
    echo "Actual CNAME: ${ACTUAL_CNAME:-<none>}"
elif command -v host >/dev/null 2>&1; then
    echo "🔍 Checking DNS CNAME for cam.falconeye.website..."
    host -t CNAME cam.falconeye.website || true
fi

# Validate CNAME points to this tunnel UUID
EXPECTED_CNAME="bc212e8f-87cd-4bf1-80fd-c9269c1bd072.cfargotunnel.com"
if [ -n "$ACTUAL_CNAME" ] && [ "$ACTUAL_CNAME" != "$EXPECTED_CNAME." ] && [ "$ACTUAL_CNAME" != "$EXPECTED_CNAME" ]; then
    echo "⚠️  DNS mismatch: cam.falconeye.website CNAME is '$ACTUAL_CNAME'"
    echo "   but expected '$EXPECTED_CNAME'. This causes Cloudflare error 1033."
    echo "   Fix: In Cloudflare DNS, set cam.falconeye.website as a proxied CNAME to:"
    echo "        $EXPECTED_CNAME (orange cloud ON)."
fi

echo ""
echo "🎉 FalconEye is running!"
echo "=========================="
echo "📱 Local Dashboard: http://localhost:$AVAILABLE_PORT"
echo "🌐 Remote Dashboard: https://cam.falconeye.website"
echo "🔎 Tunnel: falconeye-permanent-enhanced"
echo "🔎 Tunnel UUID: bc212e8f-87cd-4bf1-80fd-c9269c1bd072"
echo "🔎 Hostname: cam.falconeye.website"
echo "🔎 Expected CNAME: bc212e8f-87cd-4bf1-80fd-c9269c1bd072.cfargotunnel.com"
echo ""
echo "🛑 To stop: Press Ctrl+C or run 'pkill -f python backend.py && pkill cloudflared'"
echo ""

# Keep script running
wait
