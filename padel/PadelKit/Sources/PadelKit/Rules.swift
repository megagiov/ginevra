import Foundation

/// Una delle due coppie in campo, vista dal proprietario dell'app.
public enum Team: String, Codable, CaseIterable, Sendable, Hashable {
    case us
    case them

    public var opponent: Team { self == .us ? .them : .us }

    public var label: String { self == .us ? "Noi" : "Loro" }
}

/// Cosa succede sul 40-40.
public enum DeuceRule: String, Codable, CaseIterable, Sendable, Hashable {
    case goldenPoint
    case advantages

    public var label: String {
        switch self {
        case .goldenPoint: "Punto d'oro"
        case .advantages: "Vantaggi"
        }
    }
}

public enum MatchFormat: String, Codable, CaseIterable, Sendable, Hashable {
    /// Al meglio dei 3 set, tutti a 6 game con tie-break sul 6-6.
    case bestOfThree
    /// Due set a 6 game; sull'1-1 si gioca un super tie-break a 10.
    case twoSetsSuperTiebreak

    public var label: String {
        switch self {
        case .bestOfThree: "Al meglio dei 3 set"
        case .twoSetsSuperTiebreak: "2 set + super tie-break"
        }
    }

    public var shortLabel: String {
        switch self {
        case .bestOfThree: "3 set"
        case .twoSetsSuperTiebreak: "2 set + STB"
        }
    }
}

public struct MatchRules: Codable, Hashable, Sendable {
    public var deuceRule: DeuceRule
    public var format: MatchFormat
    public var firstServer: Team
    public var indoor: Bool

    public init(
        deuceRule: DeuceRule = .goldenPoint,
        format: MatchFormat = .bestOfThree,
        firstServer: Team = .us,
        indoor: Bool = false
    ) {
        self.deuceRule = deuceRule
        self.format = format
        self.firstServer = firstServer
        self.indoor = indoor
    }

    public static let gamesPerSet = 6
    public static let tiebreakTarget = 7
    public static let superTiebreakTarget = 10
    public static let setsToWin = 2
}

/// Un set concluso. Per il super tie-break i game valgono 1-0 e i punti
/// stanno in `tiebreakUs` / `tiebreakThem`.
public struct SetScore: Codable, Hashable, Sendable {
    public var us: Int
    public var them: Int
    public var tiebreakUs: Int?
    public var tiebreakThem: Int?
    public var isSuperTiebreak: Bool

    public init(us: Int, them: Int, tiebreakUs: Int? = nil, tiebreakThem: Int? = nil, isSuperTiebreak: Bool = false) {
        self.us = us
        self.them = them
        self.tiebreakUs = tiebreakUs
        self.tiebreakThem = tiebreakThem
        self.isSuperTiebreak = isSuperTiebreak
    }

    public var winner: Team? {
        if us > them { return .us }
        if them > us { return .them }
        return nil
    }

    /// "6-4", "7-6 (7-5)", "[10-8]".
    public var display: String {
        if isSuperTiebreak, let a = tiebreakUs, let b = tiebreakThem {
            return "[\(a)-\(b)]"
        }
        if let a = tiebreakUs, let b = tiebreakThem {
            return "\(us)-\(them) (\(a)-\(b))"
        }
        return "\(us)-\(them)"
    }

    /// Versione compatta per il Watch: "7-6", "[10-8]".
    public var compactDisplay: String {
        if isSuperTiebreak, let a = tiebreakUs, let b = tiebreakThem {
            return "[\(a)-\(b)]"
        }
        return "\(us)-\(them)"
    }
}

extension Array where Element == SetScore {
    public var setsWon: Int { filter { $0.winner == .us }.count }
    public var setsLost: Int { filter { $0.winner == .them }.count }

    /// Vincitore per numero di set; nil in caso di parità.
    public var winnerBySets: Team? {
        if setsWon > setsLost { return .us }
        if setsLost > setsWon { return .them }
        return nil
    }

    public var display: String { map(\.display).joined(separator: "  ") }
    public var compactDisplay: String { map(\.compactDisplay).joined(separator: " ") }
}
