import SwiftUI

// MARK: - Camera Grid Layout
enum CameraGridLayout: String, CaseIterable {
    case grid = "Grid"
    case list = "List"
    case single = "Single"
    
    var icon: String {
        switch self {
        case .grid: return "grid"
        case .list: return "list.bullet"
        case .single: return "rectangle"
        }
    }
}

struct CameraView: View {
    @EnvironmentObject var cameraManager: CameraManager
    @EnvironmentObject var themeManager: ThemeManager
    @State private var selectedCamera: String?
    @State private var showingFullScreen = false
    @State private var isRefreshing = false
    @State private var showingStats = false
    @State private var cameraGridLayout: CameraGridLayout = .grid
    @State private var lastRefreshTime = Date()
    @State private var refreshAnimation = false
    
    var body: some View {
        NavigationView {
            ZStack {
                // Background
                AppColors.background(for: themeManager.currentTheme, isDark: themeManager.isDarkMode)
                    .ignoresSafeArea()
                
                ScrollView {
                    LazyVStack(spacing: 20) {
                        // Enhanced Header with Animations
                        VStack(spacing: 16) {
                            HStack {
                                VStack(alignment: .leading, spacing: 4) {
                                    HStack(spacing: 12) {
                                        ThemeAwareLogo(theme: themeManager.currentTheme, isDark: themeManager.isDarkMode, size: 28)
                                            .scaleEffect(refreshAnimation ? 1.1 : 1.0)
                                            .animation(.easeInOut(duration: 0.3), value: refreshAnimation)
                                        
                                        VStack(alignment: .leading, spacing: 4) {
                                            Text("Live Cameras")
                                                .font(.system(size: 24, weight: .bold, design: .rounded))
                                                .foregroundStyle(
                                                    LinearGradient(
                                                        colors: [AppColors.accent(for: themeManager.currentTheme, isDark: themeManager.isDarkMode), AppColors.accent(for: themeManager.currentTheme, isDark: themeManager.isDarkMode).opacity(0.8)],
                                                        startPoint: .topLeading,
                                                        endPoint: .bottomTrailing
                                                    )
                                                )
                                            
                                            Text("Real-time surveillance feeds")
                                                .font(.system(size: 14, weight: .medium))
                                                .foregroundColor(AppColors.secondary(for: themeManager.currentTheme, isDark: themeManager.isDarkMode))
                                        }
                                    }
                                }
                                
                                Spacer()
                                
                                // Enhanced Control Buttons
                                HStack(spacing: 12) {
                                    // Layout Toggle Button
                                    Menu {
                                        ForEach(CameraGridLayout.allCases, id: \.self) { layout in
                                            Button(action: {
                                                withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                                                    cameraGridLayout = layout
                                                }
                                            }) {
                                                HStack {
                                                    Image(systemName: layout.icon)
                                                    Text(layout.rawValue)
                                                    if cameraGridLayout == layout {
                                                        Image(systemName: "checkmark")
                                                    }
                                                }
                                            }
                                        }
                                    } label: {
                                        Image(systemName: cameraGridLayout.icon)
                                            .font(.system(size: 16, weight: .semibold))
                                            .foregroundColor(AppColors.accent(for: themeManager.currentTheme, isDark: themeManager.isDarkMode))
                                            .padding(12)
                                            .background(
                                                Circle()
                                                    .fill(AppColors.accent(for: themeManager.currentTheme, isDark: themeManager.isDarkMode).opacity(0.1))
                                                    .overlay(
                                                        Circle()
                                                            .stroke(AppColors.accent(for: themeManager.currentTheme, isDark: themeManager.isDarkMode).opacity(0.3), lineWidth: 1)
                                                    )
                                            )
                                    }
                                    
                                    // Stats Button
                                    Button(action: {
                                        withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                                            showingStats.toggle()
                                        }
                                    }) {
                                        Image(systemName: "chart.bar.fill")
                                            .font(.system(size: 16, weight: .semibold))
                                            .foregroundColor(AppColors.accent(for: themeManager.currentTheme, isDark: themeManager.isDarkMode))
                                            .padding(12)
                                            .background(
                                                Circle()
                                                    .fill(AppColors.accent(for: themeManager.currentTheme, isDark: themeManager.isDarkMode).opacity(0.1))
                                                    .overlay(
                                                        Circle()
                                                            .stroke(AppColors.accent(for: themeManager.currentTheme, isDark: themeManager.isDarkMode).opacity(0.3), lineWidth: 1)
                                                    )
                                            )
                                    }
                                    
                                    // Enhanced Refresh Button
                                    Button(action: {
                                        refreshCameras()
                                    }) {
                                        Image(systemName: "arrow.clockwise")
                                            .font(.system(size: 16, weight: .semibold))
                                            .foregroundColor(AppColors.accent(for: themeManager.currentTheme, isDark: themeManager.isDarkMode))
                                            .rotationEffect(.degrees(isRefreshing ? 360 : 0))
                                            .animation(.linear(duration: 1.0).repeatForever(autoreverses: false), value: isRefreshing)
                                            .padding(12)
                                            .background(
                                                Circle()
                                                    .fill(AppColors.accent(for: themeManager.currentTheme, isDark: themeManager.isDarkMode).opacity(0.1))
                                                    .overlay(
                                                        Circle()
                                                            .stroke(AppColors.accent(for: themeManager.currentTheme, isDark: themeManager.isDarkMode).opacity(0.3), lineWidth: 1)
                                                    )
                                            )
                                    }
                                    .disabled(isRefreshing)
                                }
                            }
                            
                            // Live Stats Bar
                            if showingStats {
                                LiveStatsBar(
                                    cameraManager: cameraManager,
                                    theme: themeManager.currentTheme,
                                    isDark: themeManager.isDarkMode
                                )
                                .transition(.asymmetric(
                                    insertion: .opacity.combined(with: .move(edge: .top)),
                                    removal: .opacity.combined(with: .move(edge: .top))
                                ))
                            }
                        }
                        .padding(.horizontal, 20)
                        .padding(.top, 20)
                        
                        // Dynamic Camera Grid
                        Group {
                            switch cameraGridLayout {
                            case .grid:
                                LazyVGrid(columns: [
                                    GridItem(.flexible()),
                                    GridItem(.flexible())
                                ], spacing: 16) {
                                    ForEach(["cam1", "cam2"], id: \.self) { cameraId in
                                        EnhancedCameraCard(
                                            cameraId: cameraId,
                                            cameraManager: cameraManager,
                                            isSelected: selectedCamera == cameraId,
                                            onTap: {
                                                withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                                                    selectedCamera = cameraId
                                                    showingFullScreen = true
                                                }
                                            }
                                        )
                                        .transition(.asymmetric(
                                            insertion: .scale.combined(with: .opacity),
                                            removal: .scale.combined(with: .opacity)
                                        ))
                                    }
                                }
                            case .list:
                                LazyVStack(spacing: 12) {
                                    ForEach(["cam1", "cam2"], id: \.self) { cameraId in
                                        ListCameraCard(
                                            cameraId: cameraId,
                                            cameraManager: cameraManager,
                                            isSelected: selectedCamera == cameraId,
                                            onTap: {
                                                withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                                                    selectedCamera = cameraId
                                                    showingFullScreen = true
                                                }
                                            }
                                        )
                                        .transition(.asymmetric(
                                            insertion: .move(edge: .trailing).combined(with: .opacity),
                                            removal: .move(edge: .trailing).combined(with: .opacity)
                                        ))
                                    }
                                }
                            case .single:
                                LazyVStack(spacing: 16) {
                                    ForEach(["cam1", "cam2"], id: \.self) { cameraId in
                                        SingleCameraCard(
                                            cameraId: cameraId,
                                            cameraManager: cameraManager,
                                            isSelected: selectedCamera == cameraId,
                                            onTap: {
                                                withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                                                    selectedCamera = cameraId
                                                    showingFullScreen = true
                                                }
                                            }
                                        )
                                        .transition(.asymmetric(
                                            insertion: .scale.combined(with: .opacity),
                                            removal: .scale.combined(with: .opacity)
                                        ))
                                    }
                                }
                            }
                        }
                        .padding(.horizontal, 20)
                        .animation(.spring(response: 0.6, dampingFraction: 0.8), value: cameraGridLayout)
                    }
                    .padding(.bottom, 100)
                }
                
                // Enhanced iOS 18 Floating Action Buttons
                VStack {
                    Spacer()
                    HStack {
                        Spacer()
                        VStack(spacing: 16) {
                            // Quick Refresh Button
                            FloatingActionButton(
                                theme: themeManager.currentTheme,
                                isDark: themeManager.isDarkMode,
                                action: {
                                    refreshCameras()
                                },
                                icon: "arrow.clockwise",
                                isLoading: isRefreshing
                            )
                            
                            // Layout Toggle Button
                            FloatingActionButton(
                                theme: themeManager.currentTheme,
                                isDark: themeManager.isDarkMode,
                                action: {
                                    withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                                        cycleLayout()
                                    }
                                },
                                icon: cameraGridLayout.icon
                            )
                            
                            // Full Screen Button
                            FloatingActionButton(
                                theme: themeManager.currentTheme,
                                isDark: themeManager.isDarkMode,
                                action: {
                                    withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                                        selectedCamera = "cam1"
                                        showingFullScreen.toggle()
                                    }
                                },
                                icon: "arrow.up.left.and.arrow.down.right"
                            )
                        }
                        .padding(.trailing, 20)
                        .padding(.bottom, 100)
                    }
                }
            }
            .navigationBarHidden(true)
        }
        .sheet(isPresented: $showingFullScreen) {
            if let cameraId = selectedCamera {
                FullScreenCameraView(
                    cameraId: cameraId,
                    cameraManager: cameraManager
                )
            }
        }
        .onAppear {
            cameraManager.startAllCameras()
        }
    }
    
    // MARK: - Helper Functions
    private func refreshCameras() {
        withAnimation(.easeInOut(duration: 0.3)) {
            refreshAnimation = true
            isRefreshing = true
        }
        
        cameraManager.refreshAllCameras()
        lastRefreshTime = Date()
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            withAnimation(.easeInOut(duration: 0.3)) {
                refreshAnimation = false
                isRefreshing = false
            }
        }
    }
    
    private func cycleLayout() {
        let layouts = CameraGridLayout.allCases
        if let currentIndex = layouts.firstIndex(of: cameraGridLayout) {
            let nextIndex = (currentIndex + 1) % layouts.count
            cameraGridLayout = layouts[nextIndex]
        }
    }
}

