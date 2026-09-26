import SwiftUI
import SwiftData
import PadelKit

struct MatchDetailView: View {
    let match: Match
    @Environment(\.modelContext) private var context
    @Query(sort: \Player.name) private var players: [Player]
    @State private var isEditing = false

    private var names: [UUID: String] { MatchStore.names(of: players) }

    var body: some View {
        List {
            Section {
                HStack(spacing: 16) {
                    ResultBadge(result: match.result, size: 56)
                    VStack(alignment: .leading, spacing: 4) {
                        Text(resultTitle).font(.title2.bold())
                        Text(match.sets.display.isEmpty ? "Nessun set" : match.sets.display)
                            .font(.title3.monospacedDigit())
                    }
                }
                .padding(.vertical, 4)
                if match.needsDetails {
                    Button {
                        isEditing = true
                    } label: {
                        Label("Arrivata dal Watch: aggiungi compagno e avversari", systemImage: "square.and.pencil")
                            .foregroundStyle(Theme.them)
                    }
                }
            }

            Section("Partita") {
                LabeledContent("Data", value: match.date.formatted(date: .long, time: .shortened))
                LabeledContent("Circolo", value: match.club.isEmpty ? "—" : match.club)
                LabeledContent("Campo", value: match.court.isEmpty ? "—" : match.court)
                LabeledContent("Coperto", value: match.indoor ? "Sì" : "No")
            }

            Section("Giocatori") {
                LabeledContent("Compagno", value: name(match.partnerID))
                LabeledContent("Avversario 1", value: name(match.opponent1ID))
                LabeledContent("Avversario 2", value: name(match.opponent2ID))
            }

            Section("Regole") {
                LabeledContent("Sul 40-40", value: match.rules.deuceRule.label)
                LabeledContent("Formato", value: match.rules.format.label)
                LabeledContent("Primo servizio", value: match.rules.firstServer.label)
            }

            Section("Dati") {
                LabeledContent("Durata", value: match.duration > 0 ? PadelFormat.longDuration(match.duration) : "—")
                if let kcal = match.activeCalories {
                    LabeledContent("Calorie attive", value: "\(Int(kcal.rounded())) kcal")
                }
                if let avg = match.averageHeartRate {
                    LabeledContent("FC media", value: "\(Int(avg.rounded())) bpm")
                }
                if let max = match.maxHeartRate {
                    LabeledContent("FC massima", value: "\(Int(max.rounded())) bpm")
                }
                LabeledContent("Origine", value: match.source == .watch ? "Apple Watch" : "Inserita a mano")
            }

            if !match.notes.isEmpty {
                Section("Note") { Text(match.notes) }
            }
        }
        .navigationTitle(match.date.formatted(date: .abbreviated, time: .omitted))
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            Button("Modifica") { isEditing = true }
        }
        .sheet(isPresented: $isEditing) {
            MatchEditorView(title: "Modifica partita", draft: match.record) { record in
                match.update(from: record)
                try? context.save()
            }
        }
    }

    private var resultTitle: String {
        switch match.result {
        case .us: "Vittoria"
        case .them: "Sconfitta"
        case nil: "Senza risultato"
        }
    }

    private func name(_ id: UUID?) -> String {
        guard let id else { return "—" }
        return names[id] ?? "Giocatore eliminato"
    }
}
