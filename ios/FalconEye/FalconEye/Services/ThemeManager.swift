import SwiftUI
import Foundation

class ThemeManager: ObservableObject {
    @Published var currentTheme: AppTheme = .system
    
    enum AppTheme: String, CaseIterable {
        case light = "light"
        case dark = "dark"
        case system = "system"
        
        var displayName: String {
            switch self {
            case .light: return "Light"
            case .dark: return "Dark"
            case .system: return "System"
            }
        }
    }
    
    var colorScheme: ColorScheme? {
        switch currentTheme {
        case .light: return .light
        case .dark: return .dark
        case .system: return nil
        }
    }
    
    var isDarkMode: Bool {
        switch currentTheme {
        case .light: return false
        case .dark: return true
        case .system: return UITraitCollection.current.userInterfaceStyle == .dark
        }
    }
    
    func setTheme(_ theme: AppTheme) {
        currentTheme = theme
        UserDefaults.standard.set(theme.rawValue, forKey: "app_theme")
        
        // Update app icon based on theme
        AppIconManager.shared.setIconBasedOnTheme(theme, isDark: isDarkMode)
    }
    
    init() {
        if let savedTheme = UserDefaults.standard.string(forKey: "app_theme"),
           let theme = AppTheme(rawValue: savedTheme) {
            currentTheme = theme
        }
        
        // Set app icon based on current theme after a short delay to ensure UI is ready
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            AppIconManager.shared.setIconBasedOnTheme(self.currentTheme, isDark: self.isDarkMode)
        }
        
        // Listen for app becoming active to update icon if system theme changed
        NotificationCenter.default.addObserver(
            forName: UIApplication.didBecomeActiveNotification,
            object: nil,
            queue: .main
        ) { _ in
            // Update icon when app becomes active (in case system theme changed)
            if self.currentTheme == .system {
                AppIconManager.shared.setIconBasedOnTheme(self.currentTheme, isDark: self.isDarkMode)
            }
        }
    }
}

// MARK: - Theme Colors
struct AppColors {
    static func primary(for theme: ThemeManager.AppTheme, isDark: Bool) -> Color {
        switch theme {
        case .light: return .black
        case .dark: return .white
        case .system: return isDark ? .white : .black
        }
    }
    
    static func secondary(for theme: ThemeManager.AppTheme, isDark: Bool) -> Color {
        switch theme {
        case .light: return Color(red: 0.4, green: 0.4, blue: 0.4)
        case .dark: return Color(red: 0.6, green: 0.6, blue: 0.6)
        case .system: return isDark ? Color(red: 0.6, green: 0.6, blue: 0.6) : Color(red: 0.4, green: 0.4, blue: 0.4)
        }
    }
    
    static func accent(for theme: ThemeManager.AppTheme, isDark: Bool) -> Color {
        switch theme {
        case .light: return Color(red: 0.0, green: 0.5, blue: 0.0) // Green
        case .dark: return Color(red: 0.0, green: 0.8, blue: 0.0) // Brighter green
        case .system: return isDark ? Color(red: 0.0, green: 0.8, blue: 0.0) : Color(red: 0.0, green: 0.5, blue: 0.0)
        }
    }
    
    static func background(for theme: ThemeManager.AppTheme, isDark: Bool) -> Color {
        switch theme {
        case .light: return Color(red: 0.95, green: 0.95, blue: 0.95) // Light gray
        case .dark: return .black
        case .system: return isDark ? .black : Color(red: 0.95, green: 0.95, blue: 0.95)
        }
    }
    
    static func cardBackground(for theme: ThemeManager.AppTheme, isDark: Bool) -> Color {
        switch theme {
        case .light: return Color(red: 0.98, green: 0.98, blue: 0.98) // Very light gray
        case .dark: return Color(red: 0.1, green: 0.1, blue: 0.1) // Dark gray
        case .system: return isDark ? Color(red: 0.1, green: 0.1, blue: 0.1) : Color(red: 0.98, green: 0.98, blue: 0.98)
        }
    }
    
    static func glassBackground(for theme: ThemeManager.AppTheme, isDark: Bool) -> Color {
        switch theme {
        case .light: return Color.white.opacity(0.7)
        case .dark: return Color.black.opacity(0.3)
        case .system: return isDark ? Color.black.opacity(0.3) : Color.white.opacity(0.7)
        }
    }
    
    static func border(for theme: ThemeManager.AppTheme, isDark: Bool) -> Color {
        switch theme {
        case .light: return Color(red: 0.8, green: 0.8, blue: 0.8)
        case .dark: return Color.white.opacity(0.1)
        case .system: return isDark ? Color.white.opacity(0.1) : Color(red: 0.8, green: 0.8, blue: 0.8)
        }
    }
    
    static func shadow(for theme: ThemeManager.AppTheme, isDark: Bool) -> Color {
        switch theme {
        case .light: return Color.black.opacity(0.1)
        case .dark: return Color.black.opacity(0.3)
        case .system: return isDark ? Color.black.opacity(0.3) : Color.black.opacity(0.1)
        }
    }
}

