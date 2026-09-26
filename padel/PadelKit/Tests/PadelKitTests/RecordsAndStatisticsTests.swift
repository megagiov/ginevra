import XCTest
@testable import PadelKit

final class RecordsAndStatisticsTests: XCTestCase {

    private var calendar: Calendar {
        var c = Calendar(identifier: .gregorian)
        c.timeZone = TimeZone(identifier: "Europe/Rome")!
        return c
    }

    private func date(_ y: Int, _ m: Int, _ d: Int) -> Date {
        calendar.date(from: DateComponents(year: y, month: m, day: d, hour: 18))!
    }

    private let win = [SetScore(us: 6, them: 4), SetScore(us: 6, them: 3)]
    private let loss = [SetScore(us: 4, them: 6), SetScore(us: 7, them: 6, tiebreakUs: 7, tiebreakThem: 2),
                        SetScore(us: 0, them: 1, tiebreakUs: 5, tiebreakThem: 10, isSuperTiebreak: true)]

    // MARK: - Trasferimento Watch -> iPhone

    func testWatchSummaryRoundTripsThroughUserInfo() throws {
        let summary = WatchMatchSummary(
            id: UUID(), startDate: date(2026, 9, 1), endDate: date(2026, 9, 1).addingTimeInterval(5400),
            rules: MatchRules(deuceRule: .advantages, format: .twoSetsSuperTiebreak, firstServer: .them, indoor: true),
            sets: loss, winner: .them, activeCalories: 612, averageHeartRate: 138, maxHeartRate: 176)
        let info = try summary.userInfo()
        XCTAssertTrue(info[WatchMatchSummary.userInfoKey] is Data, "Deve essere un tipo property-list")
        XCTAssertEqual(try WatchMatchSummary.from(userInfo: info), summary)
        XCTAssertEqual(summary.duration, 5400)
        XCTAssertNil(try WatchMatchSummary.from(userInfo: ["altro": 1]))
    }

    // MARK: - Backup

    func testBackupRoundTripAndMergeByUUID() throws {
        // Date a secondi interi: il JSON usa ISO8601 senza frazioni.
        let anna = PlayerRecord(name: "Anna", createdAt: date(2025, 5, 1))
        let bruno = PlayerRecord(name: "Bruno", createdAt: date(2025, 6, 1))
        let m1 = MatchRecord(date: date(2026, 1, 10), partnerID: anna.id, sets: win)
        let m2 = MatchRecord(date: date(2026, 2, 10), partnerID: bruno.id, sets: loss, source: .watch)
        let file = BackupFile(exportedAt: date(2026, 3, 1), players: [anna, bruno], matches: [m1, m2])

        let decoded = try BackupFile.decode(try file.encoded())
        XCTAssertEqual(decoded, file)

        let new = decoded.newItems(existingPlayerIDs: [anna.id], existingMatchIDs: [m1.id])
        XCTAssertEqual(new.players.map(\.name), ["Bruno"])
        XCTAssertEqual(new.matches.map(\.id), [m2.id])
    }

    func testBackupFromNewerVersionIsRejected() throws {
        var file = BackupFile(players: [], matches: [])
        file.version = 99
        XCTAssertThrowsError(try BackupFile.decode(try file.encoded()))
    }

    // MARK: - Set e risultato

    func testSetDisplayAndWinner() {
        XCTAssertEqual(win.display, "6-4  6-3")
        XCTAssertEqual(loss.compactDisplay, "4-6 7-6 [5-10]")
        XCTAssertEqual(win.winnerBySets, .us)
        XCTAssertEqual(loss.winnerBySets, .them)
        XCTAssertEqual(loss.setsWon, 1)
        XCTAssertEqual(loss.setsLost, 2)
        XCTAssertNil([SetScore(us: 6, them: 2), SetScore(us: 2, them: 6)].winnerBySets)
    }

    // MARK: - Statistiche

