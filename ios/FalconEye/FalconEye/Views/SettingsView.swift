import SwiftUI
import UIKit

struct SettingsView: View {
    @EnvironmentObject var authManager: AuthenticationManager
    @EnvironmentObject var apiService: APIService
    @EnvironmentObject var themeManager: ThemeManager
    @EnvironmentObject var networkManager: NetworkManager
    @State private var systemStatus: SystemStatus?
    @State private var isLoading = true
    @State private var errorMessage: String?
    
    var body: some View {
        NavigationView {
            ZStack {
                AppColors.background(for: themeManager.currentTheme, isDark: themeManager.isDarkMode)
                    .ignoresSafeArea()
                
                if isLoading {
                    SettingsLoadingView(theme: themeManager.currentTheme, isDark: themeManager.isDarkMode)
                } else {
                    SettingsContent(systemStatus: systemStatus, authManager: authManager, theme: themeManager.currentTheme, isDark: themeManager.isDarkMode)
                }
            }
            .navigationBarHidden(true)
        }
        .onAppear {
            loadSystemStatus()
        }
    }
    
    private func loadSystemStatus() {
        isLoading = true
        errorMessage = nil
        
        Task {
            do {
                let status = try await APIService.shared.getSystemStatus()
                await MainActor.run {
                    self.systemStatus = status
                    self.isLoading = false
                }
            } catch {
                await MainActor.run {
                    self.errorMessage = error.localizedDescription
                    self.isLoading = false
                }
            }
        }
    }
}

struct SettingsLoadingView: View {
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        VStack(spacing: 20) {
            ProgressView()
                .progressViewStyle(CircularProgressViewStyle(tint: AppColors.accent(for: theme, isDark: isDark)))
                .scaleEffect(1.2)
            
            Text("Loading Settings...")
                .font(.system(size: 16, weight: .medium))
                .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
        }
    }
}

struct SettingsContent: View {
    let systemStatus: SystemStatus?
    let authManager: AuthenticationManager
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        ScrollView {
            LazyVStack(spacing: 20) {
                SettingsHeader(theme: theme, isDark: isDark)
                NetworkInfoCard(theme: theme, isDark: isDark)
                NetworkControlCard(theme: theme, isDark: isDark)
                NotificationStatusCard(theme: theme, isDark: isDark)
                ThemeSelectorCard(theme: theme, isDark: isDark)
                AppIconSelectorCard(theme: theme, isDark: isDark)
                ConnectionStatusCard(theme: theme, isDark: isDark)
                
                if let status = systemStatus {
                    SystemInfoCard(status: status, theme: theme, isDark: isDark)
                    FeaturesStatusCard(status: status, theme: theme, isDark: isDark)
                    FacesControlCard(theme: theme, isDark: isDark)
                }
                
                AppInfoCard(theme: theme, isDark: isDark)
                LogoutButton(authManager: authManager, theme: theme, isDark: isDark)
            }
            .padding(.bottom, 100)
        }
    }
}

struct SettingsHeader: View {
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        VStack(spacing: 16) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 12) {
                        ThemeAwareLogo(theme: theme, isDark: isDark, size: 28)
                        
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Settings")
                                .font(.system(size: 28, weight: .bold, design: .rounded))
                                .foregroundStyle(
                                    LinearGradient(
                                        colors: [AppColors.accent(for: theme, isDark: isDark), AppColors.accent(for: theme, isDark: isDark).opacity(0.8)],
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    )
                                )
                            
                            Text("System configuration and status")
                                .font(.system(size: 16, weight: .medium))
                                .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
                        }
                    }
                }
                
                Spacer()
            }
        }
        .padding(.horizontal, 20)
        .padding(.top, 20)
    }
}

struct NetworkInfoCard: View {
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    @EnvironmentObject var networkManager: NetworkManager
    
