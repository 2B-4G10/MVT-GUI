import SwiftUI

@main
struct MVTGUIApp: App {
    @StateObject private var appState = AppState()
    @StateObject private var environment = MVTEnvironment()
    @StateObject private var indicators = IndicatorStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .environmentObject(appState.runner)
                .environmentObject(environment)
                .environmentObject(indicators)
                .frame(minWidth: 980, minHeight: 660)
                .onAppear { environment.refresh() }
                .followsAppearance()
        }
        .commands {
            SidebarCommands()
        }

        Settings {
            SettingsView()
                .environmentObject(environment)
                .followsAppearance()
        }
    }
}