// MARK: - Live Stats Bar
struct LiveStatsBar: View {
    @ObservedObject var cameraManager: CameraManager
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    
    var body: some View {
        ThemeGlassCard(theme: theme, isDark: isDark) {
            HStack(spacing: 20) {
                // Total Cameras
                StatItem(
                    icon: "video.fill",
                    title: "Cameras",
                    value: "\(cameraManager.cameraStatus.count)",
                    color: .green
                )
                
                // Online Cameras
                StatItem(
                    icon: "checkmark.circle.fill",
                    title: "Online",
                    value: "\(cameraManager.cameraStatus.values.filter { $0 }.count)",
                    color: .green
                )
                
                // Offline Cameras
                StatItem(
                    icon: "xmark.circle.fill",
                    title: "Offline",
                    value: "\(cameraManager.cameraStatus.values.filter { !$0 }.count)",
                    color: .red
                )
                
                Spacer()
                
                // Last Update
                VStack(alignment: .trailing, spacing: 2) {
                    Text("Last Update")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundColor(AppColors.secondary(for: theme, isDark: isDark))
                    
                    Text(Date().formatted(date: .omitted, time: .shortened))
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundColor(AppColors.primary(for: theme, isDark: isDark))
                }
            }
        }
        .padding(.horizontal, 20)
    }
}

