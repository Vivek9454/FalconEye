import Foundation
import UserNotifications
import SwiftUI

class SimpleNotificationManager: NSObject, ObservableObject {
    @Published var isAuthorized = false
    @Published var isRegistered = false
    
    private let apiService = APIService.shared
    
    override init() {
        super.init()
        print("🚀 SimpleNotificationManager init() called")
        checkAuthorizationStatus()
        
        // Auto-request permissions if not already granted
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            if !self.isAuthorized {
                print("🔔 Auto-requesting notification permissions...")
                self.requestPermission()
            }
        }
    }
    
    private func checkAuthorizationStatus() {
        UNUserNotificationCenter.current().getNotificationSettings { [weak self] settings in
            DispatchQueue.main.async {
                self?.isAuthorized = settings.authorizationStatus == .authorized
                print("📱 Notification status: \(settings.authorizationStatus.rawValue) (authorized: \(self?.isAuthorized ?? false))")
                
                if settings.authorizationStatus == .authorized {
                    self?.registerForRemoteNotifications()
                }
            }
        }
    }
    
    func requestPermission() {
        print("🔔 Requesting notification permissions...")
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { [weak self] granted, error in
            DispatchQueue.main.async {
                self?.isAuthorized = granted
                if granted {
                    print("✅ Notification permission granted!")
                    self?.registerForRemoteNotifications()
                } else if let error = error {
                    print("❌ Notification permission denied with error: \(error.localizedDescription)")
                } else {
                    print("❌ Notification permission denied by user")
                }
            }
        }
    }
    
    private func registerForRemoteNotifications() {
        DispatchQueue.main.async {
            print("📱 Registering for remote notifications...")
            print("📱 Current APNs registration status: \(UIApplication.shared.isRegisteredForRemoteNotifications)")
            
            // Try to register for real APNs
            print("📱 Attempting real APNs registration...")
            UIApplication.shared.registerForRemoteNotifications()
            print("📱 APNs registration request sent to system")
        }
    }
    
    private func registerWithBackend(token: String) async {
        do {
            let response = try await apiService.registerDeviceToken(token: token)
            print("✅ Device token registered with backend: \(response.status)")
        } catch {
            print("❌ Failed to register device token with backend: \(error)")
        }
    }
    
    func sendTestNotification() {
        sendLocalNotification(
            title: "FalconEye Test",
            body: "This is a test notification from your security system"
        )
    }
    
    private func sendLocalNotification(title: String, body: String) {
        print("🔔 Creating local notification: \(title) - \(body)")
        
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default
        content.badge = 1
        
        let request = UNNotificationRequest(
            identifier: "test-notification-\(UUID().uuidString)",
            content: content,
            trigger: nil
        )
        
        print("🔔 Adding notification request to center...")
        UNUserNotificationCenter.current().add(request) { error in
            DispatchQueue.main.async {
                if let error = error {
                    print("❌ Failed to send local notification: \(error)")
                } else {
                    print("✅ Local notification sent successfully")
                    print("🔔 Notification should appear on your device now!")
                }
            }
        }
    }
    
    // MARK: - Debug Functions
    func debugStatus() {
        print("🔍 DEBUG: Simple Notification Status:")
        print("  - isAuthorized: \(isAuthorized)")
        print("  - isRegistered: \(isRegistered)")
        print("  - APNs registration: \(UIApplication.shared.isRegisteredForRemoteNotifications)")
    }
    
    func testBackendNotification() {
        print("🧪 Testing backend notification...")
        Task {
            do {
                let response = try await apiService.testBackendNotification()
                print("✅ Backend notification test: \(response.status)")
            } catch {
                print("❌ Backend notification test failed: \(error)")
            }
        }
    }
    
    func checkNotificationSettings() {
        print("🔍 Checking notification settings...")
        UNUserNotificationCenter.current().getNotificationSettings { settings in
            DispatchQueue.main.async {
                print("📱 Notification Settings:")
                print("  - Authorization Status: \(settings.authorizationStatus.rawValue)")
                print("  - Alert Setting: \(settings.alertSetting.rawValue)")
                print("  - Badge Setting: \(settings.badgeSetting.rawValue)")
                print("  - Sound Setting: \(settings.soundSetting.rawValue)")
                print("  - Lock Screen Setting: \(settings.lockScreenSetting.rawValue)")
                print("  - Notification Center Setting: \(settings.notificationCenterSetting.rawValue)")
                
                if settings.authorizationStatus != .authorized {
                    print("⚠️ Notifications not authorized! Requesting permission...")
                    self.requestPermission()
                } else {
                    print("✅ Notifications are authorized")
                }
            }
        }
    }
    
    func forceRegistration() {
        print("🔧 FORCE: Attempting manual registration...")
        print("🔧 Current authorization status: \(isAuthorized)")
        print("🔧 Current registration status: \(isRegistered)")
        print("🔧 UIApplication.shared.isRegisteredForRemoteNotifications: \(UIApplication.shared.isRegisteredForRemoteNotifications)")
        
        if !isAuthorized {
            print("🔧 Requesting permission first...")
            requestPermission()
        } else {
            print("🔧 Permission already granted, registering...")
            registerForRemoteNotifications()
        }
    }
}

// MARK: - UNUserNotificationCenterDelegate
extension SimpleNotificationManager: UNUserNotificationCenterDelegate {
    func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification, withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        // Show notification even when app is in foreground
        completionHandler([.alert, .badge, .sound])
    }
    
    func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse, withCompletionHandler completionHandler: @escaping () -> Void) {
        // Handle notification tap
        print("📱 User tapped notification: \(response.notification.request.identifier)")
        completionHandler()
    }
}
