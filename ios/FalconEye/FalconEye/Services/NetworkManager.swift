import Foundation
import Network
import SwiftUI

class NetworkManager: ObservableObject {
    static let shared = NetworkManager()
    
    @Published var isLocalNetwork = false
    @Published var currentBaseURL: String = "https://cam.falconeye.website" // Default to Cloudflare
    
    // Discovered local candidates via Bonjour (_falconeye._tcp). First reachable wins.
    private var discoveredCandidates: Set<String> = []
    // Optional static fallbacks kept for resilience if discovery fails
    private let staticFallbackCandidates: [String] = [
        "http://192.168.31.233:3000",
        "http://10.34.63.233:3000",
    ]
    private let cloudflareBaseURL = "https://cam.falconeye.website"
    
    // Track which local candidate is currently active (readable outside, writable inside)
    private(set) var activeLocalCandidate: String?
    
    private let monitor = NWPathMonitor()
    private let queue = DispatchQueue(label: "NetworkMonitor")
    
    // Bonjour discovery
    private var browser: NWBrowser?
    private let discoveryQueue = DispatchQueue(label: "falconeye.discovery")
    
    private init() {
        // Start with Cloudflare as default, then check for local network
        updateBaseURL()
        startMonitoring()
        // Immediately check current network status
        updateNetworkStatus(path: monitor.currentPath)
        
        // Force a network check after a short delay to ensure proper detection
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            self.refreshNetworkStatus()
        }
    }
    
    deinit {
        monitor.cancel()
        stopDiscovery()
    }
    
    private func startMonitoring() {
        monitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                self?.updateNetworkStatus(path: path)
            }
        }
        monitor.start(queue: queue)
    }
    
    private func updateNetworkStatus(path: NWPath) {
        let wasLocalNetwork = isLocalNetwork
        
        // Always check local server availability if we have any network connection
        if path.status == .satisfied {
            // On any reachable network (Wi‑Fi, cellular, other), try local discovery quickly.
            if path.usesInterfaceType(.wifi) {
                print("📶 WiFi detected, attempting local discovery…")
            } else if path.usesInterfaceType(.cellular) {
                print("📱 Cellular path active; attempting local discovery just in case…")
            } else {
                print("🌐 Network active (other); attempting local discovery…")
            }
            startDiscovery()
            checkLocalServerAvailability { [weak self] resolvedBase in
                DispatchQueue.main.async {
                    if let base = resolvedBase {
                        self?.isLocalNetwork = true
                        self?.activeLocalCandidate = base
                        self?.updateBaseURL()
                        print("🌐 Network changed: Local Network (\(base))")
                    } else {
                        self?.isLocalNetwork = false
                        self?.activeLocalCandidate = nil
                        self?.updateBaseURL()
                        print("🌐 Network changed: No local server found, using Cloudflare")
                    }
                }
            }
        } else {
            // No connection, use Cloudflare tunnel
            print("❌ No network connection, using Cloudflare tunnel")
            stopDiscovery()
            isLocalNetwork = false
            activeLocalCandidate = nil
            updateBaseURL()
        }
    }
    
    private func checkLocalServerAvailability(completion: @escaping (String?) -> Void) {
        // Allow manual override via UserDefaults
        if let manual = UserDefaults.standard.string(forKey: "LocalBaseURLOverride"), manual.hasPrefix("http") {
            print("🔧 Using manual LocalBaseURLOverride: \(manual)")
            return completion(manual)
        }
        
        // Try each candidate in order: discovered first, then static fallbacks
        let discovered = Array(discoveredCandidates)
        let candidates = discovered + staticFallbackCandidates
        var index = 0
        func tryNext() {
            if index >= candidates.count {
                completion(nil)
                return
            }
            let base = candidates[index]
            index += 1
            guard let url = URL(string: "\(base)/system/status") else { tryNext(); return }
            print("🔍 Checking local server availability: \(url)")
            var request = URLRequest(url: url)
            request.timeoutInterval = 1.2
            request.cachePolicy = .reloadIgnoringLocalCacheData
            URLSession.shared.dataTask(with: request) { data, response, error in
                if let http = response as? HTTPURLResponse, http.statusCode == 200 {
                    completion(base)
                } else {
                    tryNext()
                }
            }.resume()
        }
        tryNext()
    }
    
    private func updateBaseURL() {
        if isLocalNetwork, let activeCandidate = activeLocalCandidate {
            // Use the active local candidate
            currentBaseURL = activeCandidate
        } else {
            // Use Cloudflare
            currentBaseURL = cloudflareBaseURL
        }
        
        // Safety check: never use localhost or 127.0.0.1
        if currentBaseURL.contains("127.0.0.1") || currentBaseURL.contains("localhost") {
            print("⚠️ Preventing localhost connection, using Cloudflare instead")
            currentBaseURL = cloudflareBaseURL
            isLocalNetwork = false
            activeLocalCandidate = nil
        }
        
        postUpdateLog()
    }
    
    private func postUpdateLog() {
        print("🔗 Using base URL: \(currentBaseURL)")
        print("🔗 isLocalNetwork: \(isLocalNetwork)")
        print("🔗 activeLocalCandidate: \(activeLocalCandidate ?? "none")")
        print("🔗 discoveredCandidates: \(Array(discoveredCandidates))")
        print("🔗 staticFallbackCandidates: \(staticFallbackCandidates)")
        print("🔗 cloudflareBaseURL: \(cloudflareBaseURL)")
    }
    
    // Allow runtime override for demos
    func setLocalBaseURLOverride(_ url: String?) {
        if let u = url, !u.isEmpty { UserDefaults.standard.setValue(u, forKey: "LocalBaseURLOverride") }
        else { UserDefaults.standard.removeObject(forKey: "LocalBaseURLOverride") }
        refreshNetworkStatus()
    }
    
    // Helper method to get the appropriate URL for any endpoint
    func getURL(for endpoint: String) -> String {
        return "\(currentBaseURL)\(endpoint)"
    }
    
    // Method to manually refresh network status
    func refreshNetworkStatus() {
        print("🔄 Manually refreshing network status...")
        // Force a network check by creating a new path monitor temporarily
        let tempMonitor = NWPathMonitor()
        tempMonitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                self?.updateNetworkStatus(path: path)
            }
            tempMonitor.cancel()
        }
        tempMonitor.start(queue: queue)
    }
    
    // Method to force local network mode (for testing)
    func forceLocalNetwork() {
        print("🔧 Forcing local network mode...")
        isLocalNetwork = true
        updateBaseURL()
    }
    
    // Method to force cloudflare mode (for testing)
    func forceCloudflareMode() {
        print("🔧 Forcing Cloudflare mode...")
        isLocalNetwork = false
        updateBaseURL()
    }
    
    // Method to get current network status for debugging
    func getNetworkStatus() -> (isLocal: Bool, currentURL: String, activeCandidate: String?) {
        return (isLocalNetwork, currentBaseURL, activeLocalCandidate)
    }
}