    var body: some View {
        ThemeGlassCard(theme: theme, isDark: isDark) {
            VStack(spacing: 16) {
                HStack {
                    Image(systemName: "network")
                        .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                        .font(.system(size: 20))
                    
                    Text("Network Status")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                    
                    Spacer()
                    
                    NetworkStatusIndicator()
                }
                
                VStack(spacing: 12) {
                    HStack {
                        Text("Connection Type:")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
                        
                        Spacer()
                        
                        Text(networkManager.isLocalNetwork ? "Local Network" : "Cloudflare Tunnel")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                    }
                    
                    HStack {
                        Text("Server URL:")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
                        
                        Spacer()
                        
                        Text(networkManager.currentBaseURL)
                            .font(.system(size: 12, weight: .medium, design: .monospaced))
                            .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                            .lineLimit(1)
                            .minimumScaleFactor(0.8)
                    }
                    
                    Button("Refresh Network Status") {
                        networkManager.refreshNetworkStatus()
                    }
                    .buttonStyle(LiquidGlassButtonStyle(theme: theme, isDark: isDark))
                    .font(.system(size: 14, weight: .medium))
                }
            }
        }
        .padding(.horizontal, 20)
    }
}

struct ThemeSelectorCard: View {
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    @EnvironmentObject var themeManager: ThemeManager
    
    var body: some View {
        ThemeGlassCard(theme: theme, isDark: isDark) {
            VStack(spacing: 16) {
                HStack {
                    Image(systemName: "paintbrush.fill")
                        .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                        .font(.system(size: 20))
                    
                    Text("Appearance")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                    
                    Spacer()
                }
                
                VStack(spacing: 12) {
                    ForEach(ThemeManager.AppTheme.allCases, id: \.self) { themeOption in
                        Button(action: {
                            themeManager.setTheme(themeOption)
                        }) {
                            HStack {
                                Image(systemName: themeIcon(for: themeOption))
                                    .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                                    .font(.system(size: 16))
                                
                                Text(themeOption.displayName)
                                    .font(.system(size: 16, weight: .medium))
                                    .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                                
                                Spacer()
                                
                                if themeManager.currentTheme == themeOption {
                                    Image(systemName: "checkmark.circle.fill")
                                        .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                                        .font(.system(size: 16))
                                }
                            }
                            .padding(.vertical, 8)
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                }
            }
        }
        .padding(.horizontal, 20)
    }
    
    private func themeIcon(for theme: ThemeManager.AppTheme) -> String {
        switch theme {
        case .light: return "sun.max.fill"
        case .dark: return "moon.fill"
        case .system: return "gear"
        }
    }
}

struct AppIconSelectorCard: View {
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    @EnvironmentObject var appIconManager: AppIconManager
    
    var body: some View {
        ThemeGlassCard(theme: theme, isDark: isDark) {
            VStack(spacing: 16) {
                HStack {
                    Image(systemName: "app.badge")
                        .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                        .font(.system(size: 20))
                    
                    Text("App Icon")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                    
                    Spacer()
                }
                
                VStack(spacing: 12) {
                    ForEach(AppIconManager.AppIcon.allCases, id: \.self) { iconOption in
                        Button(action: {
                            appIconManager.setIcon(iconOption)
                        }) {
                            HStack {
                                Image(systemName: iconIcon(for: iconOption))
                                    .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                                    .font(.system(size: 16))
                                
                                Text(iconOption.displayName)
                                    .font(.system(size: 16, weight: .medium))
                                    .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                                
                                Spacer()
                                
                                if appIconManager.currentIcon == iconOption {
                                    Image(systemName: "checkmark.circle.fill")
                                        .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                                        .font(.system(size: 16))
                                }
                            }
                            .padding(.vertical, 8)
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                }
            }
        }
        .padding(.horizontal, 20)
    }
    
    private func iconIcon(for icon: AppIconManager.AppIcon) -> String {
        switch icon {
        case .primary: return "app"
        case .light: return "sun.max.fill"
        case .dark: return "moon.fill"
        }
    }
}

struct ConnectionStatusCard: View {
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        ThemeGlassCard(theme: theme, isDark: isDark) {
            VStack(spacing: 16) {
                HStack {
                    Image(systemName: "wifi")
                        .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                        .font(.system(size: 20))
                    
                    Text("Connection Status")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                    
                    Spacer()
                }
                
                HStack {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Server")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
                        
                        Text(APIService.shared.baseURL)
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                    }
                    
                    Spacer()
                    
                    VStack(alignment: .trailing, spacing: 8) {
                        Text("Status")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
                        
                        HStack(spacing: 6) {
                            Circle()
                                .fill(AppColors.accent(for: theme, isDark: isDark))
                                .frame(width: 8, height: 8)
                            
                            Text("Connected")
                                .font(.system(size: 16, weight: .semibold))
                                .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                        }
                    }
                }
            }
        }
        .padding(.horizontal, 20)
    }
}

struct SystemInfoCard: View {
    let status: SystemStatus
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        ThemeGlassCard(theme: theme, isDark: isDark) {
            VStack(spacing: 16) {
                HStack {
                    Image(systemName: "info.circle")
                        .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                        .font(.system(size: 20))
                    
                    Text("System Information")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                    
                    Spacer()
                }
                
                VStack(spacing: 12) {
                    HStack {
                        Text("Device Type")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
                        
                        Spacer()
                        
                        Text((status.device ?? "Unknown").uppercased())
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                    }
                    
                    HStack {
                        Text("System Status")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
                        
                        Spacer()
                        
                        HStack(spacing: 6) {
                            Circle()
                                .fill(AppColors.accent(for: theme, isDark: isDark))
                                .frame(width: 8, height: 8)
                            
                            Text(status.status.uppercased())
                                .font(.system(size: 16, weight: .semibold))
                                .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                        }
                    }
                    
                    HStack {
                        Text("Detection Objects")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
                        
                        Spacer()
                        
                        Text("\(status.surveillance_objects?.count ?? 0) configured")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                    }
                }
            }
        }
        .padding(.horizontal, 20)
    }
}

struct FacesControlCard: View {
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    @State private var facesEnabled: Bool = false
    @State private var loading = false
    @State private var message: String?