    func testStatisticsTotalsStreakAndMonths() {
        let anna = UUID(), bruno = UUID(), carlo = UUID(), dario = UUID()
        let names = [anna: "Anna", bruno: "Bruno", carlo: "Carlo", dario: "Dario"]
        let matches = [
            MatchRecord(date: date(2026, 1, 5), partnerID: anna, opponent1ID: carlo, opponent2ID: dario, sets: win, duration: 3600, activeCalories: 500),
            MatchRecord(date: date(2026, 1, 20), partnerID: anna, opponent1ID: carlo, sets: loss, duration: 5400, activeCalories: 700),
            MatchRecord(date: date(2026, 2, 3), partnerID: anna, opponent1ID: carlo, sets: win, duration: 3600),
            MatchRecord(date: date(2026, 2, 9), partnerID: bruno, sets: win, duration: 1800),
            MatchRecord(date: date(2026, 3, 1), partnerID: anna, sets: win, duration: 1800),
            // Senza vincitore (interrotta sull'1-1): esclusa.
            MatchRecord(date: date(2026, 3, 2), sets: [SetScore(us: 6, them: 2), SetScore(us: 2, them: 6)])
        ]
        let s = PadelStatistics(matches: matches, playerNames: names, period: .allTime,
                                now: date(2026, 3, 10), calendar: calendar)
        XCTAssertEqual(s.played, 5)
        XCTAssertEqual(s.won, 4)
        XCTAssertEqual(s.lost, 1)
        XCTAssertEqual(s.winPercentage, 80, accuracy: 0.001)
        XCTAssertEqual(s.setsWon, 9)
        XCTAssertEqual(s.setsLost, 2)
        XCTAssertEqual(s.hoursOnCourt, 4.5, accuracy: 0.001)
        XCTAssertEqual(s.totalCalories, 1200)
        XCTAssertEqual(s.streak, .wins(3))
        XCTAssertEqual(s.months.map { [$0.won, $0.lost] }, [[1, 1], [2, 0], [1, 0]])
        XCTAssertEqual(s.winRateTrend.map(\.percentage), [100, 50, 2.0 / 3 * 100, 75, 80])

        // Bruno ha il 100% ma una sola partita: il migliore e' Anna.
        XCTAssertEqual(s.partners.first?.name, "Bruno")
        XCTAssertEqual(s.bestPartner?.name, "Anna")
        XCTAssertEqual(s.bestPartner?.played, 4)

        let carloRecord = s.opponents.first { $0.name == "Carlo" }
        XCTAssertEqual(carloRecord?.won, 2)
        XCTAssertEqual(carloRecord?.lost, 1)
        XCTAssertEqual(s.opponents.first?.name, "Carlo", "Ordinati per partite giocate")
    }

    func testStatisticsPeriodFilter() {
        let matches = [
            MatchRecord(date: date(2024, 6, 1), sets: loss),
            MatchRecord(date: date(2025, 12, 1), sets: win),
            MatchRecord(date: date(2026, 2, 20), sets: loss)
        ]
        let now = date(2026, 3, 10)
        XCTAssertEqual(PadelStatistics(matches: matches, playerNames: [:], period: .allTime, now: now, calendar: calendar).played, 3)
        XCTAssertEqual(PadelStatistics(matches: matches, playerNames: [:], period: .last12Months, now: now, calendar: calendar).played, 2)
        let recent = PadelStatistics(matches: matches, playerNames: [:], period: .last3Months, now: now, calendar: calendar)
        XCTAssertEqual(recent.played, 1)
        XCTAssertEqual(recent.streak, .losses(1))
        XCTAssertNil(recent.bestPartner)
    }

    func testEmptyStatistics() {
        let s = PadelStatistics(matches: [], playerNames: [:], period: .allTime)
        XCTAssertEqual(s.played, 0)
        XCTAssertEqual(s.winPercentage, 0)
        XCTAssertEqual(s.streak, .none)
    }
}