// MARK: - Theme-aware Button Style
struct ThemeButtonStyle: ButtonStyle {
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundColor(.white)
            .padding(.horizontal, 20)
            .padding(.vertical, 12)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(AppColors.accent(for: theme, isDark: isDark))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(AppColors.accent(for: theme, isDark: isDark).opacity(0.3), lineWidth: 1)
                    )
            )
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}

// MARK: - iOS 18 Liquid Glass Card
struct ThemeGlassCard<Content: View>: View {
    let content: Content
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    init(theme: ThemeManager.AppTheme, isDark: Bool, @ViewBuilder content: () -> Content) {
        self.theme = theme
        self.isDark = isDark
        self.content = content()
    }
    
    var body: some View {
        content
            .padding(20)
            .background(
                ZStack {
                    // iOS 18 Liquid Glass Effect with .ultraThinMaterial
                    RoundedRectangle(cornerRadius: 20)
                        .fill(.ultraThinMaterial)
                        .overlay(
                            RoundedRectangle(cornerRadius: 20)
                                .fill(
                                    LinearGradient(
                                        colors: [
                                            AppColors.accent(for: theme, isDark: isDark).opacity(0.15),
                                            AppColors.accent(for: theme, isDark: isDark).opacity(0.05),
                                            Color.clear
                                        ],
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    )
                                )
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: 20)
                                .stroke(
                                    LinearGradient(
                                        colors: [
                                            AppColors.accent(for: theme, isDark: isDark).opacity(0.4),
                                            AppColors.accent(for: theme, isDark: isDark).opacity(0.1),
                                            Color.clear
                                        ],
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    ),
                                    lineWidth: 1.5
                                )
                        )
                        .shadow(color: AppColors.accent(for: theme, isDark: isDark).opacity(0.2), radius: 25, x: 0, y: 12)
                        .shadow(color: AppColors.primary(for: theme, isDark: isDark).opacity(0.1), radius: 8, x: 0, y: 4)
                }
            )
    }
}

// MARK: - iOS 18 Liquid Glass Button
struct LiquidGlassButtonStyle: ButtonStyle {
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundColor(.white)
            .font(.system(size: 16, weight: .semibold, design: .rounded))
            .padding(.horizontal, 24)
            .padding(.vertical, 14)
            .background(
                ZStack {
                    // Liquid glass background
                    RoundedRectangle(cornerRadius: 16)
                        .fill(.ultraThinMaterial)
                        .overlay(
                            RoundedRectangle(cornerRadius: 16)
                                .fill(
                                    LinearGradient(
                                        colors: [
                                            AppColors.accent(for: theme, isDark: isDark).opacity(0.8),
                                            AppColors.accent(for: theme, isDark: isDark).opacity(0.6)
                                        ],
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    )
                                )
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: 16)
                                .stroke(
                                    LinearGradient(
                                        colors: [
                                            Color.white.opacity(0.3),
                                            Color.white.opacity(0.1)
                                        ],
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    ),
                                    lineWidth: 1
                                )
                        )
                        .shadow(color: AppColors.accent(for: theme, isDark: isDark).opacity(0.3), radius: 15, x: 0, y: 8)
                }
            )
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
            .animation(.spring(response: 0.3, dampingFraction: 0.7), value: configuration.isPressed)
    }
}

// MARK: - iOS 18 Floating Action Button
struct FloatingActionButton: View {
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    let action: () -> Void
    let icon: String
    var isLoading: Bool = false
    
    var body: some View {
        Button(action: action) {
            Group {
                if isLoading {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        .scaleEffect(0.8)
                } else {
                    Image(systemName: icon)
                        .font(.system(size: 20, weight: .semibold))
                        .foregroundColor(.white)
                }
            }
            .frame(width: 56, height: 56)
            .background(
                ZStack {
                    Circle()
                        .fill(.ultraThinMaterial)
                        .overlay(
                            Circle()
                                .fill(
                                    RadialGradient(
                                        colors: [
                                            AppColors.accent(for: theme, isDark: isDark).opacity(0.9),
                                            AppColors.accent(for: theme, isDark: isDark).opacity(0.7)
                                        ],
                                        center: .center,
                                        startRadius: 0,
                                        endRadius: 28
                                    )
                                )
                        )
                        .overlay(
                            Circle()
                                .stroke(
                                    LinearGradient(
                                        colors: [
                                            Color.white.opacity(0.4),
                                            Color.white.opacity(0.1)
                                        ],
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    ),
                                    lineWidth: 1.5
                                )
                        )
                        .shadow(color: AppColors.accent(for: theme, isDark: isDark).opacity(0.4), radius: 20, x: 0, y: 10)
                }
            )
        }
        .buttonStyle(PlainButtonStyle())
        .disabled(isLoading)
        .scaleEffect(isLoading ? 0.95 : 1.0)
        .animation(.easeInOut(duration: 0.2), value: isLoading)
    }
}
