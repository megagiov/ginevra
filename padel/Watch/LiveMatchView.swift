import SwiftUI
import PadelKit

/// Tre pagine orizzontali: controlli ← segnapunti → dati.
struct LiveMatchView: View {
    @Environment(MatchSession.self) private var session
    @State private var page = 1

    var body: some View {
        TabView(selection: $page) {
            ControlsView(page: $page).tag(0)
            ScoreboardView().tag(1)
            MetricsView().tag(2)
        }
        .tabViewStyle(.page)
    }
}

// MARK: - Segnapunti

/// Layout ispirato alle app segnapunti da polso: azioni in alto, tabellina
/// set/game al centro, due grandi riquadri dei punti da toccare in basso.
struct ScoreboardView: View {
    @Environment(MatchSession.self) private var session

    var body: some View {
        let engine = session.engine
        if engine.state.isFinished {
            MatchWonView()
        } else {
            VStack(spacing: 5) {
                actions(engine)
                scoreTable(engine.state)
                statusLine(engine)
                HStack(spacing: 6) {
                    pointTile(.us, engine: engine)
                    pointTile(.them, engine: engine)
                }
            }
            .padding(.horizontal, 2)
            .ignoresSafeArea(edges: .bottom)
        }
    }

    // Indietro (rosso) e cambio servizio (blu), sempre a portata di dito.
    private func actions(_ engine: MatchEngine) -> some View {
        HStack(spacing: 6) {
            WatchActionButton(systemImage: "arrow.uturn.backward", title: "Indietro", color: Theme.danger,
                              enabled: engine.canUndo) {
                session.undo()
            }
            .accessibilityLabel("Indietro: annulla l'ultimo punto")
            WatchActionButton(systemImage: "arrow.left.arrow.right", title: "Servizio", color: Theme.info,
                              enabled: true) {
                session.switchServer()
            }
            .accessibilityLabel("Cambia chi serve")
        }
        .frame(height: 30)
    }

    private func scoreTable(_ state: MatchState) -> some View {
        HStack(spacing: 0) {
            teamMark(.us, serving: state.server == .us)
            Spacer(minLength: 2)
            numbers(sets: state.sets(.us), games: state.games(.us))
            VStack(spacing: 2) {
                Text("SET")
                Text("GAME")
            }
            .font(.system(size: 12, weight: .semibold, design: .rounded))
            .foregroundStyle(.secondary)
            .frame(width: 50)
            numbers(sets: state.sets(.them), games: state.games(.them))
            Spacer(minLength: 2)
            teamMark(.them, serving: state.server == .them)
        }
    }

    private func numbers(sets: Int, games: Int) -> some View {
        VStack(spacing: 0) {
            Text("\(sets)")
            Text("\(games)")
        }
        .font(.system(size: 22, weight: .bold, design: .rounded).monospacedDigit())
        .frame(width: 26)
    }

    /// Nome della squadra con il pallino giallo del servizio sopra.
    private func teamMark(_ team: Team, serving: Bool) -> some View {
        VStack(spacing: 2) {
            Circle()
                .fill(serving ? Theme.ball : Color.white.opacity(0.18))
                .frame(width: 9, height: 9)
            Text(team == .us ? "NOI" : "LORO")
                .font(.system(size: 13, weight: .heavy, design: .rounded))
                .foregroundStyle(Theme.color(for: team))
        }
        .frame(width: 40)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(team.label)\(serving ? ", al servizio" : "")")
    }

    @ViewBuilder
    private func statusLine(_ engine: MatchEngine) -> some View {
        let previous = engine.state.completedSets.compactDisplay
        let status = engine.statusLabel
        if !previous.isEmpty || status != nil {
            HStack(spacing: 6) {
                if !previous.isEmpty {
                    Text(previous)
                        .font(.system(size: 13, weight: .semibold, design: .rounded).monospacedDigit())
                        .foregroundStyle(.secondary)
                }
                if let status {
                    Text(status)
                        .font(.system(size: 12, weight: .heavy, design: .rounded))
                        .foregroundStyle(.black)
                        .padding(.horizontal, 6)
                        .background(Theme.ball, in: Capsule())
                }
            }
            .lineLimit(1)
            .minimumScaleFactor(0.7)
        }
    }

    private func pointTile(_ team: Team, engine: MatchEngine) -> some View {
        let serving = engine.state.server == team
        return Button {
            session.point(for: team)
        } label: {
            ZStack(alignment: .top) {
                RoundedRectangle(cornerRadius: 16)
                    .fill(Theme.tile)
                // Striscia colorata: si capisce a colpo d'occhio di chi e' il riquadro.
                UnevenRoundedRectangle(topLeadingRadius: 16, topTrailingRadius: 16)
                    .fill(Theme.color(for: team))
                    .frame(height: 5)
                Text(engine.pointLabel(for: team))
                    .font(.system(size: 56, weight: .bold, design: .rounded).monospacedDigit())
                    .foregroundStyle(.white)
                    .minimumScaleFactor(0.5)
                    .lineLimit(1)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                if serving {
                    Circle()
                        .fill(Theme.ball)
                        .frame(width: 8, height: 8)
                        .frame(maxWidth: .infinity, alignment: .trailing)
                        .padding(.top, 11)
                        .padding(.trailing, 10)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Punto a \(team.label). Adesso \(engine.pointLabel(for: team))")
    }
}

/// Pulsante d'azione colorato in stile watchOS (sfondo tenue, icona piena).
struct WatchActionButton: View {
    let systemImage: String
    let title: String
    let color: Color
    let enabled: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Label(title, systemImage: systemImage)
                .labelStyle(.iconOnly)
                .font(.system(size: 17, weight: .bold))
                .foregroundStyle(enabled ? color : .gray)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background((enabled ? color : .gray).opacity(0.25), in: RoundedRectangle(cornerRadius: 10))
        }
        .buttonStyle(.plain)
        .disabled(!enabled)
    }
}

/// Tabella dei set: una riga per squadra, i game vincenti in verde.
struct SetsTable: View {
    let sets: [SetScore]
    let winner: Team?

