import SwiftUI
import SwiftData
import UniformTypeIdentifiers
import PadelKit

struct SettingsView: View {
    @Environment(\.modelContext) private var context
    @Environment(PhoneConnectivity.self) private var connectivity
    @Query(sort: \Match.date) private var matches: [Match]
    @Query(sort: \Player.name) private var players: [Player]
    @State private var isImporting = false
    @State private var message: String?

    var body: some View {
        NavigationStack {
            Form {
                Section("Rubrica") {
                    NavigationLink {
                        PlayersView()
                    } label: {
                        LabeledContent("Giocatori", value: "\(players.count)")
                    }
                }

                Section {
                    if let backup {
                        ShareLink(item: backup, preview: SharePreview("Backup Padel", image: Image(systemName: "doc.text"))) {
                            Label("Esporta backup", systemImage: "square.and.arrow.up")
                        }
                    }
                    Button {
                        isImporting = true
                    } label: {
                        Label("Importa backup", systemImage: "square.and.arrow.down")
                    }
                } header: {
                    Text("Backup")
                } footer: {
                    Text("Il backup è un file JSON con \(matches.count) partite e \(players.count) giocatori. Salvalo in File o mandalo a te stesso. L'importazione aggiunge solo ciò che manca: niente doppioni.")
                }

                Section("Apple Watch") {
                    LabeledContent("App sul Watch", value: connectivity.isWatchAppInstalled ? "Installata" : "Non rilevata")
                    if let last = connectivity.lastReceived {
                        LabeledContent("Ultima partita ricevuta", value: last.formatted(date: .abbreviated, time: .shortened))
                    }
                }

                Section("Informazioni") {
                    LabeledContent("Versione", value: Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "—")
                }
            }
            .navigationTitle("Impostazioni")
            .fileImporter(isPresented: $isImporting, allowedContentTypes: [.json]) { result in
                importBackup(result)
            }
            .alert("Backup", isPresented: Binding(get: { message != nil }, set: { if !$0 { message = nil } })) {
                Button("OK") { message = nil }
            } message: {
                Text(message ?? "")
            }
        }
    }

    private var backup: BackupDocument? {
        guard let data = try? MatchStore.backupData(players: players, matches: matches) else { return nil }
        let day = Date().formatted(.iso8601.year().month().day())
        return BackupDocument(data: data, fileName: "padel-backup-\(day).json")
    }

    private func importBackup(_ result: Result<URL, Error>) {
        do {
            let url = try result.get()
            let scoped = url.startAccessingSecurityScopedResource()
            defer { if scoped { url.stopAccessingSecurityScopedResource() } }
            let data = try Data(contentsOf: url)
            let added = try MatchStore.importBackup(data, into: context)
            message = added.matches == 0 && added.players == 0
                ? "Nessun dato nuovo: era tutto già presente."
                : "Importate \(added.matches) partite e \(added.players) giocatori."
        } catch {
            message = "Importazione non riuscita: \(error.localizedDescription)"
        }
    }
}

/// File JSON condivisibile con ShareLink.
struct BackupDocument: Transferable, Sendable {
    let data: Data
    let fileName: String

    static var transferRepresentation: some TransferRepresentation {
        FileRepresentation(exportedContentType: .json) { document in
            let url = FileManager.default.temporaryDirectory.appendingPathComponent(document.fileName)
            try document.data.write(to: url, options: .atomic)
            return SentTransferredFile(url)
        }
    }
}
