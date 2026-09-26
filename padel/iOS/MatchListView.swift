import SwiftUI
import SwiftData
import PadelKit

struct MatchListView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \Match.date, order: .reverse) private var matches: [Match]
    @Query(sort: \Player.name) private var players: [Player]
    @State private var isAddingMatch = false

    private var names: [UUID: String] { MatchStore.names(of: players) }
    private var incompleteCount: Int { matches.filter(\.needsDetails).count }

    var body: some View {
        NavigationStack {
            List {
                if incompleteCount > 0 {
                    Section {
                        Label(incompleteCount == 1
                              ? "1 partita dal Watch da completare"
                              : "\(incompleteCount) partite dal Watch da completare",
                              systemImage: "applewatch.radiowaves.left.and.right")
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(Theme.them)
                    } footer: {
                        Text("Aggiungi compagno e avversari per avere statistiche complete.")
                    }
                }
                ForEach(matches) { match in
                    NavigationLink {
                        MatchDetailView(match: match)
                    } label: {
                        MatchRow(match: match, names: names)
                    }
                    .listRowBackground(match.needsDetails ? Theme.them.opacity(0.12) : nil)
                }
                .onDelete(perform: delete)
            }
            .overlay {
                if matches.isEmpty {
                    ContentUnavailableView {
                        Label("Nessuna partita", systemImage: "figure.tennis")
                    } description: {
                        Text("Gioca una partita con l'Apple Watch oppure inseriscila a mano con +.")
                    }
                }
            }
            .navigationTitle("Partite")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        isAddingMatch = true
                    } label: {
                        Label("Nuova partita", systemImage: "plus")
                    }
                }
            }
            .sheet(isPresented: $isAddingMatch) {
                MatchEditorView(title: "Nuova partita",
                                draft: MatchRecord(date: Date(), sets: [SetScore(us: 0, them: 0)], duration: 90 * 60)) { record in
                    context.insert(Match(record: record))
                    try? context.save()
                }
            }
        }
    }

    private func delete(at offsets: IndexSet) {
        for index in offsets { context.delete(matches[index]) }
        try? context.save()
    }
}

struct MatchRow: View {
    let match: Match
    let names: [UUID: String]

    var body: some View {
        HStack(spacing: 14) {
            ResultBadge(result: match.result)
            VStack(alignment: .leading, spacing: 3) {
                Text(match.sets.display.isEmpty ? "Nessun set" : match.sets.display)
                    .font(.headline.monospacedDigit())
                Text(opponentsText)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                HStack(spacing: 6) {
                    Text(match.date, format: .dateTime.day().month(.abbreviated).year())
                    if !match.club.isEmpty { Text("· \(match.club)").lineLimit(1) }
                }
                .font(.caption)
                .foregroundStyle(.secondary)
                if match.needsDetails {
                    Label("Da completare", systemImage: "exclamationmark.circle.fill")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(Theme.them)
                }
            }
        }
        .padding(.vertical, 2)
    }

    private var opponentsText: String {
        let opponents = [match.opponent1ID, match.opponent2ID].compactMap { $0 }.compactMap { names[$0] }
        return opponents.isEmpty ? "Avversari non indicati" : "contro " + opponents.joined(separator: " e ")
    }
}

struct ResultBadge: View {
    let result: Team?
    var size: CGFloat = 38

    var body: some View {
        Text(label)
            .font(.system(size: size * 0.5, weight: .heavy, design: .rounded))
            .foregroundStyle(.white)
            .frame(width: size, height: size)
            .background(color, in: RoundedRectangle(cornerRadius: size * 0.28))
            .accessibilityLabel(accessibility)
    }

    private var label: String {
        switch result {
        case .us: "V"
        case .them: "S"
        case nil: "–"
        }
    }

    private var color: Color {
        switch result {
        case .us: Theme.win
        case .them: Theme.loss
        case nil: .gray
        }
    }

    private var accessibility: String {
        switch result {
        case .us: "Vittoria"
        case .them: "Sconfitta"
        case nil: "Senza risultato"
        }
    }
}