    var body: some View {
        ThemeGlassCard(theme: theme, isDark: isDark) {
            VStack(spacing: 16) {
                HStack {
                    Image(systemName: "face.smiling")
                        .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                        .font(.system(size: 20))
                    Text("Facial Recognition")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                    Spacer()
                    Toggle("", isOn: Binding(
                        get: { facesEnabled },
                        set: { val in Task { await toggleFaces(val) } }
                    ))
                    .labelsHidden()
                }
                if let msg = message {
                    Text(msg)
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                }
                HStack {
                    Button(action: { Task { await refreshStatus() } }) {
                        Label("Refresh Status", systemImage: "arrow.clockwise")
                    }
                    .buttonStyle(LiquidGlassButtonStyle(theme: theme, isDark: isDark))
                    Spacer()
                    Button(action: { Task { await quickRegisterSample() } }) {
                        Label("Quick Register Test", systemImage: "person.crop.circle.badge.plus")
                    }
                    .buttonStyle(LiquidGlassButtonStyle(theme: theme, isDark: isDark))
                }
            }
            .task { await refreshStatus() }
        }
        .padding(.horizontal, 20)
    }

    private func refreshStatus() async {
        loading = true
        defer { loading = false }
        do {
            let status = try await APIService.shared.getFacesStatus()
            facesEnabled = status.enabled
            message = "Engine: \(status.engine ?? "-")"
        } catch {
            message = error.localizedDescription
        }
    }

    private func toggleFaces(_ enabled: Bool) async {
        loading = true
        defer { loading = false }
        do {
            let status = try await APIService.shared.setFacesEnabled(enabled)
            facesEnabled = status.enabled
            message = "Faces \(status.enabled ? "Enabled" : "Disabled")"
        } catch {
            message = error.localizedDescription
        }
    }

