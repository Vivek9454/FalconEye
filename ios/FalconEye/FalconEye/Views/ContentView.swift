import SwiftUI

struct ContentView: View {
    @EnvironmentObject var authManager: AuthenticationManager
    @EnvironmentObject var themeManager: ThemeManager
    @EnvironmentObject var networkManager: NetworkManager
    @State private var selectedTab = 0
    
    var body: some View {
        if authManager.isAuthenticated {
            ZStack {
                // Background
                AppColors.background(for: themeManager.currentTheme, isDark: themeManager.isDarkMode)
                    .ignoresSafeArea()
                
                // Main content with iOS 18 enhanced TabView
                TabView(selection: $selectedTab) {
                    // Dashboard
                    DashboardView()
                        .tabItem {
                            Image(systemName: "house.fill")
                            Text("Dashboard")
                        }
                        .tag(0)
                    
                    // Live Cameras
                    CameraView()
                        .tabItem {
                            Image(systemName: "video.fill")
                            Text("Live")
                        }
                        .tag(1)
                    
                    // Clips
                    ClipsView()
                        .tabItem {
                            Image(systemName: "play.rectangle.fill")
                            Text("Clips")
                        }
                        .tag(2)
                    
                    // Settings
                    SettingsView()
                        .tabItem {
                            Image(systemName: "gearshape.fill")
                            Text("Settings")
                        }
                        .tag(3)
                }
                .accentColor(AppColors.accent(for: themeManager.currentTheme, isDark: themeManager.isDarkMode))
                .preferredColorScheme(themeManager.colorScheme)
                .background(.ultraThinMaterial.opacity(0.1))
                
                // Network Status Indicator
                VStack {
                    HStack {
                        Spacer()
                        NetworkStatusIndicator()
                            .padding(.top, 10)
                            .padding(.trailing, 20)
                    }
                    Spacer()
                }
            }
        } else {
            LoginView()
        }
    }
}

struct DashboardView: View {
    @EnvironmentObject var apiService: APIService
    @EnvironmentObject var themeManager: ThemeManager
    @State private var systemStatus: SystemStatus?
    @State private var isLoading = true
    @State private var errorMessage: String?
    
    var body: some View {
        NavigationView {
            ZStack {
                AppColors.background(for: themeManager.currentTheme, isDark: themeManager.isDarkMode)
                    .ignoresSafeArea()
                
                if isLoading {
                    LoadingView(theme: themeManager.currentTheme, isDark: themeManager.isDarkMode)
                } else if let errorMessage = errorMessage {
                    ErrorView(message: errorMessage, onRetry: loadSystemStatus, theme: themeManager.currentTheme, isDark: themeManager.isDarkMode)
                } else {
                    DashboardContent(systemStatus: systemStatus, theme: themeManager.currentTheme, isDark: themeManager.isDarkMode)
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
                let status = try await apiService.getSystemStatus()
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

struct LoadingView: View {
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        VStack(spacing: 20) {
            ProgressView()
                .progressViewStyle(CircularProgressViewStyle(tint: AppColors.accent(for: theme, isDark: isDark)))
                .scaleEffect(1.2)
            
            Text("Loading Dashboard...")
                .font(.system(size: 16, weight: .medium))
                .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
        }
    }
}

struct ErrorView: View {
    let message: String
    let onRetry: () -> Void
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 50))
                .foregroundColor(.red)
            
            Text("Connection Error")
                .font(.title2)
                .fontWeight(.semibold)
                .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
            
            Text(message)
                .font(.body)
                .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
            
            Button("Retry") {
                onRetry()
            }
            .buttonStyle(ThemeButtonStyle(theme: theme, isDark: isDark))
        }
    }
}

struct DashboardContent: View {
    let systemStatus: SystemStatus?
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        ScrollView {
            LazyVStack(spacing: 20) {
                DashboardHeader(theme: theme, isDark: isDark)
                
                if let status = systemStatus {
                    SystemStatusCards(status: status, theme: theme, isDark: isDark)
                }
            }
            .padding(.bottom, 100)
        }
    }
}

struct DashboardHeader: View {
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        VStack(spacing: 16) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 12) {
                        ThemeAwareLogo(theme: theme, isDark: isDark, size: 32)
                        
                        VStack(alignment: .leading, spacing: 2) {
                            Text("FalconEye")
                                .font(.system(size: 32, weight: .bold, design: .rounded))
                                .foregroundStyle(
                                    LinearGradient(
                                        colors: [AppColors.accent(for: theme, isDark: isDark), AppColors.accent(for: theme, isDark: isDark).opacity(0.8)],
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    )
                                )
                            
                            Text("Security Dashboard")
                                .font(.system(size: 16, weight: .medium))
                                .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
                        }
                    }
                }
                
                Spacer()
                
                StatusIndicator(theme: theme, isDark: isDark)
            }
        }
        .padding(.horizontal, 20)
        .padding(.top, 20)
    }
}

