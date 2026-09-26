import Foundation
import SwiftData
import PadelKit

@Model
final class Player {
    @Attribute(.unique) var id: UUID
    var name: String
    var createdAt: Date

    init(id: UUID = UUID(), name: String, createdAt: Date = Date()) {
        self.id = id
        self.name = name
        self.createdAt = createdAt
    }

    var record: PlayerRecord { PlayerRecord(id: id, name: name, createdAt: createdAt) }
}

/// I giocatori sono referenziati per UUID (non con relazioni SwiftData):
/// cosi' backup, import e partite arrivate dal Watch restano semplici.
@Model
final class Match {
    @Attribute(.unique) var id: UUID
    var date: Date
    var club: String
    var court: String
    var partnerID: UUID?
    var opponent1ID: UUID?
    var opponent2ID: UUID?
    var deuceRuleRaw: String
    var formatRaw: String
    var firstServerRaw: String
    var indoor: Bool
    /// `[SetScore]` in JSON: evita i limiti di SwiftData sugli array di struct.
    var setsData: Data
    var duration: TimeInterval
    var activeCalories: Double?
    var averageHeartRate: Double?
    var maxHeartRate: Double?
    var notes: String
    var sourceRaw: String

    init(record r: MatchRecord) {
        id = r.id
        date = r.date
        club = r.club
        court = r.court
        partnerID = r.partnerID
        opponent1ID = r.opponent1ID
        opponent2ID = r.opponent2ID
        deuceRuleRaw = r.rules.deuceRule.rawValue
        formatRaw = r.rules.format.rawValue
        firstServerRaw = r.rules.firstServer.rawValue
        indoor = r.rules.indoor
        setsData = (try? JSONEncoder().encode(r.sets)) ?? Data()
        duration = r.duration
        activeCalories = r.activeCalories
        averageHeartRate = r.averageHeartRate
        maxHeartRate = r.maxHeartRate
        notes = r.notes
        sourceRaw = r.source.rawValue
    }

    var sets: [SetScore] {
        get { (try? JSONDecoder().decode([SetScore].self, from: setsData)) ?? [] }
        set { setsData = (try? JSONEncoder().encode(newValue)) ?? Data() }
    }

    var rules: MatchRules {
        get {
            MatchRules(deuceRule: DeuceRule(rawValue: deuceRuleRaw) ?? .goldenPoint,
                       format: MatchFormat(rawValue: formatRaw) ?? .bestOfThree,
                       firstServer: Team(rawValue: firstServerRaw) ?? .us,
                       indoor: indoor)
        }
        set {
            deuceRuleRaw = newValue.deuceRule.rawValue
            formatRaw = newValue.format.rawValue
            firstServerRaw = newValue.firstServer.rawValue
            indoor = newValue.indoor
        }
    }

    var source: MatchSource { MatchSource(rawValue: sourceRaw) ?? .manual }
    var result: Team? { sets.winnerBySets }

    /// Arrivata dal Watch e non ancora completata con compagno e avversari.
    var needsDetails: Bool {
        source == .watch && (partnerID == nil || (opponent1ID == nil && opponent2ID == nil))
    }

    var record: MatchRecord {
        MatchRecord(id: id, date: date, club: club, court: court, partnerID: partnerID,
                    opponent1ID: opponent1ID, opponent2ID: opponent2ID, rules: rules, sets: sets,
                    duration: duration, activeCalories: activeCalories, averageHeartRate: averageHeartRate,
                    maxHeartRate: maxHeartRate, notes: notes, source: source)
    }

    func update(from r: MatchRecord) {
        date = r.date
        club = r.club
        court = r.court
        partnerID = r.partnerID
        opponent1ID = r.opponent1ID
        opponent2ID = r.opponent2ID
        rules = r.rules
        sets = r.sets
        duration = r.duration
        activeCalories = r.activeCalories
        averageHeartRate = r.averageHeartRate
        maxHeartRate = r.maxHeartRate
        notes = r.notes
    }
}

extension MatchRecord {
    /// Una partita del Watch diventa una partita "da completare".
    init(summary s: WatchMatchSummary) {
        // Un set interrotto non conta come set vinto o perso: finisce nelle note.
        var notes = ""
        if let partial = s.unfinishedSet, partial.us + partial.them > 0 {
            notes = "Partita terminata dal Watch con il set in corso sul \(partial.us)-\(partial.them)."
        }
        self.init(id: s.id, date: s.startDate, rules: s.rules, sets: s.sets, duration: s.duration,
                  activeCalories: s.activeCalories, averageHeartRate: s.averageHeartRate,
                  maxHeartRate: s.maxHeartRate, notes: notes, source: .watch)
    }
}