// MARK: - Network Status View
struct NetworkStatusIndicator: View {
    @ObservedObject var networkManager = NetworkManager.shared
    
    var body: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(networkManager.isLocalNetwork ? Color.green : Color.blue)
                .frame(width: 8, height: 8)
                .animation(.easeInOut(duration: 0.3), value: networkManager.isLocalNetwork)
            
            Text(networkManager.isLocalNetwork ? 
                 (networkManager.activeLocalCandidate?.contains("192.168") == true ? "Home" : "Hotspot") : 
                 "Cloud")
                .font(.system(size: 12, weight: .medium))
                .foregroundColor(.secondary)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(
            Capsule()
                .fill(.ultraThinMaterial)
        )
    }
}

// MARK: - Bonjour Discovery
extension NetworkManager {
    private func startDiscovery() {
        if browser != nil { return }
        let bonjour = NWBrowser.Descriptor.bonjour(type: "_falconeye._tcp", domain: "local")
        let params = NWParameters.tcp
        let b = NWBrowser(for: bonjour, using: params)
        b.stateUpdateHandler = { state in
            switch state {
            case .ready:
                print("🛰️ Bonjour discovery ready")
            case .failed(let error):
                print("🛰️ Bonjour discovery failed: \(error)")
            case .waiting(let error):
                print("🛰️ Bonjour discovery waiting: \(error)")
            default:
                break
            }
        }
        b.browseResultsChangedHandler = { [weak self] results, _ in
            guard let self = self else { return }
            var next: Set<String> = []
            for result in results {
                if case let .service(name, type, domain, interface) = result.endpoint {
                    let endpoint = NWEndpoint.service(name: name, type: type, domain: domain, interface: interface)
                    let conn = NWConnection(to: endpoint, using: .tcp)
                    conn.stateUpdateHandler = { state in
                        if case .ready = state {
                            if case let .hostPort(host, port) = conn.currentPath?.remoteEndpoint {
                                let hostStr = host.debugDescription.trimmingCharacters(in: CharacterSet(charactersIn: "\""))
                                let base = "http://\(hostStr):\(port.rawValue)"
                                self.discoveryFound(base)
                            }
                            conn.cancel()
                        }
                    }
                    conn.start(queue: self.discoveryQueue)
                }
            }
            // Replace entire set if nothing resolved via connections yet
            // We rely on discoveryFound to update when connections resolve.
            if next.isEmpty == false {
                DispatchQueue.main.async {
                    self.discoveredCandidates = next
                }
            }
        }
        browser = b
        b.start(queue: discoveryQueue)
    }
    
    private func discoveryFound(_ base: String) {
        DispatchQueue.main.async {
            let before = self.discoveredCandidates
            self.discoveredCandidates.insert(base)
            if before != self.discoveredCandidates {
                print("🛰️ Discovered FalconEye at: \(base)")
                // Re-evaluate availability immediately
                self.checkLocalServerAvailability { [weak self] resolved in
                    guard let self = self else { return }
                    DispatchQueue.main.async {
                        if let r = resolved {
                            self.isLocalNetwork = true
                            self.activeLocalCandidate = r
                        }
                        self.updateBaseURL()
                    }
                }
            }
        }
    }
    
    private func stopDiscovery() {
        browser?.cancel()
        browser = nil
        discoveredCandidates.removeAll()
    }
}
