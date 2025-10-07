#!/usr/bin/env python3
"""
Camera Switcher for FalconEye
Switch between ESP32 camera and test camera
"""

import sys
import os

def switch_to_test_camera():
    """Switch backend to use test camera"""
    backend_file = "backend.py"
    
    # Read the current backend file
    with open(backend_file, 'r') as f:
        content = f.read()
    
    # Update camera URL to test camera
    content = content.replace(
        '"cam1": "http://192.168.225.6/jpg",  # Your actual camera URL',
        '"cam1": "http://localhost:8081/jpg",  # Test camera URL'
    )
    
    # Write back to file
    with open(backend_file, 'w') as f:
        f.write(content)
    
    print("✅ Switched to Test Camera")
    print("📱 Test Camera URL: http://localhost:8081")
    print("🖼️  JPEG Endpoint: http://localhost:8081/jpg")

def switch_to_esp32_camera():
    """Switch backend to use ESP32 camera"""
    backend_file = "backend.py"
    
    # Read the current backend file
    with open(backend_file, 'r') as f:
        content = f.read()
    
    # Update camera URL to ESP32
    content = content.replace(
        '"cam1": "http://localhost:8081/jpg",  # Test camera URL',
        '"cam1": "http://192.168.225.6/jpg",  # Your actual camera URL'
    )
    
    # Write back to file
    with open(backend_file, 'w') as f:
        f.write(content)
    
    print("✅ Switched to ESP32 Camera")
    print("📱 ESP32 Camera URL: http://192.168.225.6")
    print("🖼️  JPEG Endpoint: http://192.168.225.6/jpg")

def show_status():
    """Show current camera configuration"""
    backend_file = "backend.py"
    
    with open(backend_file, 'r') as f:
        content = f.read()
    
    if "localhost:8081" in content:
        print("📷 Current Camera: Test Camera")
        print("🖼️  URL: http://localhost:8081/jpg")
    elif "192.168.225.6" in content:
        print("📷 Current Camera: ESP32 Camera")
        print("🖼️  URL: http://192.168.225.6/jpg")
    else:
        print("❓ Unknown camera configuration")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("FalconEye Camera Switcher")
        print("Usage:")
        print("  python switch_camera.py test     - Switch to test camera")
        print("  python switch_camera.py esp32    - Switch to ESP32 camera")
        print("  python switch_camera.py status   - Show current camera")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "test":
        switch_to_test_camera()
    elif command == "esp32":
        switch_to_esp32_camera()
    elif command == "status":
        show_status()
    else:
        print(f"Unknown command: {command}")
        print("Use 'test', 'esp32', or 'status'")
        sys.exit(1)





























