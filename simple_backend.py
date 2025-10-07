#!/usr/bin/env python3
"""
Simplified FalconEye Backend - Focus on Live Stream
Optimized for ESP32 camera with better stream handling
"""

import os
import cv2
import time
import uuid
import json
import boto3
import threading
import requests
import numpy as np
from datetime import datetime
from ultralytics import YOLO
from flask import Flask, request, jsonify, Response, send_from_directory, render_template_string
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import torch

# ---------------- CONFIG ----------------
CAMERAS = {
    "cam1": "http://192.168.225.6/jpg",  # Your ESP32 camera
}

OUTPUT_DIR = "clips"
METADATA_FILE = os.path.join(OUTPUT_DIR, "metadata.json")

# Create directories
os.makedirs(OUTPUT_DIR, exist_ok=True)
if not os.path.exists(METADATA_FILE):
    with open(METADATA_FILE, "w") as f:
        json.dump({}, f)

# ---------------- Device Selection ----------------
if torch.cuda.is_available():
    DEVICE = "cuda"
    GPU_NAME = torch.cuda.get_device_name(0)
    print(f"[INFO] CUDA available ✅ Using GPU: {GPU_NAME}")
elif torch.backends.mps.is_available():
    DEVICE = "mps"  # Apple Metal Performance Shaders for M1/M2
    GPU_NAME = "Apple Silicon GPU"
    print(f"[INFO] MPS available ✅ Using Apple Silicon GPU")
else:
    DEVICE = "cpu"
    GPU_NAME = None
    print("[INFO] No GPU acceleration available ⚠️ Falling back to CPU")

# Load YOLO model
print("Loading YOLO model...")
model = YOLO("yolov8s.pt").to(DEVICE)
print("YOLO model loaded!")

app = Flask(__name__)
CORS(app)

# Global variables for frame sharing
current_frame = None
frame_lock = threading.Lock()
last_frame_time = 0

# ---------------- Frame Capture ----------------
def capture_frames():
    """Continuously capture frames from ESP32 camera"""
    global current_frame, last_frame_time
    
    print(f"[CAPTURE] Starting high-speed frame capture from ESP32...")
    
    # Use session for connection pooling
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'image/jpeg,image/*,*/*',
        'Connection': 'keep-alive'
    })
    
    consecutive_failures = 0
    frame_count = 0
    
    while True:
        try:
            # Get frame from ESP32 with shorter timeout
            resp = session.get(CAMERAS["cam1"], timeout=1.5, stream=False)
            if resp.status_code == 200:
                # Convert to OpenCV image
                img_arr = np.frombuffer(resp.content, np.uint8)
                frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    with frame_lock:
                        current_frame = frame.copy()
                        last_frame_time = time.time()
                    
                    consecutive_failures = 0
                    frame_count += 1
                    
                    # Print status every 50 frames
                    if frame_count % 50 == 0:
                        print(f"[CAPTURE] Captured {frame_count} frames successfully")
                else:
                    consecutive_failures += 1
            else:
                consecutive_failures += 1
                
        except Exception as e:
            consecutive_failures += 1
            if consecutive_failures % 20 == 0:  # Print error every 20 failures
                print(f"[CAPTURE] Error (attempt {consecutive_failures}): {e}")
        
        # Much faster capture rate - 10 FPS
        time.sleep(0.1)

def get_latest_frame():
    """Get the latest captured frame"""
    global current_frame, last_frame_time
    
    with frame_lock:
        if current_frame is not None and time.time() - last_frame_time < 10:  # More lenient timeout
            return current_frame.copy()
        else:
            return None

