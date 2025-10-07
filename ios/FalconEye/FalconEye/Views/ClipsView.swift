import SwiftUI
import AVKit

struct ClipsView: View {
    @EnvironmentObject var apiService: APIService
    @EnvironmentObject var themeManager: ThemeManager
    @State private var clipsSummary: ClipsSummary?
    @State private var clips: [String: ClipMetadata] = [:]
    @State private var isLoading = false
    @State private var selectedDate: String?
    @State private var showingVideoPlayer = false
    @State private var selectedVideoURL: URL?
    @State private var errorMessage: String?
    @State private var showingDatePicker = false
    
    var body: some View {
        NavigationView {
            ZStack {
                // Background
                AppColors.background(for: themeManager.currentTheme, isDark: themeManager.isDarkMode)
                    .ignoresSafeArea()
                
                if isLoading {
                    VStack(spacing: 20) {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: AppColors.accent(for: themeManager.currentTheme, isDark: themeManager.isDarkMode)))
                            .scaleEffect(1.2)
                        
                        Text("Loading Security Clips...")
                            .font(.system(size: 16, weight: .medium))
                            .foregroundColor(AppColors.secondary(for: themeManager.currentTheme, isDark: themeManager.isDarkMode))
                    }
                } else if let errorMessage = errorMessage {
                    VStack(spacing: 20) {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.system(size: 50))
                            .foregroundColor(.red)
                        
                        Text("Error Loading Clips")
                            .font(.title2)
                            .fontWeight(.semibold)
                            .foregroundColor(AppColors.primary(for: themeManager.currentTheme, isDark: themeManager.isDarkMode))
                        
                        Text(errorMessage)
                            .font(.body)
                            .foregroundColor(AppColors.secondary(for: themeManager.currentTheme, isDark: themeManager.isDarkMode))
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, 40)
                        
                        Button("Retry") {
                            loadClips()
                        }
                        .buttonStyle(LiquidGlassButtonStyle(theme: themeManager.currentTheme, isDark: themeManager.isDarkMode))
                    }
                } else if clips.isEmpty {
                    // Empty state
                    VStack(spacing: 20) {
                        Image(systemName: "video.slash")
                            .font(.system(size: 60))
                            .foregroundColor(.secondary)
                        
                        Text("No Clips Found")
                            .font(.title2)
                            .fontWeight(.semibold)
                            .foregroundColor(.primary)
                        
                        Text("No security clips have been recorded yet. Clips will appear here when motion is detected.")
                            .font(.body)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, 40)
                        
                        Button(action: loadClips) {
                            HStack {
                                Image(systemName: "arrow.clockwise")
                                Text("Refresh")
                            }
                            .foregroundColor(.white)
                            .padding(.horizontal, 20)
                            .padding(.vertical, 12)
                            .background(
                                RoundedRectangle(cornerRadius: 12)
                                    .fill(.green)
                            )
                        }
                        .buttonStyle(GlassButtonStyle())
                    }
                } else {
                    ScrollView {
                        LazyVStack(spacing: 20) {
                            // Header
                            VStack(spacing: 16) {
                                HStack {
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text("Security Clips")
                                            .font(.system(size: 28, weight: .bold, design: .rounded))
                                            .foregroundStyle(
                                                LinearGradient(
                                                    colors: [.green, Color.green.opacity(0.8)],
                                                    startPoint: .topLeading,
                                                    endPoint: .bottomTrailing
                                                )
                                            )
                                        
                                        Text("Recorded surveillance footage")
                                            .font(.system(size: 16, weight: .medium))
                                            .foregroundColor(.secondary)
                                    }
                                    
                                    Spacer()
                                    
                                    // Date filter button
                                    Button(action: { showingDatePicker = true }) {
                                        HStack(spacing: 6) {
                                            Image(systemName: "calendar")
                                                .font(.system(size: 14, weight: .semibold))
                                            
                                            Text(selectedDate ?? "All Dates")
                                                .font(.system(size: 14, weight: .medium))
                                        }
                                        .foregroundColor(.green)
                                        .padding(.horizontal, 12)
                                        .padding(.vertical, 8)
                                        .background(
                                            RoundedRectangle(cornerRadius: 8)
                                                .fill(.green.opacity(0.1))
                                                .overlay(
                                                    RoundedRectangle(cornerRadius: 8)
                                                        .stroke(.green.opacity(0.3), lineWidth: 1)
                                                )
                                        )
                                    }
                                    
                                    // Refresh button
                                    Button(action: loadClips) {
                                        Image(systemName: "arrow.clockwise")
                                            .font(.system(size: 18, weight: .semibold))
                                            .foregroundColor(.green)
                                            .padding(12)
                                            .background(
                                                Circle()
                                                    .fill(.green.opacity(0.1))
                                                    .overlay(
                                                        Circle()
                                                            .stroke(.green.opacity(0.3), lineWidth: 1)
                                                    )
                                            )
                                    }
                                }

                            }
                            .padding(.horizontal, 20)
                            .padding(.top, 20)
                            
                            // Summary Cards
                            if let summary = clipsSummary {
                                ForEach(filteredDateSections(summary)) { dateInfo in
                                    ClipsDateSection(
                                        dateInfo: dateInfo,
                                        clips: clips,
                                        onVideoTap: { filename in
                                            playVideo(filename: filename)
                                        }
                                    )
                                }
                            }
                        }
                        .padding(.bottom, 100)
                    }
                }
            }
            .navigationBarHidden(true)
        }
        .sheet(isPresented: $showingVideoPlayer) {
            if let videoURL = selectedVideoURL {
                VideoPlayerView(videoURL: videoURL)
            } else {
                // Show loading state while video is being downloaded
                VStack(spacing: 20) {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .green))
                        .scaleEffect(1.5)
                    
                    Text("Loading video...")
                        .font(.system(size: 18, weight: .medium))
                        .foregroundColor(.primary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(Color.black)
            }
        }
        .sheet(isPresented: $showingDatePicker) {
            DatePickerSheet(
                availableDates: clipsSummary?.clips_by_date.map { $0.date } ?? [],
                selectedDate: $selectedDate
            )
        }
        .onAppear {
            loadClips()
        }
    }
    
    private func loadClips() {
        isLoading = true
        errorMessage = nil
        Task {
            do {
                async let summaryTask = apiService.getClipsSummary()
                async let clipsTask = apiService.getClips()
                
                let (summary, clipsData) = try await (summaryTask, clipsTask)
                
                DispatchQueue.main.async {
                    self.clipsSummary = summary
                    self.clips = clipsData
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
    
    private func filteredDateSections(_ summary: ClipsSummary) -> [ClipsByDate] {
        if let selectedDate = selectedDate {
            return summary.clips_by_date.filter { $0.date == selectedDate }
        }
        return summary.clips_by_date
    }
    
    private func playVideo(filename: String) {
        // Show loading state immediately
        showingVideoPlayer = true
        selectedVideoURL = nil
        
        Task {
            do {
                let videoData = try await apiService.downloadClip(filename: filename)
                
                // Create temporary file
                let tempURL = FileManager.default.temporaryDirectory
                    .appendingPathComponent(filename)
                
                try videoData.write(to: tempURL)
                
                DispatchQueue.main.async {
                    self.selectedVideoURL = tempURL
                }
            } catch {
                DispatchQueue.main.async {
                    self.showingVideoPlayer = false
                    self.errorMessage = "Failed to load video: \(error.localizedDescription)"
                }
            }
        }
    }
}

struct ClipsDateSection: View {
    let dateInfo: ClipsByDate
    let clips: [String: ClipMetadata]
    let onVideoTap: (String) -> Void
    @State private var isExpanded: Bool = true
    
    private var dateClips: [ClipMetadata] {
        clips.values.filter { clip in
            // Extract just the date part from the timestamp
            let datePart = String(clip.timestamp.prefix(10)) // Get "2025-09-11" part
            return datePart == dateInfo.date
        }.sorted { $0.timestamp > $1.timestamp }
    }
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            // Date Header
            Button(action: { isExpanded.toggle() }) {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(formatDate(dateInfo.date))
                            .font(.system(size: 18, weight: .semibold))
                            .foregroundColor(.primary)
                        
                        Text("\(dateInfo.count) clips • \(dateInfo.objects.joined(separator: ", "))")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(.secondary)
                    }
                    
                    Spacer()
                    
                    Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(.secondary)
                }
                .padding(.horizontal, 20)
                .padding(.vertical, 16)
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(.ultraThinMaterial)
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(.white.opacity(0.1), lineWidth: 1)
                        )
                )
            }
            .buttonStyle(.plain)
            
            // Clips Grid
            if isExpanded {
                LazyVGrid(columns: [
                    GridItem(.flexible()),
                    GridItem(.flexible())
                ], spacing: 16) {
                    ForEach(dateClips, id: \.filename) { clip in
                        ClipCard(
                            clip: clip,
                            onTap: {
                                onVideoTap(clip.filename)
                            }
                        )
                    }
                }
                .padding(.horizontal, 20)
            }
        }
    }
    
    private func formatDate(_ dateString: String) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        
        if let date = formatter.date(from: dateString) {
            let displayFormatter = DateFormatter()
            displayFormatter.dateFormat = "EEEE, MMM d, yyyy"  // "Monday, Sep 15, 2025"
            return displayFormatter.string(from: date)
        }
        
        return dateString
    }
}

