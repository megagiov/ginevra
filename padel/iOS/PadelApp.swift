import SwiftUI
import SwiftData

@main
struct PadelApp: App {
    private let container: ModelContainer
    private let connectivity: PhoneConnectivity

    init() {
        do {
            container = try ModelContainer(for: Match.self, Player.self)
        } catch {
            fatalError("Impossibile aprire il database: \(error)")
        }
        // Va attivata subito: le partite accodate dal Watch con
        // transferUserInfo arrivano appena la sessione e' attiva.
        DemoData.seedIfNeeded(container.mainContext)
        connectivity = PhoneConnectivity(container: container)
        connectivity.activate()
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(connectivity)
        }
        .modelContainer(container)
    }
}

struct RootView: View {
    @State private var tab = DemoData.initialTab

    var body: some View {
        TabView(selection: $tab) {
            MatchListView()
                .tabItem { Label("Partite", systemImage: "list.bullet.rectangle") }
                .tag(0)
            StatsView()
                .tabItem { Label("Statistiche", systemImage: "chart.bar.xaxis") }
                .tag(1)
            SettingsView()
                .tabItem { Label("Impostazioni", systemImage: "gearshape") }
                .tag(2)
        }
        .tint(Theme.win)
    }
}