struct StatItem: View {
    let icon: String
    let title: String
    let value: String
    let color: Color
    
    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: icon)
                .font(.system(size: 14, weight: .semibold))
                .foregroundColor(color)
            
            VStack(alignment: .leading, spacing: 1) {
                Text(value)
                    .font(.system(size: 16, weight: .bold))
                    .foregroundColor(.primary)
                
                Text(title)
                    .font(.system(size: 10, weight: .medium))
                    .foregroundColor(.secondary)
            }
        }
    }
}

// MARK: - Enhanced Camera Card
struct EnhancedCameraCard: View {
    let cameraId: String
    @ObservedObject var cameraManager: CameraManager
    let isSelected: Bool
    let onTap: () -> Void
    @State private var isHovered = false
    
    private func getCameraDisplayName(_ cameraId: String) -> String {
        switch cameraId {
        case "cam1": return "ESP32 Cam"
        case "cam2": return "Pi Zero Cam"
        default: return cameraId.uppercased()
        }
    }
    
    private func getCameraAspectRatio(_ cameraId: String) -> CGFloat {
        if let image = cameraManager.cameraImages[cameraId] {
            let width = image.size.width
            let height = image.size.height
            return width / height
        }
        // Default to 16/9 if no image available
        return 16.0 / 9.0
    }
    
