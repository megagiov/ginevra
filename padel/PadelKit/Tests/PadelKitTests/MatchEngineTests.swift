import XCTest
@testable import PadelKit

final class MatchEngineTests: XCTestCase {

    // MARK: - Aiuti

    private func engine(_ deuce: DeuceRule = .goldenPoint, _ format: MatchFormat = .bestOfThree,
                        server: Team = .us) -> MatchEngine {
        MatchEngine(rules: MatchRules(deuceRule: deuce, format: format, firstServer: server))
    }

    private func points(_ e: inout MatchEngine, _ team: Team, _ n: Int) {
        for _ in 0..<n { e.point(for: team) }
    }

    /// Fa vincere un game "a zero" alla squadra indicata.
    private func game(_ e: inout MatchEngine, _ team: Team) {
        points(&e, team, 4)
    }

    /// Porta il set corrente sul punteggio indicato alternando i game.
    private func games(_ e: inout MatchEngine, us: Int, them: Int) {
        var u = 0, t = 0
        while u < us || t < them {
            if u < us { game(&e, .us); u += 1 }
            if t < them { game(&e, .them); t += 1 }
        }
    }

    // MARK: - Game

    func testNormalGameLabels() {
        var e = engine()
        XCTAssertEqual(e.pointLabel(for: .us), "0")
        e.point(for: .us)
        XCTAssertEqual(e.pointLabel(for: .us), "15")
        e.point(for: .us)
        XCTAssertEqual(e.pointLabel(for: .us), "30")
        e.point(for: .them)
        XCTAssertEqual(e.pointLabel(for: .them), "15")
        e.point(for: .us)
        XCTAssertEqual(e.pointLabel(for: .us), "40")
        let outcome = e.point(for: .us)
        XCTAssertEqual(outcome, .game)
        XCTAssertEqual(e.state.gamesUs, 1)
        XCTAssertEqual(e.state.pointsUs, 0)
        XCTAssertEqual(e.state.pointsThem, 0)
    }

    func testAdvantages() {
        var e = engine(.advantages)
        points(&e, .us, 3)
        points(&e, .them, 3)
        XCTAssertEqual(e.pointLabel(for: .us), "40")
        XCTAssertEqual(e.statusLabel, "Parità")
        e.point(for: .us)
        XCTAssertEqual(e.pointLabel(for: .us), "AD")
        XCTAssertEqual(e.pointLabel(for: .them), "40")
        XCTAssertEqual(e.statusLabel, "Vantaggio Noi")
        e.point(for: .them) // torna parita'
        XCTAssertEqual(e.pointLabel(for: .us), "40")
        XCTAssertEqual(e.pointLabel(for: .them), "40")
        XCTAssertEqual(e.state.gamesUs + e.state.gamesThem, 0)
        e.point(for: .them)
        XCTAssertEqual(e.pointLabel(for: .them), "AD")
        XCTAssertEqual(e.point(for: .them), .game)
        XCTAssertEqual(e.state.gamesThem, 1)
    }

    func testGoldenPoint() {
        var e = engine(.goldenPoint)
        points(&e, .us, 3)
        points(&e, .them, 3)
        XCTAssertEqual(e.statusLabel, "Punto d'oro")
        XCTAssertEqual(e.pointLabel(for: .us), "40")
        XCTAssertEqual(e.point(for: .them), .game)
        XCTAssertEqual(e.state.gamesThem, 1)
    }

    // MARK: - Set

    func testSetSixFour() {
        var e = engine()
        games(&e, us: 5, them: 4)
        XCTAssertEqual(e.state.completedSets.count, 0)
        game(&e, .us)
        XCTAssertEqual(e.state.completedSets, [SetScore(us: 6, them: 4)])
        XCTAssertEqual(e.state.gamesUs, 0)
        XCTAssertEqual(e.state.setsWon, 1)
    }

    func testSetSevenFive() {
        var e = engine()
        games(&e, us: 5, them: 5)
        game(&e, .us)          // 6-5: non basta
        XCTAssertEqual(e.state.completedSets.count, 0)
        XCTAssertEqual(e.state.mode, .regular)
        game(&e, .us)          // 7-5
        XCTAssertEqual(e.state.completedSets, [SetScore(us: 7, them: 5)])
    }

    func testTiebreakSevenSix() {
        var e = engine()
        games(&e, us: 6, them: 6)
        XCTAssertEqual(e.state.mode, .tiebreak)
        XCTAssertEqual(e.statusLabel, "Tie-break")
        points(&e, .us, 6)
        points(&e, .them, 6)
        XCTAssertEqual(e.pointLabel(for: .us), "6")
        e.point(for: .us)      // 7-6: servono 2 punti di scarto
        XCTAssertEqual(e.state.completedSets.count, 0)
        XCTAssertEqual(e.point(for: .us), .set) // 8-6
        XCTAssertEqual(e.state.completedSets,
                       [SetScore(us: 7, them: 6, tiebreakUs: 8, tiebreakThem: 6)])
        XCTAssertEqual(e.state.completedSets[0].display, "7-6 (8-6)")
        XCTAssertEqual(e.state.mode, .regular)
    }

