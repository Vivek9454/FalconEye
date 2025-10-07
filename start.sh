#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Start the Flask application
echo "Starting FalconEye backend..."
python backend.py &

# Wait a moment for the app to start
sleep 3

# Start Cloudflare tunnel
echo "Starting Cloudflare tunnel..."
cloudflared tunnel --url http://localhost:3000 --hostname cam.falconeye.website

# Keep the script running
wait
