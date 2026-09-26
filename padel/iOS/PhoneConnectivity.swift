import Foundation
import Observation
import SwiftData
import WatchConnectivity
import PadelKit

/// Riceve le partite dal Watch. I metodi del delegate arrivano su una coda
/// di sistema: sono `nonisolated`, decodificano li' e poi saltano sul
/// MainActor per toccare SwiftData.
@MainActor
@Observable
final class PhoneConnectivity: NSObject {
    private let container: ModelContainer
    private(set) var lastReceived: Date?
    private(set) var isWatchAppInstalled = false

    init(container: ModelContainer) {
        self.container = container
        super.init()
    }

    func activate() {
        guard WCSession.isSupported() else { return }
        let session = WCSession.default
        session.delegate = self
        session.activate()
    }

    private func receive(_ summary: WatchMatchSummary) {
        if MatchStore.insertIfNew(summary, in: container.mainContext) {
            lastReceived = Date()
        }
    }

    private func updateState(installed: Bool) {
        isWatchAppInstalled = installed
    }
}

extension PhoneConnectivity: WCSessionDelegate {
    nonisolated func session(_ session: WCSession, activationDidCompleteWith activationState: WCSessionActivationState, error: Error?) {
        let installed = session.isWatchAppInstalled
        Task { @MainActor in self.updateState(installed: installed) }
    }

    nonisolated func sessionWatchStateDidChange(_ session: WCSession) {
        let installed = session.isWatchAppInstalled
        Task { @MainActor in self.updateState(installed: installed) }
    }

    nonisolated func sessionDidBecomeInactive(_ session: WCSession) {}

    nonisolated func sessionDidDeactivate(_ session: WCSession) {
        // Cambio di Watch associato: si riattiva per quello nuovo.
        session.activate()
    }

    nonisolated func session(_ session: WCSession, didReceiveUserInfo userInfo: [String: Any]) {
        guard let summary = try? WatchMatchSummary.from(userInfo: userInfo) else { return }
        Task { @MainActor in self.receive(summary) }
    }
}