struct ClipCard: View {
    let clip: ClipMetadata
    let onTap: () -> Void
    @State private var isPressed = false
    
    var body: some View {
        VStack(spacing: 12) {
            // Video Thumbnail
            ZStack {
                RoundedRectangle(cornerRadius: 12)
                    .fill(.ultraThinMaterial)
                    .aspectRatio(16/9, contentMode: .fit)
                
                VStack(spacing: 8) {
                    Image(systemName: "play.circle.fill")
                        .font(.system(size: 40))
                        .foregroundColor(.green)
                    
                    Text(formatDuration(clip.duration))
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(.white)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(
                            RoundedRectangle(cornerRadius: 6)
                                .fill(.black.opacity(0.7))
                        )
                }
            }
            
            // Clip Info
            VStack(alignment: .leading, spacing: 8) {
                // Camera and Time
                HStack {
                    Text(getCameraDisplayName(clip.camera ?? "unknown"))
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundColor(.green)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(
                            RoundedRectangle(cornerRadius: 4)
                                .fill(.green.opacity(0.1))
                        )
                    
                    Spacer()
                    
                    Text(formatTime(clip.timestamp))
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(.secondary)
                }
                
                // Tags
                if !clip.tags.isEmpty {
                    Text(clip.tags.joined(separator: ", "))
                        .font(.system(size: 11, weight: .medium))
                        .foregroundColor(.secondary)
                        .lineLimit(2)
                }
                
                // File size
                Text(formatFileSize(clip.size ?? 0))
                    .font(.system(size: 10, weight: .regular))
                    .foregroundColor(.secondary)
            }

        }
        .scaleEffect(isPressed ? 0.95 : 1.0)
        .animation(.easeInOut(duration: 0.1), value: isPressed)
        .onTapGesture {
            // Add haptic feedback for better user experience
            let impactFeedback = UIImpactFeedbackGenerator(style: .medium)
            impactFeedback.impactOccurred()
            
            onTap()
        }
        .onLongPressGesture(minimumDuration: 0, maximumDistance: .infinity, pressing: { pressing in
            isPressed = pressing
        }, perform: {})
    }
    
