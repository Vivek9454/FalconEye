#!/usr/bin/env python3
"""
FalconEye Test Runner
Runs test camera and backend for testing object detection
"""

import subprocess
import time
import signal
import sys
import os
import threading

def run_test_camera():
    """Run the test camera in background"""
    print("🎥 Starting Test Camera...")
    return subprocess.Popen([sys.executable, "test_camera.py"])

def run_backend():
    """Run the FalconEye backend"""
    print("🚀 Starting FalconEye Backend...")
    return subprocess.Popen([sys.executable, "backend.py"])

def main():
    print("=" * 60)
    print("🎯 FalconEye Object Detection Test")
    print("=" * 60)
    
    # Switch to test camera
    print("📷 Switching to Test Camera...")
    subprocess.run([sys.executable, "switch_camera.py", "test"])
    
    # Start test camera
    test_camera_proc = run_test_camera()
    time.sleep(2)  # Wait for test camera to start
    
    # Start backend
    backend_proc = run_backend()
    
    print("\n" + "=" * 60)
    print("✅ Test Environment Ready!")
    print("=" * 60)
    print("🌐 FalconEye Dashboard: http://localhost:3000")
    print("🎥 Test Camera: http://localhost:8081")
    print("📱 Test Camera JPEG: http://localhost:8081/jpg")
    print("\n🎯 Test Features:")
    print("  • Simulated objects (people, cars, animals, etc.)")
    print("  • Random movement and appearance")
    print("  • Real-time object detection")
    print("  • Video recording when objects detected")
    print("  • Push notifications")
    print("\nPress Ctrl+C to stop all services")
    print("=" * 60)
    
    try:
        # Wait for processes
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if test_camera_proc.poll() is not None:
                print("❌ Test camera stopped unexpectedly")
                break
            if backend_proc.poll() is not None:
                print("❌ Backend stopped unexpectedly")
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Stopping test environment...")
        
        # Terminate processes
        test_camera_proc.terminate()
        backend_proc.terminate()
        
        # Wait for graceful shutdown
        test_camera_proc.wait(timeout=5)
        backend_proc.wait(timeout=5)
        
        print("✅ Test environment stopped")

if __name__ == "__main__":
    main()





























