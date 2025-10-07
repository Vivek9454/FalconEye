"""
FalconEye Local Notification Service
Simple HTTP-based notification system for local push notifications
"""

import requests
import json
import time
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class NotificationPayload:
    title: str
    body: str
    data: Optional[Dict] = None
    sound: str = "default"
    badge: Optional[int] = None

class LocalNotificationService:
    """Local notification service that sends HTTP requests to iOS app"""
    
    def __init__(self):
        self.registered_devices = set()
        self.stored_notifications = {}  # device_id -> list of notifications
        self.notification_url = "http://localhost:8080"  # Default iOS app URL
        
    def register_device(self, device_id: str, device_url: Optional[str] = None) -> bool:
        """Register a device for local notifications"""
        try:
            self.registered_devices.add(device_id)
            if device_url:
                self.notification_url = device_url
            logger.info(f"✅ Registered device: {device_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to register device: {e}")
            return False
    
    def unregister_device(self, device_id: str) -> bool:
        """Unregister a device"""
        try:
            self.registered_devices.discard(device_id)
            logger.info(f"✅ Unregistered device: {device_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to unregister device: {e}")
            return False
    
    def send_notification(self, payload: NotificationPayload, device_id: Optional[str] = None) -> bool:
        """Send local notification to device(s)"""
        if not self.registered_devices and not device_id:
            logger.warning("No registered devices available")
            return False
        
        devices_to_send = [device_id] if device_id else list(self.registered_devices)
        
        if not devices_to_send:
            logger.warning("No devices to send notification to")
            return False
        
        success_count = 0
        
        for device in devices_to_send:
            if self._send_to_device(device, payload):
                success_count += 1
        
        logger.info(f"📱 Sent notification to {success_count}/{len(devices_to_send)} devices")
        return success_count > 0
    
    def _send_to_device(self, device_id: str, payload: NotificationPayload) -> bool:
        """Send notification to a specific device via HTTP"""
        try:
            # For now, we'll use a simple approach where the iOS app polls for notifications
            # In a real implementation, you might use WebSockets or Server-Sent Events
            logger.info(f"📱 [LOCAL] Would send: {payload.title} - {payload.body}")
            logger.info(f"📱 [LOCAL] To device: {device_id}")
            
            # Store the notification for the iOS app to poll
            self._store_notification(device_id, payload)
            return True
                
        except Exception as e:
            logger.error(f"❌ Failed to send notification: {e}")
            return False
    
    def _store_notification(self, device_id: str, payload: NotificationPayload):
        """Store notification for device to poll"""
        current_time = time.time()
        
        # Check if we already have a similar notification in the last 30 seconds to prevent spam
        if device_id in self.stored_notifications:
            for existing_notif in self.stored_notifications[device_id]:
                if (existing_notif['title'] == payload.title and 
                    existing_notif['body'] == payload.body and 
                    current_time - existing_notif['timestamp'] < 30):  # 30 seconds
                    logger.info(f"📱 Skipping duplicate notification for {device_id}")
                    return
        
        notification_data = {
            "id": f"notif_{int(current_time * 1000)}",
            "device_id": device_id,
            "title": payload.title,
            "body": payload.body,
            "data": payload.data or {},
            "sound": payload.sound,
            "badge": payload.badge,
            "timestamp": current_time
        }
        
        # Store in memory
        if device_id not in self.stored_notifications:
            self.stored_notifications[device_id] = []
        self.stored_notifications[device_id].append(notification_data)
        
        # Keep only last 5 notifications per device to avoid memory issues and spam
        if len(self.stored_notifications[device_id]) > 5:
            self.stored_notifications[device_id] = self.stored_notifications[device_id][-5:]
        
        logger.info(f"📱 Stored notification for {device_id}: {notification_data}")
    
    def get_stored_notifications(self, device_id: str) -> List[dict]:
        """Get stored notifications for a device"""
        return self.stored_notifications.get(device_id, [])
    
    def clear_stored_notifications(self, device_id: str):
        """Clear stored notifications for a device after they've been delivered"""
        if device_id in self.stored_notifications:
            self.stored_notifications[device_id] = []
            logger.info(f"📱 Cleared stored notifications for device {device_id}")
    
    def send_security_alert(self, detected_objects: List[str], image_url: Optional[str] = None) -> bool:
        """Send security alert notification"""
        title = "🚨 Security Alert"
        body = f"Detected: {', '.join(detected_objects)}"
        
        payload = NotificationPayload(
            title=title,
            body=body,
            data={
                "type": "security_alert",
                "detected_objects": ",".join(detected_objects),
                "timestamp": str(int(time.time() * 1000))
            },
            sound="default",
            badge=1
        )
        
        return self.send_notification(payload)
    
    def send_test_notification(self) -> bool:
        """Send test notification"""
        payload = NotificationPayload(
            title="🧪 FalconEye Test",
            body="This is a test notification from your security system",
            data={"type": "test"},
            sound="default"
        )
        
        return self.send_notification(payload)
    
    def get_status(self) -> Dict:
        """Get notification service status"""
        return {
            "service": "local_http",
            "registered_devices": len(self.registered_devices),
            "last_notification": "N/A"
        }

# Global notification service instance
notification_service = LocalNotificationService()

# Convenience functions for backward compatibility
def register_device_token(token: str) -> bool:
    """Register device token (backward compatibility)"""
    return notification_service.register_device(token)

def unregister_device_token(token: str) -> bool:
    """Unregister device token (backward compatibility)"""
    return notification_service.unregister_device(token)

def send_push_notification(title: str, body: str, token: Optional[str] = None, detected_objects: Optional[List[str]] = None) -> bool:
    """Send push notification (backward compatibility)"""
    data = {}
    if detected_objects:
        data["detected_objects"] = ",".join(detected_objects)
        data["type"] = "security_alert"
    
    payload = NotificationPayload(
        title=title,
        body=body,
        data=data,
        sound="default"
    )
    
    return notification_service.send_notification(payload, token)

def send_security_alert(detected_objects: List[str], image_url: Optional[str] = None) -> bool:
    """Send security alert (backward compatibility)"""
    return notification_service.send_security_alert(detected_objects, image_url)

def send_test_notification() -> bool:
    """Send test notification (backward compatibility)"""
    return notification_service.send_test_notification()

def get_notification_status() -> Dict:
    """Get notification status (backward compatibility)"""
    return notification_service.get_status()
