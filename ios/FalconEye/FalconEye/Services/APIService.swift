import Foundation
import Combine

class APIService: ObservableObject {
    static let shared = APIService()
    
    private let networkManager = NetworkManager.shared
    private let session = URLSession.shared
    
    // Computed property that automatically switches between local and cloud URLs
    var baseURL: String {
        let url = networkManager.currentBaseURL
        print("🌐 APIService baseURL: \(url)")
        return url
    }
    
    @Published var isConnected = false
    @Published var systemStatus: SystemStatus?
    
    init() {
        print("🔧 APIService initialized with baseURL: \(baseURL)")
        checkConnection()
    }
    
    // MARK: - Connection Management
    func checkConnection() {
        guard let url = URL(string: "\(baseURL)/mobile/status") else { 
            print("❌ Invalid URL: \(baseURL)/mobile/status")
            return 
        }
        
        print("🌐 Checking connection to: \(url)")
        session.dataTask(with: url) { [weak self] data, response, error in
            DispatchQueue.main.async {
                if let httpResponse = response as? HTTPURLResponse,
                   httpResponse.statusCode == 200 {
                    self?.isConnected = true
                    if let data = data {
                        do {
                            self?.systemStatus = try JSONDecoder().decode(SystemStatus.self, from: data)
                        } catch {
                            print("Error decoding system status: \(error)")
                        }
                    }
                } else {
                    self?.isConnected = false
                }
            }
        }.resume()
    }
    
    func getSystemStatus() async throws -> SystemStatus {
        guard let url = URL(string: "\(baseURL)/mobile/status") else {
            throw APIError(message: "Invalid URL", statusCode: nil)
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError(message: "Failed to get system status", statusCode: nil)
        }
        
        let status = try JSONDecoder().decode(SystemStatus.self, from: data)
        
        DispatchQueue.main.async {
            self.systemStatus = status
        }
        
        return status
    }
    
    // MARK: - Authentication
    func login(username: String, password: String, rememberMe: Bool) async throws -> LoginResponse {
        guard let url = URL(string: "\(baseURL)/auth/login") else {
            throw APIError(message: "Invalid URL", statusCode: nil)
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let loginRequest = LoginRequest(username: username, password: password, remember_me: rememberMe)
        request.httpBody = try JSONEncoder().encode(loginRequest)
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError(message: "Invalid response", statusCode: nil)
        }
        
        let loginResponse = try JSONDecoder().decode(LoginResponse.self, from: data)
        
        if httpResponse.statusCode == 200 {
            return loginResponse
        } else {
            throw APIError(message: loginResponse.message ?? "Login failed", statusCode: httpResponse.statusCode)
        }
    }
    
    // MARK: - Camera Operations
    func getCameraInfo() async throws -> CameraInfo {
        guard let url = URL(string: "\(baseURL)/mobile/camera/info") else {
            throw APIError(message: "Invalid URL", statusCode: nil)
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError(message: "Failed to get camera info", statusCode: nil)
        }
        
        return try JSONDecoder().decode(CameraInfo.self, from: data)
    }
    
    func getCameraSnapshot(cameraId: String) async throws -> Data {
        guard let url = URL(string: "\(baseURL)/camera/snapshot/\(cameraId)") else {
            throw APIError(message: "Invalid URL", statusCode: nil)
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError(message: "Failed to get camera snapshot", statusCode: nil)
        }
        
        return data
    }
    
    // MARK: - Clips Management
    func getClipsSummary() async throws -> ClipsSummary {
        guard let url = URL(string: "\(baseURL)/mobile/clips/summary") else {
            throw APIError(message: "Invalid URL", statusCode: nil)
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError(message: "Failed to get clips summary", statusCode: nil)
        }
        
        return try JSONDecoder().decode(ClipsSummary.self, from: data)
    }
    
    func getClips() async throws -> [String: ClipMetadata] {
        guard let url = URL(string: "\(baseURL)/clips") else {
            throw APIError(message: "Invalid URL", statusCode: nil)
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError(message: "Failed to get clips", statusCode: nil)
        }
        
        // Parse the raw JSON response
        let json = try JSONSerialization.jsonObject(with: data) as? [String: [String: Any]] ?? [:]
        
        // Convert to ClipMetadata objects
        var clips: [String: ClipMetadata] = [:]
        for (filename, clipData) in json {
            let clip = ClipMetadata(
                filename: filename,
                timestamp: clipData["timestamp"] as? String ?? "",
                duration: clipData["duration"] as? Double ?? 0.0,
                size: clipData["size"] as? Int,
                tags: clipData["tags"] as? [String] ?? [],
                uploaded_to_s3: clipData["uploaded_to_s3"] as? Bool ?? false,
                s3_url: clipData["s3_url"] as? String,
                camera: clipData["camera"] as? String,
                s3_upload_time: clipData["s3_upload_time"] as? String
            )
            clips[filename] = clip
        }
        
        return clips
    }
    
    func downloadClip(filename: String) async throws -> Data {
        guard let url = URL(string: "\(baseURL)/clips/\(filename)") else {
            throw APIError(message: "Invalid URL", statusCode: nil)
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError(message: "Failed to download clip", statusCode: nil)
        }
        
        return data
    }
    
    // MARK: - Detections
    func getRecentDetections() async throws -> [Detection] {
        guard let url = URL(string: "\(baseURL)/mobile/detections/recent") else {
            throw APIError(message: "Invalid URL", statusCode: nil)
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError(message: "Failed to get recent detections", statusCode: nil)
        }
        
        return try JSONDecoder().decode([Detection].self, from: data)
    }
    
