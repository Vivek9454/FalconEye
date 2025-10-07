import SwiftUI

struct LoginView: View {
    @EnvironmentObject var authManager: AuthenticationManager
    @EnvironmentObject var themeManager: ThemeManager
    @EnvironmentObject var notificationManager: LocalNotificationManager
    @State private var username = ""
    @State private var password = ""
    @State private var rememberMe = false
    @State private var showPassword = false
    @State private var isLoading = false
    @State private var errorMessage = ""
    
    var body: some View {
        GeometryReader { geometry in
            ZStack {
                // Animated background
                AnimatedBackground(theme: themeManager.currentTheme, isDark: themeManager.isDarkMode)
                
                // Main content
                VStack(spacing: 0) {
                    Spacer()
                    
                    // Login container
                    VStack(spacing: 32) {
                        // Logo container
                        VStack(spacing: 16) {
                            // Logo
                            ThemeAwareAppIcon(theme: themeManager.currentTheme, isDark: themeManager.isDarkMode, size: 80)
                                .shadow(color: AppColors.accent(for: themeManager.currentTheme, isDark: themeManager.isDarkMode).opacity(0.3), radius: 8, x: 0, y: 4)
                                .shadow(color: AppColors.accent(for: themeManager.currentTheme, isDark: themeManager.isDarkMode).opacity(0.2), radius: 0, x: 0, y: 0)
                                .scaleEffect(1.0)
                                .animation(.easeInOut(duration: 3).repeatForever(autoreverses: true), value: UUID())
                            
                            // Title
                            Text("FalconEye")
                                .font(.system(size: 28, weight: .semibold, design: .rounded))
                                .foregroundStyle(
                                    LinearGradient(
                                        colors: [AppColors.accent(for: themeManager.currentTheme, isDark: themeManager.isDarkMode), AppColors.accent(for: themeManager.currentTheme, isDark: themeManager.isDarkMode).opacity(0.8)],
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    )
                                )
                        }
                        
                        // Form
                        VStack(spacing: 20) {
                            // Username field
                            VStack(alignment: .leading, spacing: 8) {
                                TextField("Username", text: $username)
                                    .textFieldStyle(GlassTextFieldStyle())
                                    .autocapitalization(.none)
                                    .disableAutocorrection(true)
                            }
                            
                            // Password field
                            VStack(alignment: .leading, spacing: 8) {
                                ZStack(alignment: .trailing) {
                                    if showPassword {
                                        TextField("Password", text: $password)
                                            .textFieldStyle(GlassTextFieldStyle())
                                    } else {
                                        SecureField("Password", text: $password)
                                            .textFieldStyle(GlassTextFieldStyle())
                                    }
                                    
                                    Button(action: { showPassword.toggle() }) {
                                        Image(systemName: showPassword ? "eye.slash" : "eye")
                                            .foregroundColor(.secondary)
                                            .font(.system(size: 16))
                                    }
                                    .padding(.trailing, 16)
                                }
                            }
                            
                            // Remember me
                            HStack {
                                Button(action: { rememberMe.toggle() }) {
                                    HStack(spacing: 12) {
                                        Image(systemName: rememberMe ? "checkmark.square.fill" : "square")
                                            .foregroundColor(rememberMe ? .green : .secondary)
                                            .font(.system(size: 20))
                                        
                                        Text("Remember me for this session")
                                            .font(.system(size: 15, weight: .regular))
                                            .foregroundColor(.secondary)
                                    }
                                }
                                .buttonStyle(.plain)
                                
                                Spacer()
                            }
                            
                            // Error message
                            if !errorMessage.isEmpty {
                                Text(errorMessage)
                                    .font(.system(size: 14, weight: .medium))
                                    .foregroundColor(.red)
                                    .padding(.horizontal, 20)
                                    .padding(.vertical, 12)
                                    .background(
                                        RoundedRectangle(cornerRadius: 8)
                                            .fill(.red.opacity(0.1))
                                            .overlay(
                                                RoundedRectangle(cornerRadius: 8)
                                                    .stroke(.red.opacity(0.3), lineWidth: 1)
                                            )
                                    )
                            }
                            
                            // Login button
                            Button(action: login) {
                                HStack {
                                    if isLoading {
                                        ProgressView()
                                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                            .scaleEffect(0.8)
                                    } else {
                                        Text("ACCESS DASHBOARD")
                                            .font(.system(size: 16, weight: .semibold))
                                            .tracking(0.5)
                                    }
                                }
                                .frame(maxWidth: .infinity)
                                .frame(height: 56)
                                .background(
                                    LinearGradient(
                                        colors: [.green, Color.green.opacity(0.8)],
                                        startPoint: .leading,
                                        endPoint: .trailing
                                    )
                                )
                                .clipShape(RoundedRectangle(cornerRadius: 12))
                                .shadow(color: .green.opacity(0.3), radius: 8, x: 0, y: 4)
                            }
                            .buttonStyle(GlassButtonStyle())
                            .disabled(isLoading || username.isEmpty || password.isEmpty)
                        }
                        
                        // Security badge
                        HStack(spacing: 8) {
                            Image(systemName: "lock.shield")
                                .foregroundColor(.green)
                                .font(.system(size: 14))
                            
                            Text("Secure surveillance system • Encrypted connection")
                                .font(.system(size: 12, weight: .medium))
                                .foregroundColor(.secondary)
                        }
                        .padding(.top, 8)
                    }
                    .padding(40)
                    .background(
                        RoundedRectangle(cornerRadius: 24)
                            .fill(.ultraThinMaterial)
                            .overlay(
                                RoundedRectangle(cornerRadius: 24)
                                    .stroke(.white.opacity(0.1), lineWidth: 1)
                            )
                            .shadow(color: .black.opacity(0.4), radius: 20, x: 0, y: 10)
                            .shadow(color: .white.opacity(0.05), radius: 0, x: 0, y: 0)
                    )
                    .padding(.horizontal, 20)
                    
                    Spacer()
                }
            }
        }
        .background(Color.black)
        .ignoresSafeArea()
    }
    
