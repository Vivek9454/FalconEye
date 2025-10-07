import UIKit
import SwiftUI

class AppIconManager: ObservableObject {
    static let shared = AppIconManager()
    
    @Published var currentIcon: AppIcon = .primary
    
    enum AppIcon: String, CaseIterable, Identifiable {
        case primary = "AppIcon"
        case light = "LightIcon"
        case dark = "DarkIcon"
        
        var id: String { self.rawValue }
        
        var displayName: String {
            switch self {
            case .primary: return "System Default"
            case .light: return "Light Theme"
            case .dark: return "Dark Theme"
            }
        }
        
        var iconName: String? {
            switch self {
            case .primary: return nil
            case .light: return "LightIcon"
            case .dark: return "DarkIcon"
            }
        }
    }
    
    private init() {
        // Load saved icon preference
        if let savedIcon = UserDefaults.standard.string(forKey: "selectedAppIcon"),
           let icon = AppIcon(rawValue: savedIcon) {
            self.currentIcon = icon
        }
        
        // Listen for app becoming active to update icon if needed
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(appDidBecomeActive),
            name: UIApplication.didBecomeActiveNotification,
            object: nil
        )
    }
    
    @objc private func appDidBecomeActive() {
        // Update icon when app becomes active (in case system theme changed)
        print("📱 App became active, checking if icon needs update...")
        // This will be called by ThemeManager when needed
    }
    
    deinit {
        NotificationCenter.default.removeObserver(self)
    }
    
    func setIcon(_ icon: AppIcon) {
        guard UIApplication.shared.supportsAlternateIcons else {
            print("❌ Alternate icons not supported on this device")
            return
        }
        
        print("🔄 Setting app icon to: \(icon.displayName)")
        
        // iOS 18 enhanced icon switching with haptic feedback
        let impactFeedback = UIImpactFeedbackGenerator(style: .medium)
        impactFeedback.impactOccurred()
        
        UIApplication.shared.setAlternateIconName(icon.iconName) { error in
            if let error = error {
                print("❌ Failed to set app icon: \(error.localizedDescription)")
                // Haptic feedback for error
                let notificationFeedback = UINotificationFeedbackGenerator()
                notificationFeedback.notificationOccurred(.error)
            } else {
                print("✅ Successfully set app icon to: \(icon.displayName)")
                // Success haptic feedback
                let notificationFeedback = UINotificationFeedbackGenerator()
                notificationFeedback.notificationOccurred(.success)
                
                DispatchQueue.main.async {
                    self.currentIcon = icon
                    UserDefaults.standard.set(icon.rawValue, forKey: "selectedAppIcon")
                }
            }
        }
    }
    
    func setIconBasedOnTheme(_ theme: ThemeManager.AppTheme, isDark: Bool) {
        let icon: AppIcon
        switch theme {
        case .light:
            icon = .light
        case .dark:
            icon = .dark
        case .system:
            icon = isDark ? .dark : .light
        }
        
        print("🎨 Theme changed to: \(theme.displayName), isDark: \(isDark), setting icon to: \(icon.displayName)")
        setIcon(icon)
    }
}