    func testTiebreakLostSevenZero() {
        var e = engine()
        games(&e, us: 6, them: 6)
        points(&e, .them, 7)
        XCTAssertEqual(e.state.completedSets, [SetScore(us: 6, them: 7, tiebreakUs: 0, tiebreakThem: 7)])
    }

    // MARK: - Super tie-break

    func testSuperTiebreakStartsAtOneSetAll() {
        var e = engine(.goldenPoint, .twoSetsSuperTiebreak)
        games(&e, us: 6, them: 3)
        games(&e, us: 2, them: 6)
        XCTAssertEqual(e.state.mode, .superTiebreak)
        XCTAssertEqual(e.statusLabel, "Super tie-break")
        points(&e, .us, 9)
        points(&e, .them, 9)
        e.point(for: .us)       // 10-9: non basta
        XCTAssertNil(e.state.winner)
        e.point(for: .them)     // 10-10
        e.point(for: .them)     // 10-11
        XCTAssertEqual(e.point(for: .them), .match) // 10-12
        XCTAssertEqual(e.state.winner, .them)
        XCTAssertEqual(e.state.completedSets.last,
                       SetScore(us: 0, them: 1, tiebreakUs: 10, tiebreakThem: 12, isSuperTiebreak: true))
        XCTAssertEqual(e.state.completedSets.last?.display, "[10-12]")
    }

    func testSuperTiebreakWinAtTen() {
        var e = engine(.goldenPoint, .twoSetsSuperTiebreak)
        games(&e, us: 3, them: 6)
        games(&e, us: 6, them: 4)
        points(&e, .us, 10)
        XCTAssertEqual(e.state.winner, .us)
        XCTAssertEqual(e.statusLabel, "Vittoria")
    }

    func testBestOfThreeHasNoSuperTiebreak() {
        var e = engine(.goldenPoint, .bestOfThree)
        games(&e, us: 6, them: 3)
        games(&e, us: 2, them: 6)
        XCTAssertEqual(e.state.mode, .regular)
        games(&e, us: 6, them: 0)
        XCTAssertEqual(e.state.winner, .us)
        XCTAssertEqual(e.state.completedSets.count, 3)
    }

    // MARK: - Fine partita

    func testMatchEndsTwoSetsToZeroAndIgnoresFurtherPoints() {
        var e = engine()
        games(&e, us: 6, them: 0)
        games(&e, us: 6, them: 0)
        XCTAssertEqual(e.state.winner, .us)
        XCTAssertTrue(e.state.isFinished)
        let before = e
        XCTAssertEqual(e.point(for: .them), .ignored)
        XCTAssertEqual(e, before)
    }

    func testUndoAfterVictoryReopensMatch() {
        var e = engine()
        games(&e, us: 6, them: 0)
        games(&e, us: 5, them: 0)
        points(&e, .us, 3)
        XCTAssertEqual(e.point(for: .us), .match)
        e.undoLastPoint()
        XCTAssertNil(e.state.winner)
        XCTAssertEqual(e.state.completedSets.count, 1)
        XCTAssertEqual(e.state.gamesUs, 5)
        XCTAssertEqual(e.pointLabel(for: .us), "40")
        e.point(for: .them)
        XCTAssertEqual(e.pointLabel(for: .them), "15")
    }

    // MARK: - Servizio

    func testServiceAlternatesEveryGame() {
        var e = engine(server: .them)
        XCTAssertEqual(e.state.server, .them)
        points(&e, .us, 3)
        XCTAssertEqual(e.state.server, .them, "Durante il game non cambia")
        e.point(for: .us)
        XCTAssertEqual(e.state.server, .us)
        game(&e, .them)
        XCTAssertEqual(e.state.server, .them)
    }

    func testServiceContinuesAcrossSets() {
        var e = engine(server: .us)
        games(&e, us: 6, them: 3) // 9 game: l'ultimo lo ha servito "Noi"
        XCTAssertEqual(e.state.completedSets.count, 1)
        XCTAssertEqual(e.state.server, .them)
    }

