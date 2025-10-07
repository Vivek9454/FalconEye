import Foundation
import Network

public struct DiscoveredService: Hashable {
    public let name: String
    public let host: String
    public let port: Int
}

public final class FalconEyeDiscovery {
    private let browser: NWBrowser
    private let queue = DispatchQueue(label: "falconeye.discovery")
    private var found: Set<DiscoveredService> = []
    public init() {
        let parameters = NWParameters.tcp
        let bonjour = NWBrowser.Descriptor.bonjour(type: "_falconeye._tcp", domain: "local")
        browser = NWBrowser(for: bonjour, using: parameters)
    }

    public func start(update: @escaping (Set<DiscoveredService>) -> Void) {
        browser.stateUpdateHandler = { _ in }
        browser.browseResultsChangedHandler = { [weak self] results, _ in
            guard let self = self else { return }
            var next: Set<DiscoveredService> = []
            for result in results {
                switch result.endpoint {
                case .service(let name, let type, let domain, let interface):
                    // Resolve endpoint to host:port
                    let params = NWParameters.tcp
                    let endpoint = NWEndpoint.service(name: name, type: type, domain: domain, interface: interface)
                    let connection = NWConnection(to: endpoint, using: params)
                    connection.stateUpdateHandler = { state in
                        if case .ready = state {
                            if case let .hostPort(host, port) = connection.currentPath?.remoteEndpoint {
                                let hostStr = host.debugDescription.trimmingCharacters(in: CharacterSet(charactersIn: "\""))
                                next.insert(DiscoveredService(name: name, host: hostStr, port: Int(port.rawValue)))
                            }
                            connection.cancel()
                        }
                    }
                    connection.start(queue: self.queue)
                default:
                    break
                }
            }
            self.found = next
            update(next)
        }
        browser.start(queue: queue)
    }

    public func stop() {
        browser.cancel()
    }
}

public enum EndpointSelector {
    public static func chooseBaseURL(local: Set<DiscoveredService>, tunnelURL: URL?) -> URL? {
        if let localSvc = local.first {
            var comps = URLComponents()
            comps.scheme = "http"
            comps.host = localSvc.host
            comps.port = localSvc.port
            return comps.url
        }
        return tunnelURL
    }
}
