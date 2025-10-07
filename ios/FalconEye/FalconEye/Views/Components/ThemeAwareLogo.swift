import SwiftUI

struct ThemeAwareLogo: View {
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    let size: CGFloat
    
    init(theme: ThemeManager.AppTheme, isDark: Bool, size: CGFloat = 40) {
        self.theme = theme
        self.isDark = isDark
        self.size = size
    }
    
    var body: some View {
        Image(logoImageName)
            .resizable()
            .aspectRatio(contentMode: .fit)
            .frame(width: size, height: size)
    }
    
    private var logoImageName: String {
        switch theme {
        case .light: return "f_light"
        case .dark: return "f_dark"
        case .system: return isDark ? "f_dark" : "f_light"
        }
    }
}

struct ThemeAwareAppIcon: View {
    let theme: ThemeManager.AppTheme
    let isDark: Bool
    let size: CGFloat
    
    init(theme: ThemeManager.AppTheme, isDark: Bool, size: CGFloat = 60) {
        self.theme = theme
        self.isDark = isDark
        self.size = size
    }
    
    var body: some View {
        Image(iconImageName)
            .resizable()
            .aspectRatio(contentMode: .fit)
            .frame(width: size, height: size)
            .clipShape(RoundedRectangle(cornerRadius: 12))
    }
    
    private var iconImageName: String {
        switch theme {
        case .light: return "f_light"
        case .dark: return "f_dark"
        case .system: return isDark ? "f_dark" : "f_light"
        }
    }
}

#Preview {
    VStack(spacing: 20) {
        HStack {
            ThemeAwareLogo(theme: .light, isDark: false, size: 40)
            Text("Light Mode")
        }
        
        HStack {
            ThemeAwareLogo(theme: .dark, isDark: true, size: 40)
            Text("Dark Mode")
        }
        
        HStack {
            ThemeAwareAppIcon(theme: .system, isDark: false, size: 60)
            Text("System Mode (Light)")
        }
    }
    .padding()
}
