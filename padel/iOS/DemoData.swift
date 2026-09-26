import Foundation
import SwiftData
import PadelKit

/// Dati di esempio per gli screenshot automatici (argomento di avvio `-demo`).
/// Non viene mai usato nell'uso normale.
@MainActor
enum DemoData {
    static var isEnabled: Bool { ProcessInfo.processInfo.arguments.contains("-demo") }

    /// Scheda iniziale per gli screenshot: `-tab 1` apre le statistiche.
    static var initialTab: Int {
        let args = ProcessInfo.processInfo.arguments
        guard let i = args.firstIndex(of: "-tab"), i + 1 < args.count else { return 0 }
        return Int(args[i + 1]) ?? 0
    }

    static func seedIfNeeded(_ context: ModelContext) {
        guard isEnabled, ((try? context.fetchCount(FetchDescriptor<Match>())) ?? 0) == 0 else { return }
        let names = ["Luca", "Marco", "Giulia", "Andrea", "Sara", "Paolo"]
        let players = names.map { Player(name: $0) }
        players.forEach(context.insert)
        let id = Dictionary(uniqueKeysWithValues: players.map { ($0.name, $0.id) })
        let calendar = Calendar.current
        let now = Date()

        let results: [[SetScore]] = [
            [SetScore(us: 6, them: 4), SetScore(us: 6, them: 3)],
            [SetScore(us: 4, them: 6), SetScore(us: 7, them: 6, tiebreakUs: 7, tiebreakThem: 4),
             SetScore(us: 1, them: 0, tiebreakUs: 10, tiebreakThem: 7, isSuperTiebreak: true)],
            [SetScore(us: 3, them: 6), SetScore(us: 5, them: 7)],
            [SetScore(us: 6, them: 2), SetScore(us: 6, them: 4)],
            [SetScore(us: 7, them: 5), SetScore(us: 2, them: 6), SetScore(us: 6, them: 3)],
            [SetScore(us: 6, them: 7, tiebreakUs: 5, tiebreakThem: 7), SetScore(us: 4, them: 6)],
            [SetScore(us: 6, them: 1), SetScore(us: 6, them: 3)],
            [SetScore(us: 6, them: 4), SetScore(us: 3, them: 6), SetScore(us: 7, them: 5)],
            [SetScore(us: 6, them: 3), SetScore(us: 6, them: 4)]
        ]
        let partners = ["Luca", "Luca", "Marco", "Luca", "Giulia", "Marco", "Luca", "Giulia", "Luca"]
        let opponents = [("Andrea", "Sara"), ("Paolo", "Andrea"), ("Sara", "Paolo"), ("Andrea", "Paolo"),
                         ("Sara", "Andrea"), ("Paolo", "Sara"), ("Andrea", "Sara"), ("Paolo", "Andrea"), ("Sara", "Paolo")]
        for (i, sets) in results.enumerated() {
            let date = calendar.date(byAdding: .day, value: -(results.count - i) * 17, to: now) ?? now
            let isLast = i == results.count - 1
            let record = MatchRecord(
                date: date, club: "Padel Club Vegasi", court: "Campo \(i % 3 + 1)",
                partnerID: isLast ? nil : id[partners[i]],
                opponent1ID: isLast ? nil : id[opponents[i].0], opponent2ID: isLast ? nil : id[opponents[i].1],
                rules: MatchRules(deuceRule: .goldenPoint, format: i == 1 ? .twoSetsSuperTiebreak : .bestOfThree),
                sets: sets, duration: TimeInterval(70 + i * 5) * 60, activeCalories: Double(520 + i * 23),
                averageHeartRate: 138, maxHeartRate: 171, source: isLast ? .watch : .manual)
            context.insert(Match(record: record))
        }
        try? context.save()
    }
}