    private func quickRegisterSample() async {
        // This stub demonstrates registration flow; replace with image picker.
        guard let img = UIImage(systemName: "person.crop.circle")?.withTintColor(.black, renderingMode: .alwaysOriginal),
              let data = img.jpegData(compressionQuality: 0.8) else {
            message = "No sample image available"
            return
        }
        do {
            let res = try await APIService.shared.registerFace(name: "TestUser", jpegData: data)
            message = res.message ?? (res.success == true ? "Registered" : "Failed")
        } catch {
            message = error.localizedDescription
        }
    }
}

struct FeaturesStatusCard: View {
    let status: SystemStatus
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        ThemeGlassCard(theme: theme, isDark: isDark) {
            VStack(spacing: 16) {
                HStack {
                    Image(systemName: "star.fill")
                        .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                        .font(.system(size: 20))
                    
                    Text("System Features")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                    
                    Spacer()
                }
                
                LazyVGrid(columns: [
                    GridItem(.flexible()),
                    GridItem(.flexible())
                ], spacing: 12) {
                    if let features = status.features {
                        FeatureStatusRow(feature: "Live Stream", isEnabled: features.live_stream ?? false, theme: theme, isDark: isDark)
                        FeatureStatusRow(feature: "Object Detection", isEnabled: features.object_detection ?? false, theme: theme, isDark: isDark)
                        FeatureStatusRow(feature: "Video Recording", isEnabled: features.video_recording ?? false, theme: theme, isDark: isDark)
                        FeatureStatusRow(feature: "Push Notifications", isEnabled: features.push_notifications ?? false, theme: theme, isDark: isDark)
                        FeatureStatusRow(feature: "Mobile Optimized", isEnabled: features.mobile_optimized ?? false, theme: theme, isDark: isDark)
                    }
                }
            }
        }
        .padding(.horizontal, 20)
    }
}

struct FeatureStatusRow: View {
    let feature: String
    let isEnabled: Bool
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: isEnabled ? "checkmark.circle.fill" : "xmark.circle.fill")
                .foregroundColor(isEnabled ? AppColors.accent(for: theme, isDark: isDark) : .red)
                .font(.system(size: 16))
            
            Text(feature.replacingOccurrences(of: "_", with: " ").capitalized)
                .font(.system(size: 14, weight: .medium))
                .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct AppInfoCard: View {
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        ThemeGlassCard(theme: theme, isDark: isDark) {
            VStack(spacing: 16) {
                HStack {
                    Image(systemName: "app.badge")
                        .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                        .font(.system(size: 20))
                    
                    Text("App Information")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                    
                    Spacer()
                }
                
                VStack(spacing: 12) {
                    InfoRow(label: "Version", value: "1.0.0", theme: theme, isDark: isDark)
                    InfoRow(label: "Build", value: "Debug", theme: theme, isDark: isDark)
                    InfoRow(label: "Platform", value: "iOS", theme: theme, isDark: isDark)
                }
            }
        }
        .padding(.horizontal, 20)
    }
}

struct InfoRow: View {
    let label: String
    let value: String
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        HStack {
            Text(label)
                .font(.system(size: 14, weight: .medium))
                .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
            
            Spacer()
            
            Text(value)
                .font(.system(size: 16, weight: .semibold))
                .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
        }
    }
}

struct LogoutButton: View {
    let authManager: AuthenticationManager
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        Button(action: {
            authManager.logout()
        }) {
            HStack {
                Image(systemName: "rectangle.portrait.and.arrow.right")
                    .font(.system(size: 16, weight: .semibold))
                
                Text("Logout")
                    .font(.system(size: 16, weight: .semibold))
            }
            .foregroundColor(.white)
            .frame(maxWidth: .infinity)
            .frame(height: 56)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(.red)
            )
        }
        .buttonStyle(LiquidGlassButtonStyle(theme: theme, isDark: isDark))
        .padding(.horizontal, 20)
    }
}

// MARK: - Network Control Card
struct NetworkControlCard: View {
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    @EnvironmentObject var networkManager: NetworkManager
    
    var body: some View {
        ThemeGlassCard(theme: theme, isDark: isDark) {
            VStack(spacing: 16) {
                HStack {
                    Image(systemName: "network")
                        .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                        .font(.system(size: 20))
                    
                    Text("Network Control")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                    
                    Spacer()
                }
                
                VStack(spacing: 12) {
                    HStack {
                        Text("Current Mode:")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
                        
                        Spacer()
                        
                        Text(networkManager.isLocalNetwork ? "Local Network" : "Cloudflare Tunnel")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                    }
                    
                    HStack(spacing: 12) {
                        Button("Force Local") {
                            networkManager.forceLocalNetwork()
                        }
                        .buttonStyle(LiquidGlassButtonStyle(theme: theme, isDark: isDark))
                        .font(.system(size: 14, weight: .medium))
                        
                        Button("Force Cloud") {
                            networkManager.forceCloudflareMode()
                        }
                        .buttonStyle(LiquidGlassButtonStyle(theme: theme, isDark: isDark))
                        .font(.system(size: 14, weight: .medium))
                        
                        Button("Auto Detect") {
                            networkManager.refreshNetworkStatus()
                        }
                        .buttonStyle(LiquidGlassButtonStyle(theme: theme, isDark: isDark))
                        .font(.system(size: 14, weight: .medium))
                    }
                }
            }
        }
        .padding(.horizontal, 20)
    }
}

