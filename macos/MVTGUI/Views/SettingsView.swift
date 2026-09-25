import AppKit
import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var environment: MVTEnvironment
    @AppStorage(Appearance.key) private var appearance = Appearance.system

    var body: some View {
        Form {
            Section {
                PathField(
                    title: "MVT location",
                    path: $environment.customBinDirectory,
                    mode: .folder,
                    placeholder: "Automatic"
                )
                Text("Folder containing mvt-ios and mvt-android, e.g. ~/.local/bin for pipx or uv installs, or a virtualenv's bin folder. Leave empty to search automatically.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                HStack {
                    Spacer()
                    Button("Apply") { environment.refresh() }
                }
            } header: {
                Text("Installation")
            }

            Section("Appearance") {
                Picker("Look", selection: $appearance) {
                    ForEach(Appearance.allCases) { Text($0.title).tag($0) }
                }
                .pickerStyle(.segmented)
            }

            Section("Behavior") {
                Toggle("Check for MVT updates on each run", isOn: $environment.checkForUpdates)
                Toggle("Check for indicator updates on each run", isOn: $environment.checkIndicatorUpdates)
                Toggle("Verbose (debug) output", isOn: $environment.verbose)
            }
        }
        .formStyle(.grouped)
        .frame(width: 520)
        .fixedSize(horizontal: false, vertical: true)
    }
}