    var body: some View {
        VStack(spacing: 12) {
            // Enhanced Camera Preview
            ZStack {
                RoundedRectangle(cornerRadius: 20)
                    .fill(.ultraThinMaterial)
                    .aspectRatio(getCameraAspectRatio(cameraId), contentMode: .fit)
                    .overlay(
                        Group {
                            if let image = cameraManager.cameraImages[cameraId] {
                                Image(uiImage: image)
                                    .resizable()
                                    .aspectRatio(contentMode: .fit)
                                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                                    .clipped()
                                    .scaleEffect(isHovered ? 1.05 : 1.0)
                                    .animation(.easeInOut(duration: 0.3), value: isHovered)
                            } else {
                                VStack(spacing: 12) {
                                    ProgressView()
                                        .progressViewStyle(CircularProgressViewStyle(tint: .green))
                                        .scaleEffect(1.2)
                                    
                                    Text("Loading...")
                                        .font(.system(size: 14, weight: .medium))
                                        .foregroundColor(.secondary)
                                }
                            }
                        }
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 20)
                            .stroke(
                                isSelected ? .green : .clear,
                                lineWidth: 3
                            )
                    )
                    .overlay(
                        // Shimmer effect for loading
                        Group {
                            if cameraManager.cameraImages[cameraId] == nil {
                                RoundedRectangle(cornerRadius: 20)
                                    .fill(
                                        LinearGradient(
                                            colors: [
                                                Color.white.opacity(0.1),
                                                Color.white.opacity(0.3),
                                                Color.white.opacity(0.1)
                                            ],
                                            startPoint: .leading,
                                            endPoint: .trailing
                                        )
                                    )
                                    .offset(x: -200)
                                    .animation(
                                        .linear(duration: 1.5)
                                        .repeatForever(autoreverses: false),
                                        value: cameraManager.cameraImages[cameraId] == nil
                                    )
                            }
                        }
                    )
                
                // Enhanced Status Overlay
                VStack {
                    HStack {
                        Spacer()
                        
                        // Status indicator with animation
                        HStack(spacing: 6) {
                            Circle()
                                .fill(cameraManager.cameraStatus[cameraId] == true ? .green : .red)
                                .frame(width: 6, height: 6)
                                .scaleEffect(cameraManager.cameraStatus[cameraId] == true ? 1.2 : 1.0)
                                .animation(.easeInOut(duration: 0.5).repeatForever(autoreverses: true), value: cameraManager.cameraStatus[cameraId] == true)
                            
                            Text(cameraManager.cameraStatus[cameraId] == true ? "LIVE" : "OFFLINE")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(cameraManager.cameraStatus[cameraId] == true ? .green : .red)
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(.black.opacity(0.7))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 8)
                                        .stroke(.white.opacity(0.2), lineWidth: 1)
                                )
                        )
                    }
                    
                    Spacer()
                    
                    // Camera info indicator
                    HStack {
                        HStack(spacing: 4) {
                            Image(systemName: "video.fill")
                                .font(.system(size: 8))
                                .foregroundColor(.white)
                            
                            Text("LIVE")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(.white)
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(.black.opacity(0.7))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 8)
                                        .stroke(.white.opacity(0.2), lineWidth: 1)
                                )
                        )
                        
                        Spacer()
                    }
                }
                .padding(12)
            }
            
            // Enhanced Camera Info
            VStack(spacing: 6) {
                Text(getCameraDisplayName(cameraId))
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundColor(.primary)
                    .multilineTextAlignment(.center)
                
                HStack(spacing: 4) {
                    Image(systemName: "video.fill")
                        .font(.system(size: 10))
                        .foregroundColor(.green)
                    
                    Text("Surveillance Camera")
                        .font(.system(size: 11, weight: .medium))
                        .foregroundColor(.secondary)
                }
            }
        }
        .onTapGesture {
            onTap()
        }
        .scaleEffect(isSelected ? 1.02 : (isHovered ? 1.01 : 1.0))
        .animation(.spring(response: 0.4, dampingFraction: 0.8), value: isSelected)
        .animation(.easeInOut(duration: 0.2), value: isHovered)
        .onHover { hovering in
            isHovered = hovering
        }
    }
}

