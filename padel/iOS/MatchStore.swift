import Foundation
import SwiftData
import PadelKit

/// Operazioni sul database che non appartengono a una singola vista.
@MainActor
enum MatchStore {
    /// Inserisce la partita del Watch solo se il suo UUID non c'e' gia'.
    @discardableResult
    static func insertIfNew(_ summary: WatchMatchSummary, in context: ModelContext) -> Bool {
        guard !matchExists(summary.id, in: context) else { return false }
        context.insert(Match(record: MatchRecord(summary: summary)))
        try? context.save()
        return true
    }

    static func matchExists(_ id: UUID, in context: ModelContext) -> Bool {
        var descriptor = FetchDescriptor<Match>(predicate: #Predicate { $0.id == id })
        descriptor.fetchLimit = 1
        return ((try? context.fetchCount(descriptor)) ?? 0) > 0
    }

    static func backupData(players: [Player], matches: [Match]) throws -> Data {
        try BackupFile(players: players.map(\.record), matches: matches.map(\.record)).encoded()
    }

    /// Unisce un backup al database: aggiunge solo cio' che manca (per UUID).
    static func importBackup(_ data: Data, into context: ModelContext) throws -> (players: Int, matches: Int) {
        let file = try BackupFile.decode(data)
        let playerIDs = Set(try context.fetch(FetchDescriptor<Player>()).map(\.id))
        let matchIDs = Set(try context.fetch(FetchDescriptor<Match>()).map(\.id))
        let new = file.newItems(existingPlayerIDs: playerIDs, existingMatchIDs: matchIDs)
        for p in new.players {
            context.insert(Player(id: p.id, name: p.name, createdAt: p.createdAt))
        }
        for m in new.matches {
            context.insert(Match(record: m))
        }
        try context.save()
        return (new.players.count, new.matches.count)
    }

    /// Elimina un giocatore togliendolo dalle partite in cui compare.
    static func delete(_ player: Player, in context: ModelContext) {
        let id = player.id
        let matches = (try? context.fetch(FetchDescriptor<Match>())) ?? []
        for m in matches {
            if m.partnerID == id { m.partnerID = nil }
            if m.opponent1ID == id { m.opponent1ID = nil }
            if m.opponent2ID == id { m.opponent2ID = nil }
        }
        context.delete(player)
        try? context.save()
    }

    static func names(of players: [Player]) -> [UUID: String] {
        Dictionary(players.map { ($0.id, $0.name) }, uniquingKeysWith: { first, _ in first })
    }
}