    var body: some View {
        Grid(horizontalSpacing: 2, verticalSpacing: 2) {
            row(.us)
            row(.them)
        }
        .font(.system(size: 22, weight: .semibold, design: .rounded).monospacedDigit())
    }

    private func row(_ team: Team) -> some View {
        GridRow {
            HStack(spacing: 2) {
                Text(team == .us ? "NOI" : "LORO")
                    .font(.system(size: 13, weight: .heavy, design: .rounded))
                    .foregroundStyle(Theme.color(for: team))
                if winner == team {
                    Image(systemName: "trophy.fill")
                        .font(.system(size: 12))
                        .foregroundStyle(Theme.ball)
                }
            }
            .frame(width: 58, height: 34)
            .background(Theme.tile)
            ForEach(Array(sets.enumerated()), id: \.offset) { _, set in
                let value = set.isSuperTiebreak ? (team == .us ? set.tiebreakUs : set.tiebreakThem) ?? 0
                                                : (team == .us ? set.us : set.them)
                Text("\(value)")
                    .foregroundStyle(set.winner == team ? Theme.win : .white)
                    .frame(width: 32, height: 34)
                    .background(Theme.tile)
            }
        }
    }
}

/// A vittoria raggiunta: si puo' ancora tornare indietro prima di salvare.
struct MatchWonView: View {
    @Environment(MatchSession.self) private var session

    var body: some View {
        let state = session.state
        VStack(spacing: 10) {
            Text(state.winner == .us ? "Vittoria!" : "Partita persa")
                .font(.system(size: 22, weight: .heavy, design: .rounded))
            SetsTable(sets: state.completedSets, winner: state.winner)
                .clipShape(RoundedRectangle(cornerRadius: 8))
            Spacer(minLength: 0)
            HStack(spacing: 6) {
                WatchActionButton(systemImage: "arrow.uturn.backward", title: "Indietro", color: Theme.danger, enabled: true) {
                    session.undo()
                }
                WatchActionButton(systemImage: "checkmark.circle.fill", title: "Salva partita", color: Theme.info,
                                  enabled: !session.isFinishing) {
                    Task { await session.finish() }
                }
            }
            .frame(height: 40)
        }
        .padding(.top, 4)
    }
}

// MARK: - Controlli

struct ControlsView: View {
    @Environment(MatchSession.self) private var session
    @Binding var page: Int
    @State private var confirmEnd = false

    var body: some View {
        ScrollView {
            VStack(spacing: 8) {
                Button {
                    session.undo()
                    page = 1
                } label: {
                    Label("Indietro", systemImage: "arrow.uturn.backward")
                }
                .disabled(!session.engine.canUndo)

                Button {
                    session.switchServer()
                } label: {
                    Label("Servizio: \(session.state.server.label)", systemImage: "tennisball.fill")
                }
                .tint(Theme.ball)

                Button(role: .destructive) {
                    confirmEnd = true
                } label: {
                    Label("Termina partita", systemImage: "xmark")
                }
                .disabled(session.isFinishing)
            }
        }
        .confirmationDialog("Terminare la partita?", isPresented: $confirmEnd) {
            Button("Termina e salva", role: .destructive) {
                Task { await session.finish() }
            }
            Button("Continua a giocare", role: .cancel) {}
        } message: {
            Text("L'allenamento viene salvato e il risultato inviato all'iPhone.")
        }
    }
}

// MARK: - Dati

struct MetricsView: View {
    @Environment(MatchSession.self) private var session

    var body: some View {
        let metrics = session.workout.metrics
        TimelineView(.periodic(from: session.startDate, by: 1)) { context in
            VStack(alignment: .leading, spacing: 2) {
                Text(PadelFormat.duration(context.date.timeIntervalSince(session.startDate)))
                    .font(.system(size: 34, weight: .bold, design: .rounded).monospacedDigit())
                    .foregroundStyle(Theme.ball)
                metric(value: metrics.heartRate, unit: "BPM", icon: "heart.fill", color: .red)
                metric(value: metrics.activeCalories, unit: "KCAL", icon: "flame.fill", color: Theme.them)
                HStack {
                    small("Media", metrics.averageHeartRate)
                    Spacer()
                    small("Max", metrics.maxHeartRate)
                }
                if let message = metrics.message {
                    Text(message).font(.footnote).foregroundStyle(.secondary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func metric(value: Double?, unit: String, icon: String, color: Color) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 4) {
            Text(value.map { "\(Int($0.rounded()))" } ?? "--")
                .font(.system(size: 30, weight: .semibold, design: .rounded).monospacedDigit())
            Text(unit).font(.system(size: 14, weight: .bold))
            Image(systemName: icon).foregroundStyle(color)
        }
    }

    private func small(_ label: String, _ value: Double?) -> some View {
        VStack(alignment: .leading) {
            Text(label).font(.caption2).foregroundStyle(.secondary)
            Text(value.map { "\(Int($0.rounded())) bpm" } ?? "--")
                .font(.system(size: 17, weight: .semibold, design: .rounded).monospacedDigit())
        }
    }
}
