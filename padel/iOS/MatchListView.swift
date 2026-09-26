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

/// Scheda partita: intestazione con data e durata, poi una riga per
/// squadra con i game di ogni set (quelli vincenti in verde).
struct MatchRow: View {
    let match: Match
    let names: [UUID: String]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Text(match.source == .watch ? "WATCH" : "PARTITA")
                    .font(.caption2.weight(.heavy))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Theme.navy, in: RoundedRectangle(cornerRadius: 4))
                if match.needsDetails {
                    Text("DA COMPLETARE")
                        .font(.caption2.weight(.heavy))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Theme.them, in: RoundedRectangle(cornerRadius: 4))
                }
                Spacer()
                Label(match.date.formatted(.dateTime.day(.twoDigits).month(.twoDigits).year()), systemImage: "calendar")
                if match.duration > 0 {
                    Label("\(Int(match.duration / 60))′", systemImage: "timer")
                }
            }
            .font(.caption)
            .foregroundStyle(.secondary)
            .labelStyle(CompactLabelStyle())

            teamRow(.us, title: usTitle)
            Divider()
            teamRow(.them, title: themTitle)

            if !match.club.isEmpty {
                Text(match.club + (match.court.isEmpty ? "" : " · " + match.court))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 6)
    }

    private var usTitle: String {
        guard let partner = match.partnerID.flatMap({ names[$0] }) else { return "Noi" }
        return "Noi · \(partner)"
    }

    private var themTitle: String {
        let opponents = [match.opponent1ID, match.opponent2ID].compactMap { $0 }.compactMap { names[$0] }
        return opponents.isEmpty ? "Avversari" : opponents.joined(separator: " e ")
    }

    private func teamRow(_ team: Team, title: String) -> some View {
        HStack(spacing: 0) {
            Image(systemName: "trophy.circle.fill")
                .font(.title3)
                .foregroundStyle(Theme.navy, Theme.ball)
                .opacity(match.result == team ? 1 : 0)
                .frame(width: 30, alignment: .leading)
            Text(title)
                .font(.body.weight(match.result == team ? .semibold : .regular))
                .lineLimit(1)
            Spacer(minLength: 8)
            ForEach(Array(match.sets.enumerated()), id: \.offset) { _, set in
                Text("\(value(of: set, for: team))")
                    .font(.title2.weight(.medium).monospacedDigit())
                    .foregroundStyle(set.winner == team ? Theme.win : .primary)
                    .frame(width: 30)
            }
        }
        .accessibilityElement(children: .combine)
    }

    private func value(of set: SetScore, for team: Team) -> Int {
        if set.isSuperTiebreak {
            return (team == .us ? set.tiebreakUs : set.tiebreakThem) ?? 0
        }
        return team == .us ? set.us : set.them
    }
}

/// Icona e testo vicini, in piccolo.
struct CompactLabelStyle: LabelStyle {
    func makeBody(configuration: Configuration) -> some View {
        HStack(spacing: 3) {
            configuration.icon
            configuration.title
        }
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
