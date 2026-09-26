import Foundation

/// Che tipo di "game" si sta giocando.
public enum GameMode: String, Codable, Sendable, Hashable {
    case regular
    case tiebreak
    case superTiebreak
}

/// Istantanea del punteggio. Tutta la logica sta in `MatchEngine`.
public struct MatchState: Codable, Equatable, Sendable {
    public var completedSets: [SetScore] = []
    public var gamesUs = 0
    public var gamesThem = 0
    /// Punti del game corrente (o del tie-break), come conteggio grezzo.
    public var pointsUs = 0
    public var pointsThem = 0
    public var mode: GameMode = .regular
    public var server: Team
    /// Chi ha servito il primo punto del tie-break in corso.
    public var tiebreakFirstServer: Team?
    public var winner: Team?

    public init(server: Team) {
        self.server = server
    }

    public var setsWon: Int { completedSets.setsWon }
    public var setsLost: Int { completedSets.setsLost }
    public var isFinished: Bool { winner != nil }

    public func games(_ team: Team) -> Int { team == .us ? gamesUs : gamesThem }
    public func points(_ team: Team) -> Int { team == .us ? pointsUs : pointsThem }
    public func sets(_ team: Team) -> Int { team == .us ? setsWon : setsLost }
}

/// Un'azione registrata durante la partita. Lo storico degli eventi e'
/// la fonte di verita': lo stato si ricalcola rigiocandoli, quindi
/// l'annullamento e' sempre esatto e senza limiti.
public enum MatchEvent: Codable, Equatable, Sendable {
    case point(Team)
    case setServer(Team)
}

/// Esito di un punto, utile per il feedback aptico.
public enum PointOutcome: Equatable, Sendable {
    case ignored
    case point
    case game
    case set
    case match
}

/// Motore di punteggio del padel: struct pura, senza dipendenze da UI.
public struct MatchEngine: Codable, Equatable, Sendable {
    public let rules: MatchRules
    public private(set) var events: [MatchEvent] = []
    public private(set) var state: MatchState

    public init(rules: MatchRules) {
        self.rules = rules
        self.state = MatchState(server: rules.firstServer)
    }

    // MARK: - Azioni

    @discardableResult
    public mutating func point(for team: Team) -> PointOutcome {
        guard !state.isFinished else { return .ignored }
        events.append(.point(team))
        return Self.apply(.point(team), to: &state, rules: rules)
    }

    /// Correzione manuale di chi serve adesso. La rotazione riparte da qui.
    public mutating func setServer(_ team: Team) {
        guard state.server != team, !state.isFinished else { return }
        events.append(.setServer(team))
        Self.apply(.setServer(team), to: &state, rules: rules)
    }

    public var canUndo: Bool { events.contains { if case .point = $0 { true } else { false } } }

    /// Annulla l'ultimo punto. Le correzioni di servizio fatte *dopo*
    /// quel punto vengono tolte insieme a lui, perche' si riferivano a
    /// una situazione che non esiste piu'.
    public mutating func undoLastPoint() {
        guard let index = events.lastIndex(where: { if case .point = $0 { true } else { false } }) else { return }
        events.removeSubrange(index...)
        state = Self.replay(events, rules: rules)
    }

    public static func replay(_ events: [MatchEvent], rules: MatchRules) -> MatchState {
        var state = MatchState(server: rules.firstServer)
        for event in events {
            apply(event, to: &state, rules: rules)
        }
        return state
    }

    // MARK: - Visualizzazione

    /// Etichetta del punto nel game: "0", "15", "30", "40", "AD", oppure
    /// il numero nei tie-break.
    public func pointLabel(for team: Team) -> String {
        let mine = state.points(team)
        let theirs = state.points(team.opponent)
        guard state.mode == .regular else { return "\(mine)" }
        if mine >= 3 && theirs >= 3 {
            return mine > theirs ? "AD" : "40"
        }
        return ["0", "15", "30", "40"][min(mine, 3)]
    }

