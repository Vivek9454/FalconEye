import SwiftUI
import UserNotifications

class AppDelegate: NSObject, UIApplicationDelegate {
    var notificationManager: LocalNotificationManager?
    
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey : Any]? = nil) -> Bool {
        print("🚀 FalconEye app launched")
        return true
    }
    
    func applicationDidEnterBackground(_ application: UIApplication) {
        print("📱 App entered background - scheduling background tasks")
        // The notification manager will handle background task scheduling
    }
    
    func applicationWillEnterForeground(_ application: UIApplication) {
        print("📱 App entering foreground - checking for notifications")
        // Check for notifications immediately when app comes to foreground
        Task {
            await notificationManager?.checkForNotifications()
        }
    }
    
    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        print("✅ APNS registration successful")
        let tokenString = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
        print("📱 APNS Token: \(tokenString)")
        
        // Update notification manager status
        DispatchQueue.main.async {
            self.notificationManager?.isRegistered = true
        }
    }
    
    func application(_ application: UIApplication, didFailToRegisterForRemoteNotificationsWithError error: Error) {
        print("❌ APNS registration failed: \(error)")
        print("📱 Local notifications will still work")
        
        // Update notification manager to indicate we're using local notifications only
        DispatchQueue.main.async {
            self.notificationManager?.isRegistered = true // For local notifications
        }
    }
}

@main
struct FalconEyeApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var delegate
    @StateObject private var authManager = AuthenticationManager()
    @StateObject private var apiService = APIService.shared
    @StateObject private var cameraManager = CameraManager()
    @StateObject private var notificationManager = LocalNotificationManager()
    @StateObject private var themeManager = ThemeManager()
    @StateObject private var appIconManager = AppIconManager.shared
    @StateObject private var networkManager = NetworkManager.shared
    
    init() {
        // Set up notification delegate
        UNUserNotificationCenter.current().delegate = notificationManager
    }
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(authManager)
                .environmentObject(apiService)
                .environmentObject(cameraManager)
                .environmentObject(notificationManager)
                .environmentObject(themeManager)
                .environmentObject(appIconManager)
                .environmentObject(networkManager)
                .preferredColorScheme(themeManager.colorScheme)
                .onAppear {
                    // Connect AppDelegate to NotificationManager
                    delegate.notificationManager = notificationManager
                    // Request permissions on app launch
                    notificationManager.requestPermissions()
                }
        }
    }
}