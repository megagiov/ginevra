import Foundation

public enum MatchSource: String, Codable, Sendable, Hashable {
    case watch
    case manual
}

/// Riepilogo di fine partita spedito dal Watch all'iPhone.
/// L'`id` nasce sul Watch all'inizio della partita: l'iPhone lo usa per
/// scartare i doppioni.
public struct WatchMatchSummary: Codable, Equatable, Sendable, Identifiable {
    public var id: UUID
    public var startDate: Date
    public var endDate: Date
    public var rules: MatchRules
    public var sets: [SetScore]
    /// Set interrotto quando la partita e' stata terminata a meta'.
    public var unfinishedSet: SetScore?
    public var winner: Team?
    public var activeCalories: Double?
    public var averageHeartRate: Double?
    public var maxHeartRate: Double?

    public init(id: UUID, startDate: Date, endDate: Date, rules: MatchRules, sets: [SetScore],
                unfinishedSet: SetScore? = nil, winner: Team?, activeCalories: Double? = nil,
                averageHeartRate: Double? = nil, maxHeartRate: Double? = nil) {
        self.id = id
        self.startDate = startDate
        self.endDate = endDate
        self.rules = rules
        self.sets = sets
        self.unfinishedSet = unfinishedSet
        self.winner = winner
        self.activeCalories = activeCalories
        self.averageHeartRate = averageHeartRate
        self.maxHeartRate = maxHeartRate
    }

    public var duration: TimeInterval { endDate.timeIntervalSince(startDate) }

    /// Chiave usata nel dizionario di `transferUserInfo`.
    public static let userInfoKey = "padel.matchSummary.v1"

    /// `transferUserInfo` accetta solo tipi property-list: il riepilogo
    /// viaggia come JSON dentro un `Data`.
    public func userInfo() throws -> [String: Any] {
        [Self.userInfoKey: try PadelJSON.encoder.encode(self)]
    }

    public static func from(userInfo: [String: Any]) throws -> WatchMatchSummary? {
        guard let data = userInfo[userInfoKey] as? Data else { return nil }
        return try PadelJSON.decoder.decode(WatchMatchSummary.self, from: data)
    }
}

// MARK: - Backup

public struct PlayerRecord: Codable, Equatable, Sendable, Identifiable {
    public var id: UUID
    public var name: String
    public var createdAt: Date

    public init(id: UUID = UUID(), name: String, createdAt: Date = Date()) {
        self.id = id
        self.name = name
        self.createdAt = createdAt
    }
}

/// Una partita in forma indipendente dal database: usata per backup,
/// import e calcolo delle statistiche.
public struct MatchRecord: Codable, Equatable, Sendable, Identifiable {
    public var id: UUID
    public var date: Date
    public var club: String
    public var court: String
    public var partnerID: UUID?
    public var opponent1ID: UUID?
    public var opponent2ID: UUID?
    public var rules: MatchRules
    public var sets: [SetScore]
    public var duration: TimeInterval
    public var activeCalories: Double?
    public var averageHeartRate: Double?
    public var maxHeartRate: Double?
    public var notes: String
    public var source: MatchSource

    public init(id: UUID = UUID(), date: Date, club: String = "", court: String = "",
                partnerID: UUID? = nil, opponent1ID: UUID? = nil, opponent2ID: UUID? = nil,
                rules: MatchRules = MatchRules(), sets: [SetScore], duration: TimeInterval = 0,
                activeCalories: Double? = nil, averageHeartRate: Double? = nil, maxHeartRate: Double? = nil,
                notes: String = "", source: MatchSource = .manual) {
        self.id = id
        self.date = date
        self.club = club
        self.court = court
        self.partnerID = partnerID
        self.opponent1ID = opponent1ID
        self.opponent2ID = opponent2ID
        self.rules = rules
        self.sets = sets
        self.duration = duration
        self.activeCalories = activeCalories
        self.averageHeartRate = averageHeartRate
        self.maxHeartRate = maxHeartRate
        self.notes = notes
        self.source = source
    }

    public var result: Team? { sets.winnerBySets }
}

public struct BackupFile: Codable, Equatable, Sendable {
    public static let currentVersion = 1

    public var version: Int
    public var exportedAt: Date
    public var players: [PlayerRecord]
    public var matches: [MatchRecord]

    public init(exportedAt: Date = Date(), players: [PlayerRecord], matches: [MatchRecord]) {
        self.version = Self.currentVersion
        self.exportedAt = exportedAt
        self.players = players
        self.matches = matches
    }

    public func encoded() throws -> Data {
        let encoder = PadelJSON.encoder
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return try encoder.encode(self)
    }

    public static func decode(_ data: Data) throws -> BackupFile {
        let file = try PadelJSON.decoder.decode(BackupFile.self, from: data)
        guard file.version <= currentVersion else { throw BackupError.newerVersion(file.version) }
        return file
    }

    /// Cosa aggiungere al database: solo gli elementi con UUID nuovo.
    /// Quelli gia' presenti non vengono toccati.
    public func newItems(existingPlayerIDs: Set<UUID>, existingMatchIDs: Set<UUID>) -> (players: [PlayerRecord], matches: [MatchRecord]) {
        (players.filter { !existingPlayerIDs.contains($0.id) },
         matches.filter { !existingMatchIDs.contains($0.id) })
    }
}

public enum BackupError: LocalizedError, Equatable {
    case newerVersion(Int)

    public var errorDescription: String? {
        switch self {
        case .newerVersion(let v):
            "Il backup è stato creato da una versione più recente dell'app (formato \(v))."
        }
    }
}

public enum PadelJSON {
    public static var encoder: JSONEncoder {
        let e = JSONEncoder()
        e.dateEncodingStrategy = .iso8601
        return e
    }

    public static var decoder: JSONDecoder {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .iso8601
        return d
    }
}