// MARK: - List Camera Card
struct ListCameraCard: View {
    let cameraId: String
    @ObservedObject var cameraManager: CameraManager
    let isSelected: Bool
    let onTap: () -> Void
    
    private func getCameraDisplayName(_ cameraId: String) -> String {
        switch cameraId {
        case "cam1": return "ESP32 Cam"
        case "cam2": return "Pi Zero Cam"
        default: return cameraId.uppercased()
        }
    }
    
    private func getCameraAspectRatio(_ cameraId: String) -> CGFloat {
        if let image = cameraManager.cameraImages[cameraId] {
            let width = image.size.width
            let height = image.size.height
            return width / height
        }
        // Default to 16/9 if no image available
        return 16.0 / 9.0
    }
    
    var body: some View {
        HStack(spacing: 16) {
            // Camera Preview
            ZStack {
                RoundedRectangle(cornerRadius: 12)
                    .fill(.ultraThinMaterial)
                    .frame(width: 120, height: 80)
                    .aspectRatio(getCameraAspectRatio(cameraId), contentMode: .fit)
                    .overlay(
                        Group {
                            if let image = cameraManager.cameraImages[cameraId] {
                                Image(uiImage: image)
                                    .resizable()
                                    .aspectRatio(contentMode: .fit)
                                    .frame(width: 120, height: 80)
                                    .clipped()
                            } else {
                                ProgressView()
                                    .progressViewStyle(CircularProgressViewStyle(tint: .green))
                            }
                        }
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(isSelected ? .green : .clear, lineWidth: 2)
                    )
                
                // Status indicator
                VStack {
                    HStack {
                        Spacer()
                        Circle()
                            .fill(cameraManager.cameraStatus[cameraId] == true ? .green : .red)
                            .frame(width: 8, height: 8)
                    }
                    Spacer()
                }
                .padding(8)
            }
            
            // Camera Info
            VStack(alignment: .leading, spacing: 6) {
                Text(getCameraDisplayName(cameraId))
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(.primary)
                
                HStack(spacing: 10) {
                    HStack(spacing: 3) {
                        Image(systemName: "video.fill")
                            .font(.system(size: 10))
                            .foregroundColor(.green)
                        
                        Text("Surveillance")
                            .font(.system(size: 11, weight: .medium))
                            .foregroundColor(.secondary)
                    }
                    
                    HStack(spacing: 3) {
                        Image(systemName: "video.fill")
                            .font(.system(size: 10))
                            .foregroundColor(.green)
                        
                        Text("Live Feed")
                            .font(.system(size: 11, weight: .medium))
                            .foregroundColor(.secondary)
                    }
                }
            }
            
            Spacer()
            
            // Status
            VStack(alignment: .trailing, spacing: 3) {
                Text(cameraManager.cameraStatus[cameraId] == true ? "LIVE" : "OFFLINE")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundColor(cameraManager.cameraStatus[cameraId] == true ? .green : .red)
                
                Text("Tap to view")
                    .font(.system(size: 9, weight: .medium))
                    .foregroundColor(.secondary)
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(.ultraThinMaterial)
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(isSelected ? .green : .clear, lineWidth: 2)
                )
        )
        .onTapGesture {
            onTap()
        }
        .scaleEffect(isSelected ? 1.02 : 1.0)
        .animation(.spring(response: 0.4, dampingFraction: 0.8), value: isSelected)
    }
}

// MARK: - Single Camera Card
struct SingleCameraCard: View {
    let cameraId: String
    @ObservedObject var cameraManager: CameraManager
    let isSelected: Bool
    let onTap: () -> Void
    
    private func getCameraDisplayName(_ cameraId: String) -> String {
        switch cameraId {
        case "cam1": return "ESP32 Cam"
        case "cam2": return "Pi Zero Cam"
        default: return cameraId.uppercased()
        }
    }
    
    private func getCameraAspectRatio(_ cameraId: String) -> CGFloat {
        if let image = cameraManager.cameraImages[cameraId] {
            let width = image.size.width
            let height = image.size.height
            return width / height
        }
        // Default to 16/9 if no image available
        return 16.0 / 9.0
    }
    
