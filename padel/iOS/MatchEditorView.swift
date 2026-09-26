import SwiftUI
import SwiftData
import PadelKit

/// Editor usato sia per l'inserimento manuale sia per la modifica.
/// Lavora su una copia (`MatchRecord`): "Annulla" non tocca il database.
struct MatchEditorView: View {
    let title: String
    @State var draft: MatchRecord
    let onSave: (MatchRecord) -> Void

    @Environment(\.dismiss) private var dismiss
    @Query(sort: \Match.date, order: .reverse) private var matches: [Match]

    var body: some View {
        NavigationStack {
            Form {
                Section("Partita") {
                    DatePicker("Data", selection: $draft.date)
                    TextField("Circolo", text: $draft.club)
                    TextField("Campo", text: $draft.court)
                    Toggle("Campo coperto", isOn: $draft.rules.indoor)
                }

                Section("Giocatori") {
                    PlayerField(title: "Compagno", selection: $draft.partnerID,
                                suggestions: suggestions(\.partnerID), excluded: excluded(except: draft.partnerID))
                    PlayerField(title: "Avversario 1", selection: $draft.opponent1ID,
                                suggestions: opponentSuggestions, excluded: excluded(except: draft.opponent1ID))
                    PlayerField(title: "Avversario 2", selection: $draft.opponent2ID,
                                suggestions: opponentSuggestions, excluded: excluded(except: draft.opponent2ID))
                }

                Section("Regole") {
                    Picker("Sul 40-40", selection: $draft.rules.deuceRule) {
                        ForEach(DeuceRule.allCases, id: \.self) { Text($0.label).tag($0) }
                    }
                    Picker("Formato", selection: $draft.rules.format) {
                        ForEach(MatchFormat.allCases, id: \.self) { Text($0.label).tag($0) }
                    }
                    Picker("Primo servizio", selection: $draft.rules.firstServer) {
                        ForEach(Team.allCases, id: \.self) { Text($0.label).tag($0) }
                    }
                }

                Section {
                    ForEach(Array(draft.sets.indices), id: \.self) { index in
                        SetEditorRow(number: index + 1, set: setBinding(index))
                    }
                    .onDelete { draft.sets.remove(atOffsets: $0) }
                    if draft.sets.count < 3 {
                        Button {
                            draft.sets.append(SetScore(us: 0, them: 0))
                        } label: {
                            Label("Aggiungi set", systemImage: "plus.circle")
                        }
                        if draft.rules.format == .twoSetsSuperTiebreak, draft.sets.count == 2 {
                            Button {
                                draft.sets.append(SetScore(us: 0, them: 0, tiebreakUs: 0, tiebreakThem: 0, isSuperTiebreak: true))
                            } label: {
                                Label("Aggiungi super tie-break", systemImage: "plus.circle.fill")
                            }
                        }
                    }
                } header: {
                    Text("Set")
                } footer: {
                    Text(resultText)
                }

                Section("Durata") {
                    Stepper(value: minutesBinding, in: 0...360, step: 5) {
                        LabeledContent("Durata", value: PadelFormat.longDuration(draft.duration))
                    }
                }

                Section("Note") {
                    TextField("Note sulla partita", text: $draft.notes, axis: .vertical)
                        .lineLimit(3...8)
                }
            }
            .navigationTitle(title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Annulla") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Salva") {
                        onSave(draft)
                        dismiss()
                    }
                    .bold()
                }
            }
        }
    }

    // MARK: - Aiuti

    private var resultText: String {
        let sets = draft.sets
        switch sets.winnerBySets {
        case .us: return "Risultato: vittoria \(sets.setsWon)-\(sets.setsLost)"
        case .them: return "Risultato: sconfitta \(sets.setsWon)-\(sets.setsLost)"
        case nil: return "Risultato: nessun vincitore (set pari)"
        }
    }

    /// Binding protetto: evita crash se la riga sparisce durante un'animazione.
    private func setBinding(_ index: Int) -> Binding<SetScore> {
        Binding(
            get: { draft.sets.indices.contains(index) ? draft.sets[index] : SetScore(us: 0, them: 0) },
            set: { if draft.sets.indices.contains(index) { draft.sets[index] = $0 } }
        )
    }

    private var minutesBinding: Binding<Int> {
        Binding(get: { Int(draft.duration / 60) }, set: { draft.duration = TimeInterval($0 * 60) })
    }

    private func excluded(except current: UUID?) -> Set<UUID> {
        Set([draft.partnerID, draft.opponent1ID, draft.opponent2ID].compactMap { $0 }).subtracting([current].compactMap { $0 })
    }

    /// Giocatori piu' frequenti nel ruolo indicato, dal piu' ricorrente.
    private func suggestions(_ keyPath: KeyPath<Match, UUID?>) -> [UUID] {
        ranked(matches.compactMap { $0[keyPath: keyPath] })
    }

    private var opponentSuggestions: [UUID] {
        ranked(matches.flatMap { [$0.opponent1ID, $0.opponent2ID].compactMap { $0 } })
    }

    private func ranked(_ ids: [UUID]) -> [UUID] {
        var counts: [UUID: Int] = [:]
        for id in ids { counts[id, default: 0] += 1 }
        return counts.sorted { $0.value > $1.value }.prefix(5).map(\.key)
    }
}

