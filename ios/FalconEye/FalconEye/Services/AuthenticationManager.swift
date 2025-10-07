import Foundation
import SwiftUI

class AuthenticationManager: ObservableObject {
    @Published var isAuthenticated = false
    @Published var currentUser: String?
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    private let userDefaults = UserDefaults.standard
    private let apiService = APIService.shared
    
    init() {
        checkAuthenticationStatus()
    }
    
    private func checkAuthenticationStatus() {
        // Check if user is already authenticated
        if let savedUser = userDefaults.string(forKey: "currentUser") {
            currentUser = savedUser
            isAuthenticated = true
        }
    }
    
    func login(username: String, password: String, rememberMe: Bool) async {
        DispatchQueue.main.async {
            self.isLoading = true
            self.errorMessage = nil
        }
        
        do {
            let response = try await apiService.login(username: username, password: password, rememberMe: rememberMe)
            
            DispatchQueue.main.async {
                if response.status == "ok" {
                    self.currentUser = username
                    self.isAuthenticated = true
                    self.userDefaults.set(username, forKey: "currentUser")
                    if rememberMe {
                        self.userDefaults.set(true, forKey: "rememberMe")
                    }
                } else {
                    self.errorMessage = response.message ?? "Login failed"
                }
                self.isLoading = false
            }
        } catch {
            DispatchQueue.main.async {
                self.errorMessage = error.localizedDescription
                self.isLoading = false
            }
        }
    }
    
    func logout() {
        DispatchQueue.main.async {
            self.currentUser = nil
            self.isAuthenticated = false
            self.userDefaults.removeObject(forKey: "currentUser")
            self.userDefaults.removeObject(forKey: "rememberMe")
        }
    }
    
    func clearError() {
        errorMessage = nil
    }
}
