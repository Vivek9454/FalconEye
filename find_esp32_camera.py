#!/usr/bin/env python3
"""
Auto-discover ESP32 camera on the network
Scans common IP ranges and tests for ESP32 camera endpoints
"""

import requests
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import subprocess
import os

def test_camera_url(ip, port=80):
    """Test if an IP has an ESP32 camera"""
    url = f"http://{ip}:{port}/jpg"
    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
            return True, url
    except:
        pass
    return False, None

def scan_network_range(network_base, start=1, end=254):
    """Scan a network range for ESP32 cameras"""
    print(f"🔍 Scanning {network_base}.{start}-{end} for ESP32 cameras...")
    
    found_cameras = []
    
    def check_ip(ip):
        success, url = test_camera_url(ip)
        if success:
            found_cameras.append((ip, url))
            print(f"✅ Found ESP32 camera at: {url}")
    
    # Use thread pool for parallel scanning
    with ThreadPoolExecutor(max_workers=50) as executor:
        for i in range(start, end + 1):
            ip = f"{network_base}.{i}"
            executor.submit(check_ip, ip)
    
    return found_cameras

def get_network_base():
    """Get the current network base (e.g., 192.168.1)"""
    try:
        # Get default gateway to determine network
        result = subprocess.run(['route', '-n', 'get', 'default'], 
                              capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'gateway' in line.lower():
                gateway = line.split(':')[-1].strip()
                # Extract network base (first 3 octets)
                parts = gateway.split('.')
                if len(parts) >= 3:
                    return '.'.join(parts[:3])
    except:
        pass
    
    # Fallback to common ranges
    return "192.168.1"

def update_backend_with_camera(camera_url):
    """Update backend.py with the found camera URL"""
    backend_file = "backend.py"
    
    if not os.path.exists(backend_file):
        print(f"❌ {backend_file} not found!")
        return False
    
    # Read the file
    with open(backend_file, 'r') as f:
        content = f.read()
    
    # Update the camera URL
    import re
    old_pattern = r'"cam1": "http://[^"]+/jpg"'
    new_url = f'"cam1": "{camera_url}"'
    
    if re.search(old_pattern, content):
        new_content = re.sub(old_pattern, new_url, content)
        
        # Write back to file
        with open(backend_file, 'w') as f:
            f.write(new_content)
        
        print(f"✅ Updated backend.py with camera URL: {camera_url}")
        return True
    else:
        print("❌ Could not find camera URL pattern to update")
        return False

def main():
    print("🚀 ESP32 Camera Auto-Discovery")
    print("=" * 40)
    
    # Get network base
    network_base = get_network_base()
    print(f"🌐 Scanning network: {network_base}.x")
    
    # Scan for cameras
    cameras = scan_network_range(network_base)
    
    if not cameras:
        print("❌ No ESP32 cameras found!")
        print("\n💡 Try these common ranges manually:")
        print("   • 192.168.1.x")
        print("   • 192.168.0.x") 
        print("   • 192.168.31.x")
        print("   • 10.0.0.x")
        return
    
    print(f"\n🎉 Found {len(cameras)} ESP32 camera(s):")
    for i, (ip, url) in enumerate(cameras, 1):
        print(f"   {i}. {url}")
    
    if len(cameras) == 1:
        # Auto-update if only one camera found
        camera_url = cameras[0][1]
        print(f"\n🔄 Auto-updating backend with: {camera_url}")
        if update_backend_with_camera(camera_url):
            print("\n🔄 Do you want to restart the backend? (y/n): ", end="")
            if input().lower().startswith('y'):
                print("🔄 Restarting backend...")
                subprocess.run(["pkill", "-f", "python backend.py"], capture_output=True)
                time.sleep(2)
                subprocess.Popen(["python", "backend.py"], cwd=os.getcwd())
                print("✅ Backend restarted!")
    else:
        # Let user choose if multiple cameras found
        print(f"\n📝 Which camera would you like to use? (1-{len(cameras)}): ", end="")
        try:
            choice = int(input()) - 1
            if 0 <= choice < len(cameras):
                camera_url = cameras[choice][1]
                print(f"🔄 Updating backend with: {camera_url}")
                if update_backend_with_camera(camera_url):
                    print("\n🔄 Do you want to restart the backend? (y/n): ", end="")
                    if input().lower().startswith('y'):
                        print("🔄 Restarting backend...")
                        subprocess.run(["pkill", "-f", "python backend.py"], capture_output=True)
                        time.sleep(2)
                        subprocess.Popen(["python", "backend.py"], cwd=os.getcwd())
                        print("✅ Backend restarted!")
            else:
                print("❌ Invalid choice!")
        except ValueError:
            print("❌ Invalid input!")

if __name__ == "__main__":
    main()
