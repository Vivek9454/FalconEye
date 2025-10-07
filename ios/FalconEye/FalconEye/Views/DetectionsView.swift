import SwiftUI

struct DetectionsView: View {
    @EnvironmentObject var apiService: APIService
    @EnvironmentObject var themeManager: ThemeManager
    @State private var detections: [Detection] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var refreshTimer: Timer?
    
    var body: some View {
        NavigationView {
            GeometryReader { geometry in
                ZStack {
                    AppColors.background(for: themeManager.currentTheme, isDark: themeManager.isDarkMode)
                        .ignoresSafeArea()
                    
                    if isLoading && detections.isEmpty {
                        VStack(spacing: 20) {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: AppColors.accent(for: themeManager.currentTheme, isDark: themeManager.isDarkMode)))
                                .scaleEffect(1.2)
                            
                            Text("Loading detections...")
                                .font(.system(size: 16, weight: .medium))
                                .foregroundColor(AppColors.secondary(for: themeManager.currentTheme, isDark: themeManager.isDarkMode))
                        }
                    } else if let errorMessage = errorMessage {
                        VStack(spacing: 20) {
                            Image(systemName: "exclamationmark.triangle")
                                .font(.system(size: 50))
                                .foregroundColor(.red.opacity(0.6))
                            
                            Text("Error Loading Detections")
                                .font(.system(size: 20, weight: .semibold))
                                .foregroundColor(AppColors.primary(for: themeManager.currentTheme, isDark: themeManager.isDarkMode))
                            
                            Text(errorMessage)
                                .font(.system(size: 14))
                                .foregroundColor(AppColors.secondary(for: themeManager.currentTheme, isDark: themeManager.isDarkMode))
                                .multilineTextAlignment(.center)
                            
                            Button("Retry") {
                                loadDetections()
                            }
                            .buttonStyle(LiquidGlassButtonStyle(theme: themeManager.currentTheme, isDark: themeManager.isDarkMode))
                        }
                        .padding()
                    } else if detections.isEmpty {
                        VStack(spacing: 20) {
                            Image(systemName: "eye.slash")
                                .font(.system(size: 50))
                                .foregroundColor(.secondary.opacity(0.6))
                            
                            Text("No Recent Detections")
                                .font(.system(size: 20, weight: .semibold))
                            
                            Text("Security detections will appear here when objects are detected by your cameras.")
                                .font(.system(size: 14))
                                .foregroundColor(.secondary)
                                .multilineTextAlignment(.center)
                        }
                        .padding()
                    } else {
                        ScrollView {
                            LazyVStack(spacing: 12) {
                                ForEach(detections) { detection in
                                    DetectionCard(detection: detection)
                                }
                            }
                            .padding(.horizontal, 20)
                            .padding(.top, 20)
                        }
                    }
                }
            }
            .navigationTitle("Detections")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: loadDetections) {
                        Image(systemName: "arrow.clockwise")
                            .foregroundColor(.green)
                    }
                }
            }
        }
        .onAppear {
            loadDetections()
            startRefreshTimer()
        }
        .onDisappear {
            stopRefreshTimer()
        }
    }
    
    private func loadDetections() {
        isLoading = true
        errorMessage = nil
        
        Task {
            do {
                let newDetections = try await apiService.getRecentDetections()
                
                DispatchQueue.main.async {
                    self.detections = newDetections
                    self.isLoading = false
                }
            } catch {
                DispatchQueue.main.async {
                    self.errorMessage = error.localizedDescription
                    self.isLoading = false
                }
            }
        }
    }
    
    private func startRefreshTimer() {
        refreshTimer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { _ in
            loadDetections()
        }
    }
    
    private func stopRefreshTimer() {
        refreshTimer?.invalidate()
        refreshTimer = nil
    }
}

struct DetectionCard: View {
    let detection: Detection
    
    var body: some View {
        VStack(spacing: 12) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(formatTimestamp(detection.timestamp))
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundColor(.primary)
                    
                    Text("Camera: \(detection.camera.uppercased())")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                // Confidence Indicator
                HStack(spacing: 4) {
                    Circle()
                        .fill(confidenceColor(detection.confidence))
                        .frame(width: 8, height: 8)
                    
                    Text("\(Int(detection.confidence * 100))%")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(confidenceColor(detection.confidence))
                }
            }
            
            // Detected Objects
            if !detection.objects.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Detected Objects")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundColor(.primary)
                    
                    LazyVGrid(columns: [
                        GridItem(.flexible()),
                        GridItem(.flexible()),
                        GridItem(.flexible())
                    ], spacing: 8) {
                        ForEach(detection.objects, id: \.self) { object in
                            ObjectTag(object: object)
                        }
                    }
                }
            }
            
            // Image Preview (if available)
            if let imageURL = detection.image_url {
                AsyncImage(url: URL(string: imageURL)) { image in
                    image
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                } placeholder: {
                    RoundedRectangle(cornerRadius: 8)
                        .fill(.ultraThinMaterial)
                        .overlay(
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: .green))
                        )
                }
                .frame(height: 120)
                .clipped()
                .clipShape(RoundedRectangle(cornerRadius: 8))
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(.ultraThinMaterial)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(confidenceColor(detection.confidence).opacity(0.3), lineWidth: 1)
                )
        )
    }
    
    private func formatTimestamp(_ timestamp: String) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"
        
        if let date = formatter.date(from: timestamp) {
            let displayFormatter = DateFormatter()
            displayFormatter.dateStyle = .short
            displayFormatter.timeStyle = .short
            return displayFormatter.string(from: date)
        }
        
        return timestamp
    }
    
    private func confidenceColor(_ confidence: Double) -> Color {
        if confidence >= 0.8 {
            return .green
        } else if confidence >= 0.6 {
            return .orange
        } else {
            return .red
        }
    }
}

struct ObjectTag: View {
    let object: String
    
    var body: some View {
        Text(object.capitalized)
            .font(.system(size: 12, weight: .medium))
            .foregroundColor(.white)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: 16)
                    .fill(objectColor(object))
            )
    }
    
    private func objectColor(_ object: String) -> Color {
        switch object.lowercased() {
        case "person":
            return .red
        case "car", "truck", "bus":
            return .blue
        case "bicycle", "motorcycle":
            return .orange
        case "dog", "cat":
            return .purple
        default:
            return .green
        }
    }
}

#Preview {
    DetectionsView()
        .environmentObject(APIService.shared)
}
