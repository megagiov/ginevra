import SwiftUI
import PadelKit

struct SummaryView: View {
    @Environment(MatchSession.self) private var session
    let summary: WatchMatchSummary

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 4) {
                    Text(title)
                        .font(.system(size: 26, weight: .heavy, design: .rounded))
                        .foregroundStyle(color)
                    Text(setsText)
                        .font(.system(size: 18, weight: .bold, design: .rounded).monospacedDigit())
                }
            }
            Section {
                LabeledContent("Durata", value: PadelFormat.duration(summary.duration))
                if let kcal = summary.activeCalories {
                    LabeledContent("Calorie", value: "\(Int(kcal.rounded())) kcal")
                }
                if let avg = summary.averageHeartRate {
                    LabeledContent("FC media", value: "\(Int(avg.rounded()))")
                }
                if let max = summary.maxHeartRate {
                    LabeledContent("FC max", value: "\(Int(max.rounded()))")
                }
            }
            Section {
                Label("Inviata all'iPhone. Arriva anche se ora non è raggiungibile.", systemImage: "iphone")
                    .font(.footnote)
            }
            Button {
                session.newMatch()
            } label: {
                Label("Nuova partita", systemImage: "plus")
            }
        }
        .navigationTitle("Riepilogo")
    }

    private var title: String {
        switch summary.winner {
        case .us: "Vittoria"
        case .them: "Sconfitta"
        case nil: "Interrotta"
        }
    }

    private var color: Color {
        switch summary.winner {
        case .us: Theme.us
        case .them: Theme.them
        case nil: .secondary
        }
    }

    private var setsText: String {
        var parts = summary.sets.map(\.compactDisplay)
        if let partial = summary.unfinishedSet { parts.append("(\(partial.us)-\(partial.them))") }
        return parts.isEmpty ? "Nessun set concluso" : parts.joined(separator: " ")
    }
}
