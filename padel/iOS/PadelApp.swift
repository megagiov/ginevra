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
    var body: some View {
        TabView {
            MatchListView()
                .tabItem { Label("Partite", systemImage: "list.bullet.rectangle") }
            StatsView()
                .tabItem { Label("Statistiche", systemImage: "chart.bar.xaxis") }
            SettingsView()
                .tabItem { Label("Impostazioni", systemImage: "gearshape") }
        }
        .tint(Theme.win)
    }
}