    private func formatDuration(_ duration: Double) -> String {
        let minutes = Int(duration) / 60
        let seconds = Int(duration) % 60
        return String(format: "%d:%02d", minutes, seconds)
    }
    
    private func formatTime(_ timestamp: String) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"
        
        if let date = formatter.date(from: timestamp) {
            let displayFormatter = DateFormatter()
            displayFormatter.dateFormat = "MMM d, h:mm a"  // 12-hour format with AM/PM
            return displayFormatter.string(from: date)
        }
        
        // Fallback: try to extract time from the original format
        if timestamp.contains("T") {
            let components = timestamp.components(separatedBy: "T")
            if components.count > 1 {
                let timePart = components[1].components(separatedBy: ".")[0]
                // Convert 24-hour to 12-hour format
                let timeFormatter = DateFormatter()
                timeFormatter.dateFormat = "HH:mm:ss"
                if let timeDate = timeFormatter.date(from: timePart) {
                    let displayFormatter = DateFormatter()
                    displayFormatter.dateFormat = "h:mm a"
                    return displayFormatter.string(from: timeDate)
                }
                return timePart
            }
        }
        
        return timestamp
    }
    
    private func formatFileSize(_ size: Int) -> String {
        let formatter = ByteCountFormatter()
        formatter.allowedUnits = [.useMB, .useKB]
        formatter.countStyle = .file
        return formatter.string(fromByteCount: Int64(size))
    }
    
    private func getCameraDisplayName(_ cameraId: String?) -> String {
        guard let cameraId = cameraId else { return "Unknown" }
        switch cameraId {
        case "cam1":
            return "ESP32"
        case "cam2":
            return "Pi Zero"
        default:
            return cameraId.uppercased()
        }
    }
}

