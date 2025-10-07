import Foundation
import SwiftUI
import Combine

class CameraManager: ObservableObject {
    @Published var cameraImages: [String: UIImage] = [:]
    @Published var cameraStatus: [String: Bool] = [:]
    
    private var cancellables = Set<AnyCancellable>()
    private var refreshTimers: [String: Timer] = [:]
    private let apiService = APIService.shared
    
    func startCamera(cameraId: String) {
        // Stop existing timer if any
        refreshTimers[cameraId]?.invalidate()
        
        // Set initial status
        cameraStatus[cameraId] = false
        
        // Different refresh rates for different cameras
        let refreshInterval: TimeInterval = cameraId == "cam1" ? 0.05 : 0.5  // ESP32: 20fps, Pi Zero: 2fps
        
        print("🎥 Starting camera \(cameraId) with refresh interval: \(refreshInterval)s (\(cameraId == "cam1" ? "20fps" : "2fps"))")
        
        // Start refreshing camera feed
        refreshTimers[cameraId] = Timer.scheduledTimer(withTimeInterval: refreshInterval, repeats: true) { [weak self] _ in
            self?.refreshCameraImage(cameraId: cameraId)
        }
        
        // Ensure timer runs on main run loop
        if let timer = refreshTimers[cameraId] {
            RunLoop.main.add(timer, forMode: .common)
        }
        
        // Initial refresh
        refreshCameraImage(cameraId: cameraId)
    }
    
    func stopCamera(cameraId: String) {
        refreshTimers[cameraId]?.invalidate()
        refreshTimers[cameraId] = nil
        cameraImages[cameraId] = nil
        cameraStatus[cameraId] = false
    }
    
    func startAllCameras() {
        startCamera(cameraId: "cam1")
        startCamera(cameraId: "cam2")
    }
    
    func refreshAllCameras() {
        refreshCameraImage(cameraId: "cam1")
        refreshCameraImage(cameraId: "cam2")
    }
    
    private func refreshCameraImage(cameraId: String) {
        Task {
            do {
                let imageData = try await apiService.getCameraSnapshot(cameraId: cameraId)
                
                DispatchQueue.main.async {
                    if let image = UIImage(data: imageData) {
                        self.cameraImages[cameraId] = image
                        self.cameraStatus[cameraId] = true
                    } else {
                        self.cameraStatus[cameraId] = false
                    }
                }
            } catch {
                DispatchQueue.main.async {
                    self.cameraStatus[cameraId] = false
                }
            }
        }
    }
    
    deinit {
        // Clean up all timers
        refreshTimers.values.forEach { $0.invalidate() }
    }
}