    private func login() {
        isLoading = true
        errorMessage = ""
        
        Task {
            do {
                try await authManager.login(username: username, password: password, rememberMe: rememberMe)
                
                // Request notification permissions after successful login
                await MainActor.run {
                    isLoading = false
                    print("🔔 Requesting notification permissions after login...")
                    notificationManager.requestPermissions()
                }
            } catch {
                await MainActor.run {
                    isLoading = false
                    errorMessage = error.localizedDescription
                }
            }
        }
    }
}

struct AnimatedBackground: View {
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    @State private var animate = false
    
    var body: some View {
        ZStack {
            // Base gradient
            LinearGradient(
                colors: [
                    AppColors.background(for: theme, isDark: isDark),
                    AppColors.background(for: theme, isDark: isDark).opacity(0.9),
                    AppColors.background(for: theme, isDark: isDark).opacity(0.8)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            
            // Animated particles
            ForEach(0..<3, id: \.self) { index in
                Circle()
                    .fill(
                        RadialGradient(
                            colors: [
                                AppColors.accent(for: theme, isDark: isDark).opacity(0.1),
                                AppColors.accent(for: theme, isDark: isDark).opacity(0.05),
                                Color.clear
                            ],
                            center: .center,
                            startRadius: 0,
                            endRadius: 100
                        )
                    )
                    .frame(width: 200, height: 200)
                    .offset(
                        x: animate ? CGFloat.random(in: -50...50) : CGFloat.random(in: -30...30),
                        y: animate ? CGFloat.random(in: -50...50) : CGFloat.random(in: -30...30)
                    )
                    .animation(
                        .easeInOut(duration: Double.random(in: 15...25))
                        .repeatForever(autoreverses: true),
                        value: animate
                    )
            }
        }
        .onAppear {
            animate = true
        }
    }
}

struct GlassTextFieldStyle: TextFieldStyle {
    func _body(configuration: TextField<Self._Label>) -> some View {
        configuration
            .padding(16)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(.ultraThinMaterial)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(.white.opacity(0.1), lineWidth: 2)
                    )
            )
            .foregroundColor(.white)
            .font(.system(size: 16, weight: .regular))
    }
}

struct GlassButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
            .opacity(configuration.isPressed ? 0.8 : 1.0)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}

#Preview {
    LoginView()
        .environmentObject(AuthenticationManager())
}