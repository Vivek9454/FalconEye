import Foundation

public struct DiscoverResponse: Decodable {
    public let name: String
    public let profile: String
    public let base_url: String
    public let endpoints: [String: String]
    public let cameras: [String: String]
}

public final class FalconEyeClient {
    public let baseURL: URL
    private let session: URLSession

    public init(baseURL: URL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
    }

    public func discover(completion: @escaping (Result<DiscoverResponse, Error>) -> Void) {
        let url = baseURL.appendingPathComponent("discover")
        session.dataTask(with: url) { data, resp, err in
            if let err = err { completion(.failure(err)); return }
            guard let data = data else { completion(.failure(NSError(domain: "falconeye", code: -1))); return }
            do {
                let res = try JSONDecoder().decode(DiscoverResponse.self, from: data)
                completion(.success(res))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }

    public func systemStatus(completion: @escaping (Result<Data, Error>) -> Void) {
        let url = baseURL.appendingPathComponent("system/status")
        session.dataTask(with: url) { data, _, err in
            if let err = err { completion(.failure(err)); return }
            completion(.success(data ?? Data()))
        }.resume()
    }
}
