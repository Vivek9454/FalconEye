import Foundation
import UserNotifications
import SwiftUI
import BackgroundTasks

@MainActor
class LocalNotificationManager: NSObject, ObservableObject {
    @Published var isAuthorized = false
    @Published var isRegistered = false
    @Published var registrationStatus = "Not started"
    @Published var lastNotification: String = "None"
    
    private let apiService = APIService.shared
    private var pollingTimer: Timer?
    private let backgroundTaskIdentifier = "com.falconeye.notification-check"
    
    override init() {
        super.init()
        print("🚀 LocalNotificationManager init() called")
        setupNotificationCenter()
        setupBackgroundTasks()
        checkAuthorizationStatus()
    }
    
    private func setupNotificationCenter() {
        // Set the notification center delegate
        UNUserNotificationCenter.current().delegate = self
        print("✅ Notification center delegate set")
    }
    
    private func setupBackgroundTasks() {
        // Register background task
        BGTaskScheduler.shared.register(forTaskWithIdentifier: backgroundTaskIdentifier, using: nil) { task in
            self.handleBackgroundTask(task: task as! BGAppRefreshTask)
        }
        print("✅ Background task registered: \(backgroundTaskIdentifier)")
    }
    
    private func handleBackgroundTask(task: BGAppRefreshTask) {
        print("🔄 Background task started")
        
        // Schedule the next background task
        scheduleBackgroundTask()
        
        // Perform the notification check
        Task {
            await checkForNotifications()
            task.setTaskCompleted(success: true)
        }
    }
    
    private func scheduleBackgroundTask() {
        let request = BGAppRefreshTaskRequest(identifier: backgroundTaskIdentifier)
        request.earliestBeginDate = Date(timeIntervalSinceNow: 15 * 60) // 15 minutes
        
        do {
            try BGTaskScheduler.shared.submit(request)
            print("✅ Background task scheduled for 15 minutes")
        } catch {
            print("❌ Failed to schedule background task: \(error)")
        }
    }
    
    func requestPermissions() {
        print("🔔 Requesting notification permissions...")
        registrationStatus = "Requesting permissions..."
        
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { [weak self] granted, error in
            Task { @MainActor in
                self?.isAuthorized = granted
                
                if granted {
                    print("✅ Notification permission granted!")
                    self?.registrationStatus = "Permission granted"
                    await self?.registerForRemoteNotifications()
                } else if let error = error {
                    print("❌ Notification permission denied with error: \(error.localizedDescription)")
                    self?.registrationStatus = "Permission denied: \(error.localizedDescription)"
                } else {
                    print("❌ Notification permission denied by user")
                    self?.registrationStatus = "Permission denied by user"
                }
            }
        }
    }
    
    private func checkAuthorizationStatus() {
        UNUserNotificationCenter.current().getNotificationSettings { [weak self] settings in
            Task { @MainActor in
                self?.isAuthorized = settings.authorizationStatus == .authorized
                print("📱 Notification status: \(settings.authorizationStatus.rawValue) (authorized: \(self?.isAuthorized ?? false))")
                
                if settings.authorizationStatus == .authorized {
                    self?.registrationStatus = "Already authorized"
                    await self?.registerForRemoteNotifications()
                } else {
                    self?.registrationStatus = "Not authorized"
                }
            }
        }
    }
    
    private func registerForRemoteNotifications() async {
        print("📱 Registering for remote notifications...")
        registrationStatus = "Registering for remote notifications..."
        
        await UIApplication.shared.registerForRemoteNotifications()
        
        // Generate a simple device ID for local notifications
        let deviceId = UIDevice.current.identifierForVendor?.uuidString ?? UUID().uuidString
        await registerDeviceWithBackend(deviceId: deviceId)
    }
    
    private func registerDeviceWithBackend(deviceId: String) async {
        print("🔄 Registering device with backend: \(deviceId)")
        registrationStatus = "Registering with backend..."
        
        do {
            let response = try await apiService.registerFCMToken(token: deviceId)
            print("✅ Device registered successfully: \(response.status)")
            
            self.isRegistered = true
            self.registrationStatus = "Successfully registered"
            
            // Start polling for notifications
            print("🔄 Starting notification polling after successful registration...")
            startPollingForNotifications()
            
            // Schedule background task
            scheduleBackgroundTask()
        } catch {
            print("❌ Failed to register device: \(error)")
            self.isRegistered = false
            self.registrationStatus = "Backend registration failed: \(error.localizedDescription)"
        }
    }
    
    private func startPollingForNotifications() {
        print("🔄 Starting polling for notifications...")
        
        // Stop any existing timer
        pollingTimer?.invalidate()
        
        // Start new timer
        pollingTimer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { [weak self] _ in
            Task { @MainActor in
                print("🔄 Polling for notifications...")
                await self?.checkForNotifications()
            }
        }
        
        // Also check immediately
        Task { @MainActor in
            print("🔄 Checking for notifications immediately...")
            await checkForNotifications()
        }
    }
    
