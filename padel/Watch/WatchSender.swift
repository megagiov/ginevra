import Foundation
import WatchConnectivity
import PadelKit

/// Invia i riepiloghi all'iPhone con `transferUserInfo`: il sistema li
/// mette in coda e li consegna anche se l'iPhone ora non e' raggiungibile.
/// Se la sessione non e' ancora attiva, il riepilogo resta in attesa
/// (anche su disco) e parte appena si attiva.
@MainActor
final class WatchSender: NSObject {
    private static let pendingKey = "padel.pendingSummaries.v1"

    private var pending: [WatchMatchSummary] {
        get {
            guard let data = UserDefaults.standard.data(forKey: Self.pendingKey) else { return [] }
            return (try? JSONDecoder().decode([WatchMatchSummary].self, from: data)) ?? []
        }
        set {
            UserDefaults.standard.set(try? JSONEncoder().encode(newValue), forKey: Self.pendingKey)
        }
    }

    func activate() {
        guard WCSession.isSupported() else { return }
        WCSession.default.delegate = self
        WCSession.default.activate()
    }

    func send(_ summary: WatchMatchSummary) {
        if !pending.contains(where: { $0.id == summary.id }) {
            pending.append(summary)
        }
        flush()
    }

    private func flush() {
        guard WCSession.isSupported(), WCSession.default.activationState == .activated else { return }
        var left: [WatchMatchSummary] = []
        for summary in pending {
            if let info = try? summary.userInfo() {
                WCSession.default.transferUserInfo(info)
            } else {
                left.append(summary)
            }
        }
        pending = left
    }
}

extension WatchSender: WCSessionDelegate {
    nonisolated func session(_ session: WCSession, activationDidCompleteWith activationState: WCSessionActivationState, error: Error?) {
        guard activationState == .activated else { return }
        Task { @MainActor in self.flush() }
    }
}