    var body: some View {
        VStack(spacing: 16) {
            // Large Camera Preview
            ZStack {
                RoundedRectangle(cornerRadius: 24)
                    .fill(.ultraThinMaterial)
                    .aspectRatio(getCameraAspectRatio(cameraId), contentMode: .fit)
                    .overlay(
                        Group {
                            if let image = cameraManager.cameraImages[cameraId] {
                                Image(uiImage: image)
                                    .resizable()
                                    .aspectRatio(contentMode: .fit)
                                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                                    .clipped()
                            } else {
                                VStack(spacing: 20) {
                                    ProgressView()
                                        .progressViewStyle(CircularProgressViewStyle(tint: .green))
                                        .scaleEffect(1.5)
                                    
                                    Text("Loading camera feed...")
                                        .font(.system(size: 16, weight: .medium))
                                        .foregroundColor(.secondary)
                                }
                            }
                        }
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 24)
                            .stroke(isSelected ? .green : .clear, lineWidth: 3)
                    )
                
                // Status overlay
                VStack {
                    HStack {
                        Spacer()
                        
                        HStack(spacing: 8) {
                            Circle()
                                .fill(cameraManager.cameraStatus[cameraId] == true ? .green : .red)
                                .frame(width: 10, height: 10)
                            
                            Text(cameraManager.cameraStatus[cameraId] == true ? "LIVE" : "OFFLINE")
                                .font(.system(size: 14, weight: .bold))
                                .foregroundColor(cameraManager.cameraStatus[cameraId] == true ? .green : .red)
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(
                            RoundedRectangle(cornerRadius: 10)
                                .fill(.black.opacity(0.7))
                        )
                    }
                    
                    Spacer()
                }
                .padding(20)
            }
            
            // Camera Info
            HStack {
                VStack(alignment: .leading, spacing: 3) {
                    Text(getCameraDisplayName(cameraId))
                        .font(.system(size: 18, weight: .bold))
                        .foregroundColor(.primary)
                    
                    Text("Surveillance Camera • Live Feed")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                Button("View Full Screen") {
                    onTap()
                }
                .buttonStyle(LiquidGlassButtonStyle(theme: .dark, isDark: true))
                .font(.system(size: 13, weight: .semibold))
            }
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 24)
                .fill(.ultraThinMaterial)
                .overlay(
                    RoundedRectangle(cornerRadius: 24)
                        .stroke(isSelected ? .green : .clear, lineWidth: 3)
                )
        )
        .onTapGesture {
            onTap()
        }
        .scaleEffect(isSelected ? 1.02 : 1.0)
        .animation(.spring(response: 0.4, dampingFraction: 0.8), value: isSelected)
    }
}

struct CameraCard: View {
    let cameraId: String
    @ObservedObject var cameraManager: CameraManager
    let isSelected: Bool
    let onTap: () -> Void
    
    private func getCameraDisplayName(_ cameraId: String) -> String {
        switch cameraId {
        case "cam1":
            return "ESP32 Cam"
        case "cam2":
            return "Pi Zero Cam"
        default:
            return cameraId.uppercased()
        }
    }
    
    private func getCameraAspectRatio(_ cameraId: String) -> CGFloat {
        if let image = cameraManager.cameraImages[cameraId] {
            let width = image.size.width
            let height = image.size.height
            return width / height
        }
        // Default to 16/9 if no image available
        return 16.0 / 9.0
    }
    