    func checkForNotifications() async {
        // Check with the backend for new notifications
        guard let deviceId = UIDevice.current.identifierForVendor?.uuidString else {
            print("❌ No device ID available for notification polling")
            return
        }
        
        print("📱 Checking for notifications with device ID: \(deviceId)")
        
        do {
            let notifications = try await apiService.getNotifications(deviceId: deviceId)
            print("📱 Polling notifications: \(notifications.count) pending")
            
            if notifications.count > 0 {
                print("📱 Found \(notifications.count) notifications to display")
            }
            
            for notification in notifications {
                print("📱 Sending notification: \(notification.title)")
                // Send local notification for each pending notification
                await sendLocalNotification(
                    title: notification.title,
                    body: notification.body,
                    data: notification.data
                )
            }
        } catch {
            print("❌ Failed to check for notifications: \(error)")
        }
    }
    
    func unregisterDevice() async {
        guard let deviceId = UIDevice.current.identifierForVendor?.uuidString else {
            print("❌ No device ID available")
            return
        }
        
        print("🔄 Unregistering device...")
        registrationStatus = "Unregistering..."
        
        // Stop polling
        pollingTimer?.invalidate()
        pollingTimer = nil
        
        do {
            let response = try await apiService.unregisterFCMToken(token: deviceId)
            print("✅ Device unregistered: \(response.status)")
            
            self.isRegistered = false
            self.registrationStatus = "Unregistered"
        } catch {
            print("❌ Failed to unregister device: \(error)")
            self.registrationStatus = "Unregister failed: \(error.localizedDescription)"
        }
    }
    
    func sendTestNotification() {
        print("🧪 Sending test notification...")
        registrationStatus = "Sending test..."
        
        // Send local notification
        sendLocalTestNotification()
        registrationStatus = "Local test sent successfully"
        
        // Also try backend if we have a device ID
        if let deviceId = UIDevice.current.identifierForVendor?.uuidString {
            Task {
                do {
                    let response = try await apiService.testPushNotification()
                    print("✅ Backend test notification sent: \(response.status)")
                    registrationStatus = "Local + Backend test sent"
                } catch {
                    print("❌ Backend test notification failed: \(error)")
                    registrationStatus = "Local sent, Backend failed"
                }
            }
        } else {
            print("ℹ️ No device ID available, using local notification only")
        }
    }
    
    func sendLocalTestNotification() {
        print("🔔 Sending local test notification...")
        
        let content = UNMutableNotificationContent()
        content.title = "FalconEye Test"
        content.body = "This is a local test notification"
        content.sound = .default
        content.badge = 1
        
        let request = UNNotificationRequest(
            identifier: "test-\(UUID().uuidString)",
            content: content,
            trigger: nil
        )
        
        UNUserNotificationCenter.current().add(request) { error in
            if let error = error {
                print("❌ Local notification error: \(error)")
            } else {
                print("✅ Local notification sent")
            }
        }
    }
    
    func sendLocalSecurityAlert(detectedObjects: [String]) {
        print("🚨 Sending local security alert...")
        
        let content = UNMutableNotificationContent()
        content.title = "🚨 Security Alert"
        content.body = "Detected: \(detectedObjects.joined(separator: ", "))"
        content.sound = .default
        content.badge = 1
        
        // Add custom data
        content.userInfo = [
            "type": "security_alert",
            "objects": detectedObjects,
            "timestamp": Date().timeIntervalSince1970
        ]
        
        let request = UNNotificationRequest(
            identifier: "security-\(UUID().uuidString)",
            content: content,
            trigger: nil
        )
        
        UNUserNotificationCenter.current().add(request) { [weak self] error in
            if let error = error {
                print("❌ Security alert notification error: \(error)")
            } else {
                print("✅ Security alert notification sent")
                Task { @MainActor in
                    self?.lastNotification = "Security Alert: \(detectedObjects.joined(separator: ", "))"
                }
            }
        }
    }
    
    private func sendLocalNotification(title: String, body: String, data: [String: String]? = nil) async {
        print("📱 Sending local notification: \(title)")
        
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default
        content.badge = 1
        
        // Add custom data if provided
        if let data = data {
            content.userInfo = data
        }
        
        let request = UNNotificationRequest(
            identifier: "notification-\(UUID().uuidString)",
            content: content,
            trigger: nil
        )
        
        do {
            try await UNUserNotificationCenter.current().add(request)
            print("✅ Local notification sent: \(title)")
            await MainActor.run {
                self.lastNotification = "\(title): \(body)"
            }
        } catch {
            print("❌ Failed to send local notification: \(error)")
        }
    }
    
    func getDebugInfo() -> String {
        return """
        🔍 Local Notification Debug Info:
        - isAuthorized: \(isAuthorized)
        - isRegistered: \(isRegistered)
        - registrationStatus: \(registrationStatus)
        - lastNotification: \(lastNotification)
        - pollingActive: \(pollingTimer != nil)
        """
    }
    
    func startPollingManually() {
        print("🔄 Manually starting notification polling...")
        startPollingForNotifications()
    }
}

// MARK: - UNUserNotificationCenterDelegate
extension LocalNotificationManager: UNUserNotificationCenterDelegate {
    func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification, withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        // Show notification even when app is in foreground
        print("📱 Will present notification: \(notification.request.content.title)")
        completionHandler([.alert, .badge, .sound])
    }
    
    func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse, withCompletionHandler completionHandler: @escaping () -> Void) {
        // Handle notification tap
        print("📱 User tapped notification: \(response.notification.request.identifier)")
        completionHandler()
    }
}
