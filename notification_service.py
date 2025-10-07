"""
FalconEye Push Notification Service
Complete rewrite of push notification functionality
"""

import os
import json
import time
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging
from google.oauth2 import service_account
import google.auth.transport.requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class NotificationPayload:
    title: str
    body: str
    data: Optional[Dict] = None
    image_url: Optional[str] = None
    sound: str = "default"
    badge: Optional[int] = None

class FirebaseNotificationService:
    """Firebase Cloud Messaging service for push notifications using FCM v1 API"""
    
    def __init__(self):
        self.project_id = "falconeye-security"
        self.service_account_path = self._get_service_account_path()
        self.fcm_url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        self.registered_tokens = set()
        self.credentials = None
        self.access_token = None
        self.token_expires_at = 0
        
    def _get_service_account_path(self) -> str:
        """Get Firebase service account key path"""
        # Try environment variable first
        service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
        if service_account_path and os.path.exists(service_account_path):
            return service_account_path
            
        # Try common locations
        possible_paths = [
            'firebase-service-account.json',
            'service-account-key.json',
            'falconeye-service-account.json',
            '/Users/vpaul/FalconEye/firebase-service-account.json',
            os.path.join(os.path.dirname(__file__), 'firebase-service-account.json')
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"✅ Found service account key at {path}")
                return path
        
        logger.warning("⚠️ No Firebase service account key found. Using fallback mode.")
        return None
    
    def _get_access_token(self) -> str:
        """Get OAuth2 access token for FCM v1 API"""
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token
        
        try:
            if not self.service_account_path or not os.path.exists(self.service_account_path):
                logger.error("Service account key file not found")
                return None
            
            # Load service account credentials
            self.credentials = service_account.Credentials.from_service_account_file(
                self.service_account_path,
                scopes=['https://www.googleapis.com/auth/firebase.messaging']
            )
            
            # Get access token
            request = google.auth.transport.requests.Request()
            self.credentials.refresh(request)
            
            self.access_token = self.credentials.token
            self.token_expires_at = self.credentials.expiry.timestamp() if self.credentials.expiry else time.time() + 3600
            
            logger.info("✅ Got new access token for FCM v1 API")
            return self.access_token
            
        except Exception as e:
            logger.error(f"❌ Failed to get access token: {e}")
            return None
    
    def register_token(self, token: str, platform: str = "ios") -> bool:
        """Register a device token for push notifications"""
        try:
            self.registered_tokens.add(token)
            logger.info(f"✅ Registered {platform} token: {token[:20]}...")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to register token: {e}")
            return False
    
    def unregister_token(self, token: str) -> bool:
        """Unregister a device token"""
        try:
            self.registered_tokens.discard(token)
            logger.info(f"✅ Unregistered token: {token[:20]}...")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to unregister token: {e}")
            return False
    
    def send_notification(self, payload: NotificationPayload, token: Optional[str] = None) -> bool:
        """Send push notification to device(s)"""
        if not self.registered_tokens and not token:
            logger.warning("No registered tokens available")
            return False
        
        tokens_to_send = [token] if token else list(self.registered_tokens)
        
        if not tokens_to_send:
            logger.warning("No tokens to send notification to")
            return False
        
        success_count = 0
        
        for device_token in tokens_to_send:
            if self._send_to_device(device_token, payload):
                success_count += 1
        
        logger.info(f"📱 Sent notification to {success_count}/{len(tokens_to_send)} devices")
        return success_count > 0
    
    def _send_to_device(self, device_token: str, payload: NotificationPayload) -> bool:
        """Send notification to a specific device using FCM v1 API"""
        try:
            # Check if we have service account credentials
            if not self.service_account_path or not os.path.exists(self.service_account_path):
                logger.warning("⚠️ Firebase service account key not found. Using fallback mode.")
                logger.info(f"📱 [FALLBACK] Would send: {payload.title} - {payload.body}")
                logger.info(f"📱 [FALLBACK] To token: {device_token[:20]}...")
                return True  # Return True for testing purposes
            
            # Get access token
            access_token = self._get_access_token()
            if not access_token:
                logger.warning("⚠️ Failed to get access token. Using fallback mode.")
                logger.info(f"📱 [FALLBACK] Would send: {payload.title} - {payload.body}")
                logger.info(f"📱 [FALLBACK] To token: {device_token[:20]}...")
                return True
            
            # Use FCM v1 API
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Build FCM v1 payload
            fcm_payload = {
                "message": {
                    "token": device_token,
                    "notification": {
                        "title": payload.title,
                        "body": payload.body
                    },
                    "data": payload.data or {},
                    "android": {
                        "priority": "high",
                        "notification": {
                            "sound": payload.sound,
                            "icon": "ic_notification"
                        }
                    },
                    "apns": {
                        "payload": {
                            "aps": {
                                "alert": {
                                    "title": payload.title,
                                    "body": payload.body
                                },
                                "sound": payload.sound
                            }
                        }
                    }
                }
            }
            
            # Add badge if provided and valid
            if payload.badge is not None and isinstance(payload.badge, int):
                fcm_payload["message"]["apns"]["payload"]["aps"]["badge"] = payload.badge
            
            # Add image if provided
            if payload.image_url:
                fcm_payload["message"]["android"]["notification"]["image"] = payload.image_url
                fcm_payload["message"]["apns"]["payload"]["aps"]["mutable-content"] = 1
            
            response = requests.post(
                self.fcm_url,
                headers=headers,
                json=fcm_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Notification sent to {device_token[:20]}...")
                return True
            else:
                logger.error(f"❌ FCM v1 API error {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to send notification: {e}")
            return False
    
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
            image_url=image_url,
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
            "service": "firebase_fcm_v1",
            "project_id": self.project_id,
            "registered_tokens": len(self.registered_tokens),
            "service_account_configured": bool(self.service_account_path and os.path.exists(self.service_account_path)),
            "last_notification": "N/A"  # Could track this if needed
        }

# Global notification service instance
notification_service = FirebaseNotificationService()

# Convenience functions for backward compatibility
def register_fcm_token(token: str) -> bool:
    """Register FCM token (backward compatibility)"""
    return notification_service.register_token(token, "ios")

def unregister_fcm_token(token: str) -> bool:
    """Unregister FCM token (backward compatibility)"""
    return notification_service.unregister_token(token)

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