struct VideoPlayerView: View {
    let videoURL: URL
    @Environment(\.dismiss) private var dismiss
    @State private var player: AVPlayer?
    @State private var errorMessage: String?
    
    var body: some View {
        NavigationView {
            ZStack {
                Color.black.ignoresSafeArea()
                
                if let errorMessage = errorMessage {
                    VStack(spacing: 20) {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.system(size: 50))
                            .foregroundColor(.red)
                        
                        Text("Video Playback Error")
                            .font(.title2)
                            .fontWeight(.semibold)
                        
                        Text(errorMessage)
                            .font(.body)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                        
                        Text("Note: AVI format may not be supported on iOS. Consider converting to MP4 format.")
                            .font(.caption)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                    }
                    .padding()
                } else if let player = player {
                    VideoPlayer(player: player)
                        .ignoresSafeArea()
                } else {
                    ProgressView("Loading video...")
                        .progressViewStyle(CircularProgressViewStyle(tint: .green))
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        player?.pause()
                        dismiss()
                    }
                    .foregroundColor(.white)
                }
            }
            .onAppear {
                setupPlayer()
            }
        }
    }
    
    private func setupPlayer() {
        let asset = AVAsset(url: videoURL)
        
        // Check if the asset is playable
        asset.loadValuesAsynchronously(forKeys: ["playable"]) {
            DispatchQueue.main.async {
                if asset.isPlayable {
                    self.player = AVPlayer(url: videoURL)
                } else {
                    self.errorMessage = "This video format is not supported on iOS. AVI files need to be converted to MP4."
                }
            }
        }
    }
}

struct DatePickerSheet: View {
    let availableDates: [String]
    @Binding var selectedDate: String?
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject var apiService: APIService
    
    var body: some View {
        NavigationView {
            ZStack {
                Color.black.ignoresSafeArea()
                
                List {
                    Section("All Dates") {
                        Button("Show All") {
                            selectedDate = nil
                            dismiss()
                        }
                        .foregroundColor(.primary)
                    }
                    
                    Section("Available Dates") {
                        ForEach(availableDates, id: \.self) { date in
                            Button(action: {
                                selectedDate = date
                                dismiss()
                            }) {
                                HStack {
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(formatDate(date))
                                            .font(.system(size: 16, weight: .medium))
                                            .foregroundColor(.primary)
                                        
                                        Text("\(getClipCount(for: date)) clips")
                                            .font(.system(size: 14))
                                            .foregroundColor(.secondary)
                                    }
                                    
                                    Spacer()
                                    
                                    if selectedDate == date {
                                        Image(systemName: "checkmark.circle.fill")
                                            .foregroundColor(.green)
                                    }
                                }
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
                .scrollContentBackground(.hidden)
            }
            .navigationTitle("Select Date")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
        .preferredColorScheme(.dark)
    }
    
    private func formatDate(_ dateString: String) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        
        if let date = formatter.date(from: dateString) {
            let displayFormatter = DateFormatter()
            displayFormatter.dateFormat = "EEEE, MMM d, yyyy"  // "Monday, Sep 15, 2025"
            return displayFormatter.string(from: date)
        }
        
        return dateString
    }
    
    private func getClipCount(for date: String) -> Int {
        // This is a simplified version - in a real app you'd want to get this from the clips data
        return 0  // Placeholder - would need access to clips data
    }
}

#Preview {
    ClipsView()
        .environmentObject(APIService.shared)
}