def create_placeholder():
    """Create a placeholder image when camera is offline"""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:] = (50, 50, 50)  # Dark gray background
    
    cv2.putText(img, "ESP32 Camera Offline", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.putText(img, "FalconEye AI Detection", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(img, "Waiting for connection...", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
    
    return img

# ---------------- Dashboard ----------------
dashboard_html = """
<!DOCTYPE html>
<html>
<head>
    <title>FalconEye Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; background: #111; color: #eee; margin:0; padding:0; }
        header { background:#0f9d58; padding:15px; text-align:center; font-size:24px; color:#fff; }
        .container { padding:20px; }
        h2 { color: #0f9d58; }
        .section { margin: 20px 0; }
        video, img { border: 2px solid #444; border-radius: 10px; max-width: 100%; }
        .status { background: #222; padding: 10px; border-radius: 5px; margin: 10px 0; }
        .live-stream { text-align: center; }
    </style>
</head>
<body>
<header>FalconEye Dashboard</header>
<div class="container">
    <div class="section">
        <h2>Live Stream from ESP32 Camera</h2>
        <div class="live-stream">
            <img src="/camera/live/cam1" width="640" height="480" />
        </div>
        <div class="status">
            <p><strong>Camera:</strong> ESP32 at 192.168.225.6</p>
            <p><strong>Status:</strong> <span id="status">Live</span></p>
            <p><strong>AI Detection:</strong> Active with YOLOv8</p>
            <p><strong>FPS:</strong> ~5 FPS Live Stream</p>
        </div>
    </div>

    <div class="section">
        <h2>Snapshot</h2>
        <img src="/camera/snapshot/cam1" width="320" height="240" />
    </div>

    <div class="section">
        <h2>System Status</h2>
        <div class="status">
            <p><strong>Device:</strong> {{ device }}</p>
            <p><strong>GPU:</strong> {{ gpu }}</p>
            <p><strong>Model:</strong> YOLOv8s</p>
        </div>
    </div>
</div>

<script>
// Update status
setInterval(() => {
    fetch('/system/status')
        .then(response => response.json())
        .then(data => {
            document.getElementById('status').textContent = 'Connected';
        })
        .catch(error => {
            document.getElementById('status').textContent = 'Disconnected';
        });
}, 5000);
</script>
</body>
</html>
"""

@app.route("/")
def dashboard():
    return render_template_string(dashboard_html, 
                                device=DEVICE, 
                                gpu=GPU_NAME if DEVICE != "cpu" else "None")

@app.route("/camera/live/<cam_id>")
def live(cam_id):
    """Live stream from ESP32 camera"""
    def gen():
        frame_count = 0
        last_sent_frame = None
        
        while True:
            frame = get_latest_frame()
            
            if frame is None:
                # If no frame available, wait briefly and try again
                time.sleep(0.1)
                continue
            
            # Only process if we have a new frame
            if frame is not last_sent_frame:
                # Perform object detection
                results = model(frame, conf=0.25, verbose=False)
                annotated = results[0].plot()
                
                # Add status text
                cv2.putText(annotated, f"ESP32 Live - Frame: {frame_count}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(annotated, "FalconEye AI Detection", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Show detected objects
                if results[0].boxes:
                    objects = [model.names[int(c)] for c in results[0].boxes.cls.tolist()]
                    cv2.putText(annotated, f"Detected: {', '.join(objects)}", (10, 90), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                
                # Encode and send
                _, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
                
                last_sent_frame = frame
                frame_count += 1
                
                # Print status every 100 frames
                if frame_count % 100 == 0:
                    print(f"[LIVE STREAM] Streamed {frame_count} frames")
            
            # High FPS - 5 FPS for live stream
            time.sleep(0.2)
    
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/camera/snapshot/<cam_id>")
def snapshot(cam_id):
    """Get a snapshot from ESP32 camera"""
    frame = get_latest_frame()
    if frame is None:
        frame = create_placeholder()
    
    results = model(frame, verbose=False)
    annotated = results[0].plot()
    _, buffer = cv2.imencode(".jpg", annotated)
    return Response(buffer.tobytes(), mimetype="image/jpeg")

@app.route("/system/status")
def system_status():
    """System status endpoint"""
    return jsonify({
        "device": DEVICE,
        "gpu": GPU_NAME if DEVICE != "cpu" else None,
        "camera_connected": current_frame is not None and time.time() - last_frame_time < 5
    })

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("🚀 Starting Simplified FalconEye Backend...")
    print("📱 Dashboard: http://localhost:3000")
    print("📷 ESP32 Camera: http://192.168.225.6/jpg")
    
    # Start frame capture in background
    capture_thread = threading.Thread(target=capture_frames, daemon=True)
    capture_thread.start()
    
    # Wait a moment for first frame
    time.sleep(2)
    
    # Start Flask app
    app.run(host="0.0.0.0", port=3000, debug=False)