    // MARK: - Pi Zero Pan Controls (cam2)
    func panCamLeft() async throws {
        try await sendPanCommand(action: "left")
    }
    
    func panCamRight() async throws {
        try await sendPanCommand(action: "right")
    }
    
    func panCamAuto() async throws {
        try await sendPanCommand(action: "auto")
    }
    
    private func sendPanCommand(action: String) async throws {
        guard let url = URL(string: "\(baseURL)/camera/pan/\(action)") else {
            throw APIError(message: "Invalid URL", statusCode: nil)
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let (_, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw APIError(message: "Pan command failed", statusCode: (response as? HTTPURLResponse)?.statusCode)
        }
    }
    
    // MARK: - FCM Token Management
    func registerFCMToken(token: String) async throws -> FCMResponse {
        guard let url = URL(string: "\(baseURL)/fcm/register") else {
            throw APIError(message: "Invalid URL", statusCode: nil)
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let tokenRequest = FCMTokenRequest(token: token)
        request.httpBody = try JSONEncoder().encode(tokenRequest)
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError(message: "Invalid response", statusCode: nil)
        }
        
        return try JSONDecoder().decode(FCMResponse.self, from: data)
    }
    
    func unregisterFCMToken(token: String) async throws -> FCMResponse {
        guard let url = URL(string: "\(baseURL)/fcm/unregister") else {
            throw APIError(message: "Invalid URL", statusCode: nil)
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let tokenRequest = FCMTokenRequest(token: token)
        request.httpBody = try JSONEncoder().encode(tokenRequest)
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError(message: "Invalid response", statusCode: nil)
        }
        
        return try JSONDecoder().decode(FCMResponse.self, from: data)
    }
    
    func testPushNotification() async throws -> FCMResponse {
        guard let url = URL(string: "\(baseURL)/mobile/test-push") else {
            throw APIError(message: "Invalid URL", statusCode: nil)
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let testRequest = ["test": true]
        request.httpBody = try JSONEncoder().encode(testRequest)
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError(message: "Invalid response", statusCode: nil)
        }
        
        return try JSONDecoder().decode(FCMResponse.self, from: data)
    }
    
    // MARK: - Device Token Management (Simple APNs)
    func registerDeviceToken(token: String) async throws -> FCMResponse {
        guard let url = URL(string: "\(baseURL)/device/register") else {
            throw APIError(message: "Invalid URL", statusCode: nil)
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let tokenRequest = FCMTokenRequest(token: token)
        request.httpBody = try JSONEncoder().encode(tokenRequest)
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError(message: "Invalid response", statusCode: nil)
        }
        
        return try JSONDecoder().decode(FCMResponse.self, from: data)
    }
    
    func testBackendNotification() async throws -> FCMResponse {
        guard let url = URL(string: "\(baseURL)/device/test-notification") else {
            throw APIError(message: "Invalid URL", statusCode: nil)
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError(message: "Invalid response", statusCode: nil)
        }
        
        return try JSONDecoder().decode(FCMResponse.self, from: data)
    }
    
    func getNotifications(deviceId: String) async throws -> [NotificationData] {
        guard let url = URL(string: "\(baseURL)/mobile/notifications?device_id=\(deviceId)") else {
            throw APIError(message: "Invalid URL", statusCode: nil)
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError(message: "Invalid response", statusCode: nil)
        }
        
        let notificationResponse = try JSONDecoder().decode(NotificationResponse.self, from: data)
        return notificationResponse.notifications
    }

    // MARK: - Facial Recognition
    func getFacesStatus() async throws -> FacesStatus {
        guard let url = URL(string: "\(baseURL)/faces/status") else {
            throw APIError(message: "Invalid URL", statusCode: nil)
        }
        let (data, response) = try await session.data(from: url)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw APIError(message: "Failed to get faces status", statusCode: (response as? HTTPURLResponse)?.statusCode)
        }
        return try JSONDecoder().decode(FacesStatus.self, from: data)
    }

    func setFacesEnabled(_ enabled: Bool) async throws -> FacesStatus {
        guard let url = URL(string: "\(baseURL)/faces/enable") else {
            throw APIError(message: "Invalid URL", statusCode: nil)
        }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONEncoder().encode(["enabled": enabled])
        let (data, response) = try await session.data(for: req)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw APIError(message: "Failed to set faces enabled", statusCode: (response as? HTTPURLResponse)?.statusCode)
        }
        return try JSONDecoder().decode(FacesStatus.self, from: data)
    }

    func registerFace(name: String, jpegData: Data) async throws -> FaceRegisterResponse {
        guard let url = URL(string: "\(baseURL)/faces/register") else {
            throw APIError(message: "Invalid URL", statusCode: nil)
        }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let payload: [String:Any] = [
            "name": name,
            "image_base64": "data:image/jpeg;base64,\(jpegData.base64EncodedString())"
        ]
        req.httpBody = try JSONSerialization.data(withJSONObject: payload)
        let (data, response) = try await session.data(for: req)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw APIError(message: "Failed to register face", statusCode: (response as? HTTPURLResponse)?.statusCode)
        }
        return try JSONDecoder().decode(FaceRegisterResponse.self, from: data)
    }

    func deleteFace(name: String) async throws {
        guard let url = URL(string: "\(baseURL)/faces/delete") else {
            throw APIError(message: "Invalid URL", statusCode: nil)
        }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: ["name": name])
        let (_, response) = try await session.data(for: req)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw APIError(message: "Failed to delete face", statusCode: (response as? HTTPURLResponse)?.statusCode)
        }
    }
}
