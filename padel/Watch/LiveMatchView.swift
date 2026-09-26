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
        .toolbar(.hidden, for: .navigationBar)
    }
}

// MARK: - Segnapunti

struct ScoreboardView: View {
    @Environment(MatchSession.self) private var session

    var body: some View {
        let engine = session.engine
        let state = engine.state
        if state.isFinished {
            MatchWonView()
        } else {
            VStack(spacing: 4) {
                header(engine)
                HStack(spacing: 5) {
                    teamButton(.us, engine: engine)
                    teamButton(.them, engine: engine)
                }
            }
            .padding(.horizontal, 2)
            .ignoresSafeArea(edges: .bottom)
        }
    }

    private func header(_ engine: MatchEngine) -> some View {
        HStack(spacing: 6) {
            if engine.state.completedSets.isEmpty {
                Text("Set 1").foregroundStyle(.secondary)
            } else {
                Text(engine.state.completedSets.compactDisplay)
                    .foregroundStyle(.white)
            }
            Spacer(minLength: 2)
            if let status = engine.statusLabel {
                Text(status)
                    .font(.system(size: 13, weight: .heavy, design: .rounded))
                    .foregroundStyle(.black)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 1)
                    .background(Theme.ball, in: Capsule())
            }
        }
        .font(.system(size: 15, weight: .semibold, design: .rounded).monospacedDigit())
        .lineLimit(1)
        .minimumScaleFactor(0.7)
    }

    private func teamButton(_ team: Team, engine: MatchEngine) -> some View {
        let state = engine.state
        let serving = state.server == team
        let color = Theme.color(for: team)
        return Button {
            session.point(for: team)
        } label: {
            VStack(spacing: 0) {
                HStack(spacing: 3) {
                    Text(team == .us ? "NOI" : "LORO")
                        .font(.system(size: 15, weight: .black, design: .rounded))
                    if serving {
                        Image(systemName: "tennisball.fill")
                            .font(.system(size: 13, weight: .bold))
                    }
                }
                .frame(height: 18)
                Spacer(minLength: 0)
                Text(engine.pointLabel(for: team))
                    .font(.system(size: 60, weight: .heavy, design: .rounded).monospacedDigit())
                    .minimumScaleFactor(0.5)
                    .lineLimit(1)
                Spacer(minLength: 0)
                Text("\(state.games(team))")
                    .font(.system(size: 30, weight: .bold, design: .rounded).monospacedDigit())
                Text("game")
                    .font(.system(size: 11, weight: .semibold))
                    .opacity(0.8)
                setDots(won: state.sets(team))
                    .padding(.top, 3)
            }
            .foregroundStyle(.black)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding(.vertical, 6)
            .background(color, in: RoundedRectangle(cornerRadius: 14))
            .overlay {
                RoundedRectangle(cornerRadius: 14)
                    .strokeBorder(serving ? Theme.ball : .clear, lineWidth: 4)
            }
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(team.label): \(engine.pointLabel(for: team)), \(state.games(team)) game\(serving ? ", al servizio" : "")")
        .accessibilityHint("Tocca per assegnare il punto")
    }

    private func setDots(won: Int) -> some View {
        HStack(spacing: 4) {
            ForEach(0..<MatchRules.setsToWin, id: \.self) { i in
                Circle()
                    .fill(i < won ? Color.black : Color.black.opacity(0.2))
                    .frame(width: 8, height: 8)
            }
        }
    }
}

/// A vittoria raggiunta: si puo' ancora annullare prima di salvare.
struct MatchWonView: View {
    @Environment(MatchSession.self) private var session

    var body: some View {
        let state = session.state
        ScrollView {
            VStack(spacing: 8) {
                Text(state.winner == .us ? "Vittoria!" : "Sconfitta")
                    .font(.system(size: 30, weight: .heavy, design: .rounded))
                    .foregroundStyle(state.winner == .us ? Theme.us : Theme.them)
                Text(state.completedSets.compactDisplay)
                    .font(.system(size: 20, weight: .bold, design: .rounded).monospacedDigit())
                Button {
                    Task { await session.finish() }
                } label: {
                    Label("Salva partita", systemImage: "checkmark.circle.fill")
                }
                .tint(Theme.us)
                .disabled(session.isFinishing)
                Button {
                    session.undo()
                } label: {
                    Label("Annulla ultimo punto", systemImage: "arrow.uturn.backward")
                }
            }
        }
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
                    Label("Annulla punto", systemImage: "arrow.uturn.backward")
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
