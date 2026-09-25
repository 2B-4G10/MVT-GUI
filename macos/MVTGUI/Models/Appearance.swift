import AppKit
import SwiftUI

/// The app's light or dark look, stored in the user defaults.
enum Appearance: String, CaseIterable, Identifiable {
    case system, light, dark

    static let key = "appearance"

    var id: Self { self }

    var title: String {
        switch self {
        case .system: return "Match System"
        case .light: return "Light"
        case .dark: return "Dark"
        }
    }

    /// Applies the look to every window. System colours adapt to it, so
    /// text keeps its contrast in both looks.
    func apply() {
        switch self {
        case .system: NSApp.appearance = nil
        case .light: NSApp.appearance = NSAppearance(named: .aqua)
        case .dark: NSApp.appearance = NSAppearance(named: .darkAqua)
        }
    }
}

private struct FollowsAppearance: ViewModifier {
    @AppStorage(Appearance.key) private var appearance = Appearance.system

    func body(content: Content) -> some View {
        content
            .onAppear { appearance.apply() }
            .onChange(of: appearance) { $0.apply() }
    }
}

extension View {
    /// Keeps the app's look in step with the Appearance setting.
    func followsAppearance() -> some View { modifier(FollowsAppearance()) }
}
