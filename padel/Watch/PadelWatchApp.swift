import SwiftUI

@main
struct PadelWatchApp: App {
    @State private var session = MatchSession()

    var body: some Scene {
        WindowGroup {
            WatchRootView()
                .environment(session)
        }
    }
}

struct WatchRootView: View {
    @Environment(MatchSession.self) private var session

    var body: some View {
        switch session.phase {
        case .setup:
            NavigationStack { SetupView() }
        case .playing:
            LiveMatchView()
        case .summary(let summary):
            NavigationStack { SummaryView(summary: summary) }
        }
    }
}
