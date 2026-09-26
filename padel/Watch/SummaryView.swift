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
                    if summary.sets.isEmpty {
                        Text("Nessun set concluso").foregroundStyle(.secondary)
                    } else {
                        SetsTable(sets: summary.sets, winner: summary.winner)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                    }
                    if let partial = summary.unfinishedSet {
                        Text("Set interrotto sul \(partial.us)-\(partial.them)")
                            .font(.footnote).foregroundStyle(.secondary)
                    }
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
}