    /// Stato da mostrare sopra il punteggio, se c'e' qualcosa di notevole.
    public var statusLabel: String? {
        if let winner = state.winner {
            return winner == .us ? "Vittoria" : "Sconfitta"
        }
        switch state.mode {
        case .tiebreak: return "Tie-break"
        case .superTiebreak: return "Super tie-break"
        case .regular:
            guard state.pointsUs >= 3, state.pointsThem >= 3 else { return nil }
            if rules.deuceRule == .goldenPoint { return "Punto d'oro" }
            return state.pointsUs == state.pointsThem ? "Parità" : "Vantaggio \(state.pointsUs > state.pointsThem ? "Noi" : "Loro")"
        }
    }

    // MARK: - Regole

    @discardableResult
    static func apply(_ event: MatchEvent, to state: inout MatchState, rules: MatchRules) -> PointOutcome {
        switch event {
        case .setServer(let team):
            state.server = team
            // Se il tie-break non e' ancora iniziato, la correzione cambia
            // anche il primo battitore (serve per il set successivo).
            if state.mode != .regular, state.pointsUs + state.pointsThem == 0 {
                state.tiebreakFirstServer = team
            }
            return .point
        case .point(let team):
            guard state.winner == nil else { return .ignored }
            if team == .us { state.pointsUs += 1 } else { state.pointsThem += 1 }
            switch state.mode {
            case .regular:
                return applyRegularPoint(to: &state, rules: rules)
            case .tiebreak, .superTiebreak:
                return applyTiebreakPoint(to: &state, rules: rules)
            }
        }
    }

    private static func applyRegularPoint(to state: inout MatchState, rules: MatchRules) -> PointOutcome {
        let us = state.pointsUs, them = state.pointsThem
        let leader: Team = us > them ? .us : .them
        let high = max(us, them), low = min(us, them)
        let golden = rules.deuceRule == .goldenPoint
        guard high >= 4, high - low >= 2 || golden else { return .point }

        // Game vinto.
        if leader == .us { state.gamesUs += 1 } else { state.gamesThem += 1 }
        state.pointsUs = 0
        state.pointsThem = 0
        state.server = state.server.opponent

        let gu = state.gamesUs, gt = state.gamesThem
        let target = MatchRules.gamesPerSet
        if max(gu, gt) >= target, abs(gu - gt) >= 2 {
            return closeSet(SetScore(us: gu, them: gt), state: &state, rules: rules)
        }
        if gu == target, gt == target {
            state.mode = .tiebreak
            state.tiebreakFirstServer = state.server
        }
        return .game
    }

    private static func applyTiebreakPoint(to state: inout MatchState, rules: MatchRules) -> PointOutcome {
        let us = state.pointsUs, them = state.pointsThem
        let target = state.mode == .superTiebreak ? MatchRules.superTiebreakTarget : MatchRules.tiebreakTarget

        if max(us, them) >= target, abs(us - them) >= 2 {
            let first = state.tiebreakFirstServer ?? state.server
            let set: SetScore
            if state.mode == .superTiebreak {
                set = SetScore(us: us > them ? 1 : 0, them: us > them ? 0 : 1,
                               tiebreakUs: us, tiebreakThem: them, isSuperTiebreak: true)
            } else {
                set = SetScore(us: state.gamesUs + (us > them ? 1 : 0),
                               them: state.gamesThem + (us > them ? 0 : 1),
                               tiebreakUs: us, tiebreakThem: them)
            }
            // Il primo game dopo il tie-break lo serve chi ha risposto
            // per primo nel tie-break.
            state.server = first.opponent
            return closeSet(set, state: &state, rules: rules)
        }

        // Primo punto al primo battitore, poi si cambia ogni 2 punti:
        // il servizio passa dopo il 1°, 3°, 5°... punto giocato.
        if (us + them) % 2 == 1 {
            state.server = state.server.opponent
        }
        return .point
    }

    private static func closeSet(_ set: SetScore, state: inout MatchState, rules: MatchRules) -> PointOutcome {
        state.completedSets.append(set)
        state.gamesUs = 0
        state.gamesThem = 0
        state.pointsUs = 0
        state.pointsThem = 0
        state.mode = .regular
        state.tiebreakFirstServer = nil

        if state.setsWon == MatchRules.setsToWin {
            state.winner = .us
            return .match
        }
        if state.setsLost == MatchRules.setsToWin {
            state.winner = .them
            return .match
        }
        if rules.format == .twoSetsSuperTiebreak, state.completedSets.count == 2 {
            state.mode = .superTiebreak
            state.tiebreakFirstServer = state.server
        }
        return .set
    }
}