    var body: some View {
        VStack(spacing: 12) {
            // Camera Preview
            ZStack {
                RoundedRectangle(cornerRadius: 16)
                    .fill(.ultraThinMaterial)
                    .aspectRatio(getCameraAspectRatio(cameraId), contentMode: .fit)
                    .overlay(
                        Group {
                            if let image = cameraManager.cameraImages[cameraId] {
                                Image(uiImage: image)
                                    .resizable()
                                    .aspectRatio(contentMode: .fit)
                                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                                    .clipped()
                            } else {
                                VStack(spacing: 12) {
                                    ProgressView()
                                        .progressViewStyle(CircularProgressViewStyle(tint: .green))
                                        .scaleEffect(1.2)
                                    
                                    Text("Loading...")
                                        .font(.system(size: 14, weight: .medium))
                                        .foregroundColor(.secondary)
                                }
                            }
                        }
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(isSelected ? .green : .clear, lineWidth: 3)
                    )
                
                // Status overlay
                VStack {
                    HStack {
                        Spacer()
                        
                        // Status indicator
                        HStack(spacing: 6) {
                            Circle()
                                .fill(cameraManager.cameraStatus[cameraId] == true ? .green : .red)
                                .frame(width: 6, height: 6)
                            
                            Text(cameraManager.cameraStatus[cameraId] == true ? "LIVE" : "OFFLINE")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(cameraManager.cameraStatus[cameraId] == true ? .green : .red)
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(
                            RoundedRectangle(cornerRadius: 6)
                                .fill(.black.opacity(0.7))
                        )
                    }
                    
                    Spacer()
                    
                    // Live indicator
                    HStack {
                        HStack(spacing: 4) {
                            Image(systemName: "video.fill")
                                .font(.system(size: 8))
                                .foregroundColor(.white)
                            
                            Text("LIVE")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(.white)
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(
                            RoundedRectangle(cornerRadius: 6)
                                .fill(.black.opacity(0.7))
                        )
                        
                        Spacer()
                    }
                }
                .padding(8)
            }
            
            // Camera Info
            VStack(spacing: 8) {
                Text(getCameraDisplayName(cameraId))
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(.primary)
                
                HStack(spacing: 4) {
                    Image(systemName: "video.fill")
                        .font(.system(size: 12))
                        .foregroundColor(.green)
                    
                    Text("Surveillance Camera")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(.secondary)
                }
            }
        }
        .onTapGesture {
            onTap()
        }
        .scaleEffect(isSelected ? 1.02 : 1.0)
        .animation(.easeInOut(duration: 0.2), value: isSelected)
    }
}

struct FullScreenCameraView: View {
    let cameraId: String
    @ObservedObject var cameraManager: CameraManager
    @Environment(\.dismiss) private var dismiss
    @State private var isControlsVisible = true
    @State private var controlsTimer: Timer?
    @State private var isSendingPan = false
    
    private func getCameraDisplayName(_ cameraId: String) -> String {
        switch cameraId {
        case "cam1": return "ESP32 Cam"
        case "cam2": return "Pi Zero Cam"
        default: return cameraId.uppercased()
        }
    }
    
    private func getCameraAspectRatio(_ cameraId: String) -> CGFloat {
        if let image = cameraManager.cameraImages[cameraId] {
            let width = image.size.width
            let height = image.size.height
            return width / height
        }
        // Default to 16/9 if no image available
        return 16.0 / 9.0
    }
    
    var body: some View {
        NavigationView {
            ZStack {
                // Background
                Color.black.ignoresSafeArea()
                
                VStack(spacing: 0) {
                    // Enhanced Camera feed
                    ZStack {
                        if let image = cameraManager.cameraImages[cameraId] {
                            Image(uiImage: image)
                                .resizable()
                                .aspectRatio(getCameraAspectRatio(cameraId), contentMode: .fit)
                                .frame(maxWidth: .infinity, maxHeight: .infinity)
                                .clipped()
                                .onTapGesture {
                                    toggleControls()
                                }
                        } else {
                            VStack(spacing: 20) {
                                ProgressView()
                                    .progressViewStyle(CircularProgressViewStyle(tint: .green))
                                    .scaleEffect(1.5)
                                
                                Text("Loading camera feed...")
                                    .font(.system(size: 16, weight: .medium))
                                    .foregroundColor(.secondary)
                            }
                        }
                        
                        // Enhanced Status overlay
                        VStack {
                            HStack {
                                Spacer()
                                
                                // Status indicator with pulse animation
                                HStack(spacing: 8) {
                                    Circle()
                                        .fill(cameraManager.cameraStatus[cameraId] == true ? .green : .red)
                                        .frame(width: 10, height: 10)
                                        .scaleEffect(cameraManager.cameraStatus[cameraId] == true ? 1.2 : 1.0)
                                        .animation(.easeInOut(duration: 0.5).repeatForever(autoreverses: true), value: cameraManager.cameraStatus[cameraId] == true)
                                    
                                    Text(cameraManager.cameraStatus[cameraId] == true ? "LIVE" : "OFFLINE")
                                        .font(.system(size: 14, weight: .bold))
                                        .foregroundColor(cameraManager.cameraStatus[cameraId] == true ? .green : .red)
                                }
                                .padding(.horizontal, 16)
                                .padding(.vertical, 8)
                                .background(
                                    RoundedRectangle(cornerRadius: 12)
                                        .fill(.black.opacity(0.8))
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 12)
                                                .stroke(.white.opacity(0.2), lineWidth: 1)
                                        )
                                )
                            }
                            
                            Spacer()
                            
                            // Bottom controls
                            if isControlsVisible {
                                HStack {
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(getCameraDisplayName(cameraId))
                                            .font(.system(size: 18, weight: .bold))
                                            .foregroundColor(.white)
                                        
                                        Text("Surveillance Camera • Live Feed")
                                            .font(.system(size: 13, weight: .medium))
                                            .foregroundColor(.white.opacity(0.8))
                                    }
                                    
                                    Spacer()
                                    
                                    // Pan controls for cam2 only (compact)
                                    if cameraId == "cam2" {
                                        HStack(spacing: 6) {
                                            Button(action: { Task { await pan(.left) } }) {
                                                Image(systemName: "arrow.left")
                                            }
                                            .buttonStyle(.bordered)
                                            .tint(.white)
                                            .controlSize(.small)
                                            .disabled(isSendingPan)
                                            
                                            Button(action: { Task { await pan(.auto) } }) {
                                                Image(systemName: "arrow.triangle.2.circlepath")
                                            }
                                            .buttonStyle(.bordered)
                                            .tint(.white)
                                            .controlSize(.small)
                                            .disabled(isSendingPan)
                                            
                                            Button(action: { Task { await pan(.right) } }) {
                                                Image(systemName: "arrow.right")
                                            }
                                            .buttonStyle(.bordered)
                                            .tint(.white)
                                            .controlSize(.small)
                                            .disabled(isSendingPan)
                                        }
                                        .foregroundColor(.white)
                                    }
                                    
                                    Button {
                                        cameraManager.refreshAllCameras()
                                    } label: {
                                        Image(systemName: "arrow.clockwise")
                                    }
                                    .buttonStyle(.bordered)
                                    .tint(.white)
                                    .controlSize(.small)
                                }
                                .padding(12)
                                .background(
                                    RoundedRectangle(cornerRadius: 16)
                                        .fill(.black.opacity(0.5))
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 16)
                                                .stroke(.white.opacity(0.2), lineWidth: 1)
                                        )
                                )
                                .padding(.horizontal, 12)
                                .transition(.asymmetric(
                                    insertion: .opacity.combined(with: .move(edge: .bottom)),
                                    removal: .opacity.combined(with: .move(edge: .bottom))
                                ))
                            }
                        }
                        .padding(20)
                    }
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Done") {
                        dismiss()
                    }
                    .foregroundColor(.white)
                    .font(.system(size: 15, weight: .semibold))
                }
                
                ToolbarItem(placement: .principal) {
                    Text(getCameraDisplayName(cameraId))
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundColor(.white)
                }
                
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: {
                        cameraManager.refreshAllCameras()
                    }) {
                        Image(systemName: "arrow.clockwise")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundColor(.white)
                    }
                }
            }
        }
        .preferredColorScheme(.dark)
        .onAppear {
            startControlsTimer()
        }
        .onDisappear {
            stopControlsTimer()
        }
    }
    
    private func toggleControls() {
        withAnimation(.easeInOut(duration: 0.3)) {
            isControlsVisible.toggle()
        }
        
        if isControlsVisible {
            startControlsTimer()
        } else {
            stopControlsTimer()
        }
    }
    
    private func startControlsTimer() {
        stopControlsTimer()
        controlsTimer = Timer.scheduledTimer(withTimeInterval: 3.0, repeats: false) { _ in
            withAnimation(.easeInOut(duration: 0.3)) {
                isControlsVisible = false
            }
        }
    }
    
    private func stopControlsTimer() {
        controlsTimer?.invalidate()
        controlsTimer = nil
    }
    
    private enum PanDir { case left, right, auto }
    private func pan(_ dir: PanDir) async {
        isSendingPan = true
        defer { isSendingPan = false }
        do {
            switch dir {
            case .left: try await APIService.shared.panCamLeft()
            case .right: try await APIService.shared.panCamRight()
            case .auto: try await APIService.shared.panCamAuto()
            }
        } catch {
            // no-op UI failure for now
        }
    }
}

#Preview {
    CameraView()
        .environmentObject(CameraManager())
}