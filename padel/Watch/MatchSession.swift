import Foundation
import Observation
import WatchKit
import PadelKit

/// Stato della partita sul Watch. Il punteggio vive in `MatchEngine`;
/// qui si gestiscono ciclo di vita, salvataggio, aptica e invio.
@MainActor
@Observable
final class MatchSession {
    enum Phase: Equatable {
        case setup
        case playing
        case summary(WatchMatchSummary)
    }

    private(set) var phase: Phase = .setup
    private(set) var engine = MatchEngine(rules: MatchRules())
    private(set) var matchID = UUID()
    private(set) var startDate = Date()
    private(set) var isFinishing = false

    let workout = WorkoutManager()
    let sender = WatchSender()

    private static let savedKey = "padel.inProgress.v1"

    /// Partita in corso salvata dopo ogni punto: se l'app si chiude,
    /// alla riapertura si riprende da dove si era rimasti.
    private struct Saved: Codable {
        var id: UUID
        var startDate: Date
        var engine: MatchEngine
    }

    init() {
        sender.activate()
        // Solo per gli screenshot automatici: partita a meta' del secondo set.
        if ProcessInfo.processInfo.arguments.contains("-demo") {
            var demo = MatchEngine(rules: MatchRules(deuceRule: .goldenPoint, format: .bestOfThree, firstServer: .us))
            let script: [(Team, Int)] = [(.us, 4), (.them, 4), (.us, 4), (.us, 4), (.them, 4), (.us, 4), (.them, 4), (.us, 4), (.them, 4), (.us, 4),
                                         (.them, 4), (.us, 4), (.us, 4), (.them, 4), (.them, 4), (.us, 2), (.them, 3)]
            for (team, points) in script { for _ in 0..<points { demo.point(for: team) } }
            engine = demo
            startDate = Date().addingTimeInterval(-47 * 60 - 12)
            phase = .playing
            return
        }
        if let data = UserDefaults.standard.data(forKey: Self.savedKey),
           let saved = try? JSONDecoder().decode(Saved.self, from: data) {
            matchID = saved.id
            startDate = saved.startDate
            engine = saved.engine
            phase = .playing
            Task { await workout.start(indoor: saved.engine.rules.indoor, at: Date()) }
        }
    }

    var state: MatchState { engine.state }

    // MARK: - Ciclo di vita

    func start(rules: MatchRules) {
        engine = MatchEngine(rules: rules)
        matchID = UUID()
        startDate = Date()
        phase = .playing
        save()
        WKInterfaceDevice.current().play(.start)
        Task { await workout.start(indoor: rules.indoor, at: startDate) }
    }

    /// Chiude la partita (vinta o interrotta), salva l'allenamento e
    /// accoda il riepilogo per l'iPhone.
    func finish() async {
        guard phase == .playing, !isFinishing else { return }
        isFinishing = true
        defer { isFinishing = false }
        let end = Date()
        await workout.stop(at: end)

        let s = engine.state
        let unfinished = s.isFinished || s.gamesUs + s.gamesThem == 0
            ? nil : SetScore(us: s.gamesUs, them: s.gamesThem)
        let m = workout.metrics
        let summary = WatchMatchSummary(
            id: matchID, startDate: startDate, endDate: end, rules: engine.rules,
            sets: s.completedSets, unfinishedSet: unfinished, winner: s.winner,
            activeCalories: m.activeCalories, averageHeartRate: m.averageHeartRate,
            maxHeartRate: m.maxHeartRate)
        sender.send(summary)
        UserDefaults.standard.removeObject(forKey: Self.savedKey)
        WKInterfaceDevice.current().play(.stop)
        phase = .summary(summary)
    }

    func newMatch() {
        workout.reset()
        phase = .setup
    }

    // MARK: - Punteggio

    func point(for team: Team) {
        let outcome = engine.point(for: team)
        let device = WKInterfaceDevice.current()
        switch outcome {
        case .ignored: return
        case .point: device.play(.click)
        case .game: device.play(.directionUp)
        case .set: device.play(.success)
        case .match: device.play(.notification)
        }
        save()
    }

    func undo() {
        guard engine.canUndo else { return }
        engine.undoLastPoint()
        WKInterfaceDevice.current().play(.retry)
        save()
    }

    func switchServer() {
        engine.setServer(engine.state.server.opponent)
        WKInterfaceDevice.current().play(.click)
        save()
    }

    private func save() {
        let saved = Saved(id: matchID, startDate: startDate, engine: engine)
        if let data = try? JSONEncoder().encode(saved) {
            UserDefaults.standard.set(data, forKey: Self.savedKey)
        }
    }
}