struct SetEditorRow: View {
    let number: Int
    @Binding var set: SetScore

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(set.isSuperTiebreak ? "Super tie-break" : "Set \(number)")
                .font(.subheadline.weight(.semibold))
            if set.isSuperTiebreak {
                scoreStepper("Noi", value: tiebreakBinding(\.tiebreakUs), range: 0...40, color: Theme.us)
                scoreStepper("Loro", value: tiebreakBinding(\.tiebreakThem), range: 0...40, color: Theme.them)
            } else {
                scoreStepper("Noi", value: $set.us, range: 0...7, color: Theme.us)
                scoreStepper("Loro", value: $set.them, range: 0...7, color: Theme.them)
                if isTiebreakSet {
                    Text("Punti del tie-break").font(.caption).foregroundStyle(.secondary)
                    scoreStepper("Noi", value: tiebreakBinding(\.tiebreakUs), range: 0...40, color: Theme.us)
                    scoreStepper("Loro", value: tiebreakBinding(\.tiebreakThem), range: 0...40, color: Theme.them)
                }
            }
        }
        .padding(.vertical, 4)
        .onChange(of: isTiebreakSet) { _, isTiebreak in
            // Tie-break solo sul 7-6: altrimenti i punti non hanno senso.
            if !isTiebreak, !set.isSuperTiebreak {
                set.tiebreakUs = nil
                set.tiebreakThem = nil
            }
        }
    }

    private var isTiebreakSet: Bool {
        (set.us == 7 && set.them == 6) || (set.us == 6 && set.them == 7)
    }

    private func scoreStepper(_ label: String, value: Binding<Int>, range: ClosedRange<Int>, color: Color) -> some View {
        Stepper(value: value, in: range) {
            HStack {
                Circle().fill(color).frame(width: 10, height: 10)
                Text(label)
                Spacer()
                Text("\(value.wrappedValue)").font(.title3.monospacedDigit().bold())
            }
        }
    }

    private func tiebreakBinding(_ keyPath: WritableKeyPath<SetScore, Int?>) -> Binding<Int> {
        Binding(
            get: { set[keyPath: keyPath] ?? 0 },
            set: { newValue in
                set[keyPath: keyPath] = newValue
                if set.isSuperTiebreak {
                    // Nel super tie-break i "game" indicano solo chi l'ha vinto.
                    let us = set.tiebreakUs ?? 0, them = set.tiebreakThem ?? 0
                    set.us = us > them ? 1 : 0
                    set.them = them > us ? 1 : 0
                }
            }
        )
    }
}
