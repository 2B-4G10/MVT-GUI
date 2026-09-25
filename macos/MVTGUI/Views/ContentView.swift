import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var appState: AppState
    @EnvironmentObject private var environment: MVTEnvironment

    var body: some View {
        NavigationSplitView {
            List(selection: $appState.selection) {
                Section {
                    row("Setup", systemImage: "wrench.and.screwdriver", item: .setup)
                    row("Indicators", systemImage: "shield.checkered", item: .indicators)
                    row("Results", systemImage: "list.bullet.rectangle", item: .results)
                }
                Section {
                    ForEach(MVTCommand.iosCommands) { command in
                        row(command.title, systemImage: command.systemImage, item: .command(command), color: command.accent)
                    }
                } header: {
                    SidebarHeader(title: "iOS") {
                        Image(systemName: "apple.logo")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(.primary)
                    }
                }
                Section {
                    ForEach(MVTCommand.androidCommands) { command in
                        row(command.title, systemImage: command.systemImage, item: .command(command), color: command.accent)
                    }
                } header: {
                    SidebarHeader(title: "Android") {
                        AndroidLogo()
                            .frame(width: 17, height: 11)
                    }
                }
            }
            .listStyle(.sidebar)
            .navigationSplitViewColumnWidth(min: 210, ideal: 230)
            .safeAreaInset(edge: .bottom) {
                MVTStatusFooter()
            }
        } detail: {
            switch appState.selection {
            case .setup, nil:
                SetupView()
            case .results:
                ResultsView()
            case .indicators:
                IndicatorsView()
            case .command(let command):
                CommandView(form: appState.form(for: command))
                    .id(command)
            }
        }
    }

    private func row(_ title: String, systemImage: String, item: SidebarItem, color: Color? = nil) -> some View {
        SidebarRow(title: title, systemImage: systemImage, color: color, isSelected: appState.selection == item)
            .tag(item)
    }
}

/// A sidebar row with a slightly larger, coloured icon. The icon turns
/// the selection's text colour while its row is highlighted, so it never
/// blends into the highlight.
private struct SidebarRow: View {
    let title: String
    let systemImage: String
    var color: Color?
    var isSelected = false

    var body: some View {
        Label {
            Text(title)
        } icon: {
            Image(systemName: systemImage)
                .font(.system(size: 15))
                .foregroundStyle(iconStyle)
                .frame(width: 22)
        }
    }

    private var iconStyle: AnyShapeStyle {
        if let color, !isSelected {
            return AnyShapeStyle(color)
        }
        return AnyShapeStyle(.primary)
    }
}

/// A sidebar section title with the platform's logo beside it.
private struct SidebarHeader<Logo: View>: View {
    let title: String
    @ViewBuilder let logo: Logo

    var body: some View {
        HStack(spacing: 6) {
            logo
            Text(title)
        }
    }
}

/// The Android robot's head, drawn in Android green (credited in NOTICE).
struct AndroidLogo: View {
    var body: some View {
        Canvas { context, size in
            let unit = min(size.width, size.height / 0.62)
            let origin = CGPoint(x: (size.width - unit) / 2, y: (size.height - unit * 0.62) / 2)
            func point(_ x: CGFloat, _ y: CGFloat) -> CGPoint {
                CGPoint(x: origin.x + x * unit, y: origin.y + y * unit)
            }

            var head = Path()
            head.addRelativeArc(center: point(0.5, 0.62), radius: 0.46 * unit, startAngle: .degrees(180), delta: .degrees(180))
            head.closeSubpath()

            var antennae = Path()
            antennae.move(to: point(0.29, 0.34))
            antennae.addLine(to: point(0.19, 0.05))
            antennae.move(to: point(0.71, 0.34))
            antennae.addLine(to: point(0.81, 0.05))

            let green = GraphicsContext.Shading.color(.androidGreen)
            context.fill(head, with: green)
            context.stroke(antennae, with: green, style: StrokeStyle(lineWidth: 0.075 * unit, lineCap: .round))

            let eye = 0.05 * unit
            var eyes = Path()
            eyes.addEllipse(in: CGRect(x: point(0.33, 0.46).x - eye, y: point(0.33, 0.46).y - eye, width: eye * 2, height: eye * 2))
            eyes.addEllipse(in: CGRect(x: point(0.67, 0.46).x - eye, y: point(0.67, 0.46).y - eye, width: eye * 2, height: eye * 2))
            context.blendMode = .clear
            context.fill(eyes, with: .color(.black))
        }
        .accessibilityLabel("Android")
    }
}

private struct MVTStatusFooter: View {
    @EnvironmentObject private var environment: MVTEnvironment
    @EnvironmentObject private var appState: AppState

    var body: some View {
        HStack(spacing: 8) {
            Button {
                appState.selection = .setup
            } label: {
                HStack(spacing: 6) {
                    switch environment.status {
                    case .found(let version) where environment.isOutdated:
                        Image(systemName: "arrow.up.circle.fill").foregroundStyle(.orange)
                        Text("MVT \(version) · update available")
                    case .found(let version):
                        Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
                        Text("MVT \(version)")
                    case .missing:
                        Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(.orange)
                        Text("MVT not installed")
                    case .checking, .unknown:
                        ProgressView().controlSize(.small)
                        Text("Looking for MVT…")
                    }
                    Spacer(minLength: 0)
                }
                .font(.caption)
                .lineLimit(1)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            DarkModeSwitch()
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
    }
}

/// Switches the app between light and dark. Settings also offers
/// following the system.
private struct DarkModeSwitch: View {
    @AppStorage(Appearance.key) private var appearance = Appearance.system
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        Toggle(isOn: Binding(
            get: { colorScheme == .dark },
            set: { appearance = $0 ? .dark : .light }
        )) {
            Image(systemName: colorScheme == .dark ? "moon.fill" : "sun.max.fill")
                .foregroundStyle(.secondary)
                .frame(width: 14)
        }
        .toggleStyle(.switch)
        .controlSize(.mini)
        .help(colorScheme == .dark ? "Switch to light mode" : "Switch to dark mode")
    }
}

extension Color {
    /// Android's brand green (#3DDC84), used for the Android tools.
    static let androidGreen = Color(red: 61 / 255, green: 220 / 255, blue: 132 / 255)
}

extension MVTCommand {
    /// The colour of a command's icon and Run button: blue for iOS tools,
    /// Android green for Android tools.
    var accent: Color { tool == .android ? .androidGreen : .blue }
}
