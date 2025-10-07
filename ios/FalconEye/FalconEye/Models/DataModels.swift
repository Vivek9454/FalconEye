import Foundation

// MARK: - Authentication Models
struct LoginRequest: Codable {
    let username: String
    let password: String
    let remember_me: Bool
}

struct LoginResponse: Codable {
    let status: String
    let redirect: String?
    let message: String?
}

// MARK: - Camera Models
struct CameraInfo: Codable {
    let cameras: [String]
    let live_url: String
    let snapshot_url: String
    let mobile_optimized: Bool
    let bandwidth_saving: Bool
}

struct CameraSnapshot: Codable {
    let imageData: Data?
    let timestamp: Date
}

// MARK: - Clips Models
struct ClipMetadata: Codable, Identifiable {
    let id = UUID()
    let filename: String
    let timestamp: String
    let duration: Double
    let size: Int?
    let tags: [String]
    let uploaded_to_s3: Bool
    let s3_url: String?
    let camera: String?
    let s3_upload_time: String?
    
    // Computed property for backward compatibility
    var s3_uploaded: Bool { uploaded_to_s3 }
    
    // Custom initializer to handle the API response format
    init(filename: String, timestamp: String, duration: Double, size: Int? = nil, tags: [String], uploaded_to_s3: Bool, s3_url: String? = nil, camera: String? = nil, s3_upload_time: String? = nil) {
        self.filename = filename
        self.timestamp = timestamp
        self.duration = duration
        self.size = size
        self.tags = tags
        self.uploaded_to_s3 = uploaded_to_s3
        self.s3_url = s3_url
        self.camera = camera
        self.s3_upload_time = s3_upload_time
    }
    
    var formattedDate: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"
        if let date = formatter.date(from: timestamp) {
            let displayFormatter = DateFormatter()
            displayFormatter.dateStyle = .medium
            displayFormatter.timeStyle = .short
            return displayFormatter.string(from: date)
        }
        return timestamp
    }
}

struct ClipsSummary: Codable {
    let clips_by_date: [ClipsByDate]
}

struct ClipsByDate: Codable, Identifiable {
    let id = UUID()
    let date: String
    let count: Int
    let objects: [String]
}

// MARK: - Detection Models
struct Detection: Codable, Identifiable {
    let id = UUID()
    let timestamp: String
    let objects: [String]
    let confidence: Double
    let camera: String
    let image_url: String?
}

// MARK: - System Status Models
struct SystemStatus: Codable {
    let status: String
    let device: String?
    let surveillance_objects: [String]?
    let features: SystemFeatures?
    
    // Computed properties for backward compatibility
    var cameraStreaming: Bool { true }
    var videoRecording: Bool { features?.video_recording ?? true }
    var objectDetection: Bool { features?.object_detection ?? true }
    var pushNotifications: Bool { features?.push_notifications ?? true }
}

struct SystemFeatures: Codable {
    let live_stream: Bool?
    let object_detection: Bool?
    let video_recording: Bool?
    let push_notifications: Bool?
    let mobile_optimized: Bool?
}

// MARK: - Faces Models
struct FacesStatus: Codable {
    let enabled: Bool
    let engine: String?
}

struct FaceRegisterResponse: Codable {
    let success: Bool?
    let message: String?
    let name: String?
    let faces: Int?
}

// MARK: - FCM Models
struct FCMTokenRequest: Codable {
    let token: String
}

struct FCMResponse: Codable {
    let status: String
    let message: String?
    let registered_tokens: Int?
}

// MARK: - Notification Models
struct NotificationData: Codable, Identifiable {
    let id: String
    let title: String
    let body: String
    let data: [String: String]?
    let sound: String?
    let badge: Int?
    
    enum CodingKeys: String, CodingKey {
        case id, title, body, data, sound, badge
    }
}

struct NotificationResponse: Codable {
    let notifications: [NotificationData]
    let count: Int
}

// MARK: - API Error Model
struct APIError: Error, LocalizedError {
    let message: String
    let statusCode: Int?
    
    var errorDescription: String? {
        return message
    }
}