struct StatusIndicator: View {
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        HStack(spacing: 8) {
            Circle()
                .fill(AppColors.accent(for: theme, isDark: isDark))
                .frame(width: 8, height: 8)
            
            Text("Online")
                .font(.system(size: 14, weight: .semibold))
                .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(AppColors.accent(for: theme, isDark: isDark).opacity(0.1))
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(AppColors.accent(for: theme, isDark: isDark).opacity(0.3), lineWidth: 1)
                )
        )
    }
}

struct SystemStatusCards: View {
    let status: SystemStatus
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        VStack(spacing: 20) {
            DeviceInfoCard(status: status, theme: theme, isDark: isDark)
            FeaturesCard(status: status, theme: theme, isDark: isDark)
            SurveillanceObjectsCard(status: status, theme: theme, isDark: isDark)
        }
        .padding(.horizontal, 20)
    }
}

struct DeviceInfoCard: View {
    let status: SystemStatus
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        ThemeGlassCard(theme: theme, isDark: isDark) {
            VStack(spacing: 16) {
                HStack {
                    Image(systemName: "cpu")
                        .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                        .font(.system(size: 20))
                    
                    Text("Device Information")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                    
                    Spacer()
                }
                
                HStack {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Device Type")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
                        
                        Text((status.device ?? "Unknown").uppercased())
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                    }
                    
                    Spacer()
                    
                    VStack(alignment: .trailing, spacing: 8) {
                        Text("Status")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
                        
                        Text(status.status.uppercased())
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                    }
                }
            }
        }
    }
}

struct FeaturesCard: View {
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
                        FeatureRow(feature: "Live Stream", isEnabled: features.live_stream ?? false, theme: theme, isDark: isDark)
                        FeatureRow(feature: "Object Detection", isEnabled: features.object_detection ?? false, theme: theme, isDark: isDark)
                        FeatureRow(feature: "Video Recording", isEnabled: features.video_recording ?? false, theme: theme, isDark: isDark)
                        FeatureRow(feature: "Push Notifications", isEnabled: features.push_notifications ?? false, theme: theme, isDark: isDark)
                        FeatureRow(feature: "Mobile Optimized", isEnabled: features.mobile_optimized ?? false, theme: theme, isDark: isDark)
                    }
                }
            }
        }
    }
}

struct FeatureRow: View {
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

struct SurveillanceObjectsCard: View {
    let status: SystemStatus
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        ThemeGlassCard(theme: theme, isDark: isDark) {
            VStack(spacing: 16) {
                HStack {
                    Image(systemName: "eye.fill")
                        .foregroundColor(AppColors.accent(for: theme, isDark: isDark))
                        .font(.system(size: 20))
                    
                    Text("Detection Objects")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                    
                    Spacer()
                }
                
                LazyVGrid(columns: [
                    GridItem(.flexible()),
                    GridItem(.flexible()),
                    GridItem(.flexible())
                ], spacing: 12) {
                    ForEach(status.surveillance_objects ?? [], id: \.self) { object in
                        SurveillanceObjectTag(object: object, theme: theme, isDark: isDark)
                    }
                }
            }
        }
    }
}

struct SurveillanceObjectTag: View {
    let object: String
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        Text(object.capitalized)
            .font(.system(size: 14, weight: .medium))
            .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(AppColors.accent(for: theme, isDark: isDark).opacity(0.1))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(AppColors.accent(for: theme, isDark: isDark).opacity(0.3), lineWidth: 1)
                    )
            )
    }
}

// Legacy GlassCard - use ThemeGlassCard instead
struct GlassCard<Content: View>: View {
    let content: Content
    
    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }
    
    var body: some View {
        content
            .padding(20)
            .background(
                RoundedRectangle(cornerRadius: 16)
                    .fill(.ultraThinMaterial)
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(.white.opacity(0.1), lineWidth: 1)
                    )
                    .shadow(color: .black.opacity(0.3), radius: 10, x: 0, y: 5)
            )
    }
}

#Preview {
    ContentView()
        .environmentObject(AuthenticationManager())
        .environmentObject(APIService.shared)
}
