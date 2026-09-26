import SwiftUI
import PadelKit

/// Colori sportivi ad alto contrasto, leggibili al sole.
enum Theme {
    /// Verde campo per "Noi".
    static let us = Color(red: 0.16, green: 0.84, blue: 0.42)
    /// Arancio acceso per "Loro".
    static let them = Color(red: 1.0, green: 0.55, blue: 0.10)
    /// Giallo pallina, per servizio e stati speciali.
    static let ball = Color(red: 0.93, green: 1.0, blue: 0.20)
    static let win = Color(red: 0.16, green: 0.78, blue: 0.40)
    static let loss = Color(red: 0.93, green: 0.26, blue: 0.24)

    static func color(for team: Team) -> Color { team == .us ? us : them }
}

enum PadelFormat {
    /// "1:32:05" oppure "32:05".
    static func duration(_ seconds: TimeInterval) -> String {
        let total = max(0, Int(seconds))
        let h = total / 3600, m = (total % 3600) / 60, s = total % 60
        return h > 0 ? String(format: "%d:%02d:%02d", h, m, s) : String(format: "%02d:%02d", m, s)
    }

    /// "1 h 32 min".
    static func longDuration(_ seconds: TimeInterval) -> String {
        let minutes = max(0, Int(seconds.rounded()) / 60)
        let h = minutes / 60, m = minutes % 60
        if h == 0 { return "\(m) min" }
        return m == 0 ? "\(h) h" : "\(h) h \(m) min"
    }
}
