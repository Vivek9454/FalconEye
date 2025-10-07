#!/usr/bin/env python3
"""
Quick script to update ESP32 camera IP address in backend.py
Usage: python update_camera_ip.py <new_ip>
Example: python update_camera_ip.py 192.168.31.99
"""

import sys
import re
import subprocess
import os

def update_camera_ip(new_ip):
    """Update the camera IP in backend.py"""
    backend_file = "backend.py"
    
    if not os.path.exists(backend_file):
        print(f"❌ {backend_file} not found!")
        return False
    
    # Read the file
    with open(backend_file, 'r') as f:
        content = f.read()
    
    # Update the camera URL
    old_pattern = r'"cam1": "http://[^"]+/jpg"'
    new_url = f'"cam1": "http://{new_ip}/jpg"'
    
    if re.search(old_pattern, content):
        new_content = re.sub(old_pattern, new_url, content)
        
        # Write back to file
        with open(backend_file, 'w') as f:
            f.write(new_content)
        
        print(f"✅ Updated camera IP to: {new_ip}")
        print(f"📝 New URL: http://{new_ip}/jpg")
        return True
    else:
        print("❌ Could not find camera URL pattern to update")
        return False

def restart_backend():
    """Restart the backend service"""
    print("🔄 Restarting backend...")
    
    # Kill existing backend processes
    subprocess.run(["pkill", "-f", "python backend.py"], capture_output=True)
    
    # Wait a moment
    import time
    time.sleep(2)
    
    # Start new backend
    subprocess.Popen(["python", "backend.py"], cwd=os.getcwd())
    print("✅ Backend restarted!")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_camera_ip.py <new_ip>")
        print("Example: python update_camera_ip.py 192.168.31.99")
        sys.exit(1)
    
    new_ip = sys.argv[1]
    
    # Validate IP format (basic check)
    ip_parts = new_ip.split('.')
    if len(ip_parts) != 4 or not all(part.isdigit() and 0 <= int(part) <= 255 for part in ip_parts):
        print("❌ Invalid IP address format!")
        sys.exit(1)
    
    if update_camera_ip(new_ip):
        print("\n🔄 Do you want to restart the backend? (y/n): ", end="")
        if input().lower().startswith('y'):
            restart_backend()
        else:
            print("ℹ️  Remember to restart the backend manually!")
    else:
        sys.exit(1)
