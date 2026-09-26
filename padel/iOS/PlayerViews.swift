import SwiftUI
import SwiftData

/// Riga del form che apre la rubrica per scegliere un giocatore.
struct PlayerField: View {
    let title: String
    @Binding var selection: UUID?
    let suggestions: [UUID]
    let excluded: Set<UUID>

    @Query(sort: \Player.name) private var players: [Player]

    var body: some View {
        NavigationLink {
            PlayerPickerView(title: title, selection: $selection, suggestions: suggestions, excluded: excluded)
        } label: {
            LabeledContent(title) {
                Text(selectedName ?? "Scegli")
                    .foregroundStyle(selectedName == nil ? .secondary : .primary)
            }
        }
    }

    private var selectedName: String? {
        guard let selection else { return nil }
        return players.first { $0.id == selection }?.name ?? "Giocatore eliminato"
    }
}

/// Rubrica con ricerca, suggerimenti e creazione al volo.
struct PlayerPickerView: View {
    let title: String
    @Binding var selection: UUID?
    let suggestions: [UUID]
    let excluded: Set<UUID>

    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss
    @Query(sort: \Player.name) private var players: [Player]
    @State private var search = ""

    private var trimmed: String { search.trimmingCharacters(in: .whitespacesAndNewlines) }

    private var available: [Player] { players.filter { !excluded.contains($0.id) } }

    private var filtered: [Player] {
        trimmed.isEmpty ? available : available.filter { $0.name.localizedStandardContains(trimmed) }
    }

    private var suggested: [Player] {
        guard trimmed.isEmpty else { return [] }
        return suggestions.compactMap { id in available.first { $0.id == id } }
    }

    private var canCreate: Bool {
        !trimmed.isEmpty && !players.contains { $0.name.compare(trimmed, options: [.caseInsensitive, .diacriticInsensitive]) == .orderedSame }
    }

    var body: some View {
        List {
            if canCreate {
                Section {
                    Button {
                        let player = Player(name: trimmed)
                        context.insert(player)
                        try? context.save()
                        choose(player.id)
                    } label: {
                        Label("Aggiungi «\(trimmed)»", systemImage: "person.badge.plus")
                    }
                }
            }
            if !suggested.isEmpty {
                Section("Suggeriti") {
                    ForEach(suggested) { row($0) }
                }
            }
            Section(trimmed.isEmpty ? "Tutti i giocatori" : "Risultati") {
                if selection != nil, trimmed.isEmpty {
                    Button("Nessuno", role: .destructive) { choose(nil) }
                }
                ForEach(filtered) { row($0) }
            }
        }
        .searchable(text: $search, placement: .navigationBarDrawer(displayMode: .always), prompt: "Cerca o aggiungi un nome")
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
        .overlay {
            if players.isEmpty, trimmed.isEmpty {
                ContentUnavailableView("Rubrica vuota", systemImage: "person.2",
                                       description: Text("Scrivi un nome nella ricerca per aggiungerlo."))
            }
        }
    }

    private func row(_ player: Player) -> some View {
        Button {
            choose(player.id)
        } label: {
            HStack {
                Text(player.name).foregroundStyle(.primary)
                Spacer()
                if player.id == selection {
                    Image(systemName: "checkmark").foregroundStyle(Theme.win)
                }
            }
        }
    }

    private func choose(_ id: UUID?) {
        selection = id
        dismiss()
    }
}

/// Gestione della rubrica dalle Impostazioni.
struct PlayersView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \Player.name) private var players: [Player]
    @State private var newName = ""
    @State private var isAdding = false
    @State private var renaming: Player?
    @State private var renameText = ""
    @State private var deleting: Player?

    var body: some View {
        List {
            ForEach(players) { player in
                Button {
                    renameText = player.name
                    renaming = player
                } label: {
                    Text(player.name).foregroundStyle(.primary)
                }
                .swipeActions {
                    Button("Elimina", role: .destructive) { deleting = player }
                }
            }
        }
        .overlay {
            if players.isEmpty {
                ContentUnavailableView("Nessun giocatore", systemImage: "person.2",
                                       description: Text("Aggiungi compagni e avversari abituali con +."))
            }
        }
        .navigationTitle("Giocatori")
        .toolbar {
            Button {
                newName = ""
                isAdding = true
            } label: {
                Label("Aggiungi", systemImage: "plus")
            }
        }
        .alert("Nuovo giocatore", isPresented: $isAdding) {
            TextField("Nome", text: $newName)
            Button("Annulla", role: .cancel) {}
            Button("Aggiungi") {
                let name = newName.trimmingCharacters(in: .whitespacesAndNewlines)
                guard !name.isEmpty else { return }
                context.insert(Player(name: name))
                try? context.save()
            }
        }
        .alert("Rinomina", isPresented: Binding(get: { renaming != nil }, set: { if !$0 { renaming = nil } })) {
            TextField("Nome", text: $renameText)
            Button("Annulla", role: .cancel) { renaming = nil }
            Button("Salva") {
                let name = renameText.trimmingCharacters(in: .whitespacesAndNewlines)
                if let renaming, !name.isEmpty {
                    renaming.name = name
                    try? context.save()
                }
                renaming = nil
            }
        }
        .confirmationDialog("Eliminare \(deleting?.name ?? "")?",
                            isPresented: Binding(get: { deleting != nil }, set: { if !$0 { deleting = nil } }),
                            titleVisibility: .visible) {
            Button("Elimina", role: .destructive) {
                if let deleting { MatchStore.delete(deleting, in: context) }
                deleting = nil
            }
        } message: {
            Text("Verrà tolto dalle partite in cui compare. Le partite restano.")
        }
    }
}