    func testTiebreakServiceRotation() {
        var e = engine(server: .us)
        games(&e, us: 6, them: 6) // 12 game: il 13° lo serve di nuovo "Noi"
        XCTAssertEqual(e.state.mode, .tiebreak)
        XCTAssertEqual(e.state.server, .us)
        XCTAssertEqual(e.state.tiebreakFirstServer, .us)

        // Sequenza attesa: N, L L, N N, L L, N N ...
        var servers: [Team] = [e.state.server]
        for i in 0..<10 {
            e.point(for: i % 2 == 0 ? .us : .them)
            servers.append(e.state.server)
        }
        XCTAssertEqual(servers, [.us, .them, .them, .us, .us, .them, .them, .us, .us, .them, .them])
    }

    func testFirstGameAfterTiebreakServedByFirstReceiver() {
        var e = engine(server: .us)
        games(&e, us: 6, them: 6)
        XCTAssertEqual(e.state.tiebreakFirstServer, .us)
        points(&e, .us, 7) // 7-0: al punto finale servirebbe "Noi"
        XCTAssertEqual(e.state.completedSets.count, 1)
        XCTAssertEqual(e.state.server, .them, "Serve chi ha risposto per primo nel tie-break")

        // Lo stesso con un tie-break lungo, in cui il servizio "naturale"
        // alla fine sarebbe dell'altra squadra.
        var f = engine(server: .them)
        games(&f, us: 6, them: 6)
        XCTAssertEqual(f.state.tiebreakFirstServer, .them)
        points(&f, .us, 5)
        points(&f, .them, 6)
        points(&f, .us, 3) // 8-6
        XCTAssertEqual(f.state.completedSets.count, 1)
        XCTAssertEqual(f.state.server, .us)
    }

    func testSuperTiebreakServiceRotationAndFirstServer() {
        var e = engine(.goldenPoint, .twoSetsSuperTiebreak, server: .us)
        games(&e, us: 6, them: 0) // 6 game: poi serve "Noi"
        games(&e, us: 0, them: 6) // altri 6: poi serve "Noi"
        XCTAssertEqual(e.state.mode, .superTiebreak)
        XCTAssertEqual(e.state.tiebreakFirstServer, .us)
        e.point(for: .them)
        XCTAssertEqual(e.state.server, .them)
        e.point(for: .them)
        XCTAssertEqual(e.state.server, .them)
        e.point(for: .them)
        XCTAssertEqual(e.state.server, .us)
    }

    func testManualServerCorrection() {
        var e = engine(server: .us)
        e.setServer(.them)
        XCTAssertEqual(e.state.server, .them)
        game(&e, .us)
        XCTAssertEqual(e.state.server, .us, "La rotazione riparte dalla correzione")
    }

    func testManualCorrectionAtTiebreakStartUpdatesFirstServer() {
        var e = engine(server: .us)
        games(&e, us: 6, them: 6)
        e.setServer(.them)
        XCTAssertEqual(e.state.tiebreakFirstServer, .them)
        points(&e, .us, 7)
        XCTAssertEqual(e.state.server, .us)
    }

    // MARK: - Annulla

    func testUndoSinglePoint() {
        var e = engine()
        e.point(for: .us)
        e.point(for: .them)
        e.undoLastPoint()
        XCTAssertEqual(e.state.pointsUs, 1)
        XCTAssertEqual(e.state.pointsThem, 0)
    }

    func testUndoRestoresGameSetAndServer() {
        var e = engine(server: .us)
        games(&e, us: 5, them: 4)
        points(&e, .us, 3)
        let before = e.state
        e.point(for: .us) // chiude il set 6-4
        XCTAssertEqual(e.state.completedSets.count, 1)
        e.undoLastPoint()
        XCTAssertEqual(e.state, before)
    }

    func testUndoIsUnlimitedBackToStart() {
        var e = engine(.advantages, .twoSetsSuperTiebreak, server: .them)
        games(&e, us: 6, them: 6)
        points(&e, .us, 4)
        XCTAssertTrue(e.canUndo)
        while e.canUndo { e.undoLastPoint() }
        XCTAssertEqual(e.state, MatchState(server: .them))
        XCTAssertTrue(e.events.isEmpty)
    }

    func testUndoAlsoDropsLaterServerCorrection() {
        var e = engine(server: .us)
        e.point(for: .us)
        e.setServer(.them)
        e.undoLastPoint()
        XCTAssertEqual(e.state.server, .us)
        XCTAssertTrue(e.events.isEmpty)
        e.undoLastPoint() // senza punti non fa nulla
        XCTAssertFalse(e.canUndo)
    }

    func testEngineRoundTripsThroughJSON() throws {
        var e = engine(.advantages, .twoSetsSuperTiebreak, server: .them)
        games(&e, us: 6, them: 6)
        points(&e, .them, 3)
        let data = try JSONEncoder().encode(e)
        let decoded = try JSONDecoder().decode(MatchEngine.self, from: data)
        XCTAssertEqual(decoded, e)
    }
}
