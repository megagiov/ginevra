import Foundation

public enum StatsPeriod: String, CaseIterable, Sendable, Identifiable {
    case allTime
    case last12Months
    case last3Months

    public var id: String { rawValue }

    public var label: String {
        switch self {
        case .allTime: "Sempre"
        case .last12Months: "12 mesi"
        case .last3Months: "3 mesi"
        }
    }

    public func startDate(from now: Date, calendar: Calendar = .current) -> Date? {
        switch self {
        case .allTime: nil
        case .last12Months: calendar.date(byAdding: .month, value: -12, to: now)
        case .last3Months: calendar.date(byAdding: .month, value: -3, to: now)
        }
    }
}

public struct MonthBucket: Equatable, Sendable, Identifiable {
    public var month: Date
    public var won: Int
    public var lost: Int
    public var id: Date { month }
}

public struct WinRatePoint: Equatable, Sendable, Identifiable {
    public var date: Date
    /// Percentuale di vittorie cumulata fino a questa partita (0...100).
    public var percentage: Double
    public var index: Int
    public var id: Int { index }
}

public struct PersonRecord: Equatable, Sendable, Identifiable {
    public var playerID: UUID
    public var name: String
    public var won: Int
    public var lost: Int
    public var id: UUID { playerID }
    public var played: Int { won + lost }
    public var winPercentage: Double { played == 0 ? 0 : Double(won) / Double(played) * 100 }
}

public enum Streak: Equatable, Sendable {
    case none
    case wins(Int)
    case losses(Int)

    public var label: String {
        switch self {
        case .none: "—"
        case .wins(let n): n == 1 ? "1 vittoria" : "\(n) vittorie"
        case .losses(let n): n == 1 ? "1 sconfitta" : "\(n) sconfitte"
        }
    }
}

/// Statistiche calcolate solo su risultato e set.
public struct PadelStatistics: Equatable, Sendable {
    public static let minimumMatchesForBestPartner = 3

    public var played = 0
    public var won = 0
    public var lost = 0
    public var setsWon = 0
    public var setsLost = 0
    public var totalDuration: TimeInterval = 0
    public var totalCalories: Double = 0
    public var streak: Streak = .none
    public var months: [MonthBucket] = []
    public var winRateTrend: [WinRatePoint] = []
    public var partners: [PersonRecord] = []
    public var opponents: [PersonRecord] = []

    public var winPercentage: Double { played == 0 ? 0 : Double(won) / Double(played) * 100 }
    public var hoursOnCourt: Double { totalDuration / 3600 }

    /// Miglior compagno: % vittorie piu' alta con almeno 3 partite insieme.
    public var bestPartner: PersonRecord? {
        partners
            .filter { $0.played >= Self.minimumMatchesForBestPartner }
            .max { ($0.winPercentage, $0.played) < ($1.winPercentage, $1.played) }
    }

    public init() {}

    public init(matches all: [MatchRecord], playerNames: [UUID: String], period: StatsPeriod,
                now: Date = Date(), calendar: Calendar = .current) {
        let start = period.startDate(from: now, calendar: calendar)
        // Contano solo le partite con un vincitore.
        let matches = all
            .filter { m in m.result != nil && (start.map { m.date >= $0 } ?? true) }
            .sorted { $0.date < $1.date }

        var monthMap: [Date: MonthBucket] = [:]
        var partnerMap: [UUID: PersonRecord] = [:]
        var opponentMap: [UUID: PersonRecord] = [:]

        func name(_ id: UUID) -> String { playerNames[id] ?? "Giocatore eliminato" }

        for (i, m) in matches.enumerated() {
            let win = m.result == .us
            played += 1
            if win { won += 1 } else { lost += 1 }
            setsWon += m.sets.setsWon
            setsLost += m.sets.setsLost
            totalDuration += m.duration
            totalCalories += m.activeCalories ?? 0

            let monthStart = calendar.date(from: calendar.dateComponents([.year, .month], from: m.date)) ?? m.date
            var bucket = monthMap[monthStart] ?? MonthBucket(month: monthStart, won: 0, lost: 0)
            if win { bucket.won += 1 } else { bucket.lost += 1 }
            monthMap[monthStart] = bucket

            winRateTrend.append(WinRatePoint(date: m.date, percentage: Double(won) / Double(played) * 100, index: i))

            if let p = m.partnerID {
                var r = partnerMap[p] ?? PersonRecord(playerID: p, name: name(p), won: 0, lost: 0)
                if win { r.won += 1 } else { r.lost += 1 }
                partnerMap[p] = r
            }
            for o in Set([m.opponent1ID, m.opponent2ID].compactMap { $0 }) {
                var r = opponentMap[o] ?? PersonRecord(playerID: o, name: name(o), won: 0, lost: 0)
                if win { r.won += 1 } else { r.lost += 1 }
                opponentMap[o] = r
            }
        }

        months = monthMap.values.sorted { $0.month < $1.month }
        partners = partnerMap.values.sorted {
            ($0.winPercentage, $0.played, $1.name) > ($1.winPercentage, $1.played, $0.name)
        }
        opponents = opponentMap.values.sorted {
            ($0.played, $1.name) > ($1.played, $0.name)
        }

        if let last = matches.last?.result {
            let count = matches.reversed().prefix { $0.result == last }.count
            streak = last == .us ? .wins(count) : .losses(count)
        }
    }
}