// MARK: - Notification Status Card
struct NotificationStatusCard: View {
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    @EnvironmentObject var notificationManager: LocalNotificationManager
    
    var body: some View {
        ThemeGlassCard(theme: theme, isDark: isDark) {
            VStack(spacing: 16) {
                HStack {
                    Image(systemName: "bell.fill")
                        .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                        .font(.system(size: 20))
                    
                    Text("Push Notifications")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                    
                    Spacer()
                    
                    // Status indicator
                    HStack(spacing: 6) {
                        Circle()
                            .fill(notificationManager.isRegistered ? Color.green : Color.red)
                            .frame(width: 8, height: 8)
                            .animation(.easeInOut(duration: 0.3), value: notificationManager.isRegistered)
                        
                        Text(notificationManager.isRegistered ? "Active" : "Inactive")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundColor(notificationManager.isRegistered ? .green : .red)
                    }
                }
                
                VStack(spacing: 12) {
                    // Permission status
                    HStack {
                        Text("Permission:")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
                        
                        Spacer()
                        
                        Text(notificationManager.isAuthorized ? "Granted" : "Not Granted")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(notificationManager.isAuthorized ? .green : .orange)
                    }
                    
                    // Device Registration status
                    HStack {
                        Text("Device Registration:")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
                        
                        Spacer()
                        
                        Text(notificationManager.isRegistered ? "Registered" : "Not Registered")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(notificationManager.isRegistered ? .green : .red)
                    }
                    
                    // Registration status details
                    HStack {
                        Text("Status:")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
                        
                        Spacer()
                        
                        Text(notificationManager.registrationStatus)
                            .font(.system(size: 12, weight: .medium))
                            .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                            .multilineTextAlignment(.trailing)
                    }
                    
                    // Action buttons
                    VStack(spacing: 12) {
                        HStack(spacing: 12) {
                            if !notificationManager.isAuthorized {
                                Button("Request Permission") {
                                    notificationManager.requestPermissions()
                                }
                                .buttonStyle(LiquidGlassButtonStyle(theme: theme, isDark: isDark))
                                .font(.system(size: 14, weight: .medium))
                            }
                            
                            Button("Test Notification") {
                                notificationManager.sendTestNotification()
                            }
                            .buttonStyle(LiquidGlassButtonStyle(theme: theme, isDark: isDark))
                            .font(.system(size: 14, weight: .medium))
                            
                            Button("Security Alert") {
                                notificationManager.sendLocalSecurityAlert(detectedObjects: ["Person", "Vehicle"])
                            }
                            .buttonStyle(LiquidGlassButtonStyle(theme: theme, isDark: isDark))
                            .font(.system(size: 14, weight: .medium))
                        }
                        
                        // Debug buttons
                        VStack(spacing: 8) {
                            Text("Debug Tools")
                                .font(.system(size: 12, weight: .medium))
                                .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
                            
                            HStack(spacing: 8) {
                                Button("Debug Info") {
                                    print(notificationManager.getDebugInfo())
                                }
                                .buttonStyle(LiquidGlassButtonStyle(theme: theme, isDark: isDark))
                                .font(.system(size: 12, weight: .medium))
                                
                                Button("Start Polling") {
                                    notificationManager.startPollingManually()
                                }
                                .buttonStyle(LiquidGlassButtonStyle(theme: theme, isDark: isDark))
                                .font(.system(size: 12, weight: .medium))
                                
                                Button("Unregister") {
                                    Task {
                                        await notificationManager.unregisterDevice()
                                    }
                                }
                                .buttonStyle(LiquidGlassButtonStyle(theme: theme, isDark: isDark))
                                .font(.system(size: 12, weight: .medium))
                            }
                        }
                    }
                }
            }
        }
        .padding(.horizontal, 20)
    }
}

#Preview {
    SettingsView()
        .environmentObject(AuthenticationManager())
        .environmentObject(APIService.shared)
}