import SwiftUI
import SwiftData
import Charts
import PadelKit

struct StatsView: View {
    @Query(sort: \Match.date) private var matches: [Match]
    @Query(sort: \Player.name) private var players: [Player]
    @State private var period: StatsPeriod = .allTime

    private var stats: PadelStatistics {
        PadelStatistics(matches: matches.map(\.record), playerNames: MatchStore.names(of: players), period: period)
    }

    var body: some View {
        let stats = stats
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    Picker("Periodo", selection: $period) {
                        ForEach(StatsPeriod.allCases) { Text($0.label).tag($0) }
                    }
                    .pickerStyle(.segmented)

                    if stats.played == 0 {
                        ContentUnavailableView("Nessuna partita nel periodo", systemImage: "chart.bar",
                                               description: Text("Le statistiche contano solo le partite con un vincitore."))
                    } else {
                        summaryGrid(stats)
                        monthlyChart(stats)
                        trendChart(stats)
                        partnersSection(stats)
                        opponentsSection(stats)
                    }
                }
                .padding()
            }
            .navigationTitle("Statistiche")
        }
    }

    // MARK: - Riepilogo

    private func summaryGrid(_ s: PadelStatistics) -> some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            StatTile(title: "Partite", value: "\(s.played)")
            StatTile(title: "Vinte – Perse", value: "\(s.won) – \(s.lost)")
            StatTile(title: "% vittorie", value: s.winPercentage.formatted(.number.precision(.fractionLength(0))) + "%",
                     color: s.winPercentage >= 50 ? Theme.win : Theme.loss)
            StatTile(title: "Set vinti – persi", value: "\(s.setsWon) – \(s.setsLost)")
            StatTile(title: "Ore in campo", value: s.hoursOnCourt.formatted(.number.precision(.fractionLength(1))))
            StatTile(title: "Calorie totali", value: "\(Int(s.totalCalories.rounded())) kcal")
            StatTile(title: "Serie attuale", value: s.streak.label, color: streakColor(s.streak))
        }
    }

    private func streakColor(_ streak: Streak) -> Color {
        switch streak {
        case .wins: Theme.win
        case .losses: Theme.loss
        case .none: .primary
        }
    }

    // MARK: - Grafici

    private func monthlyChart(_ s: PadelStatistics) -> some View {
        Card(title: "Vinte e perse per mese") {
            Chart(s.months) { bucket in
                BarMark(x: .value("Mese", bucket.month, unit: .month), y: .value("Partite", bucket.won))
                    .foregroundStyle(by: .value("Esito", "Vinte"))
                BarMark(x: .value("Mese", bucket.month, unit: .month), y: .value("Partite", bucket.lost))
                    .foregroundStyle(by: .value("Esito", "Perse"))
            }
            .chartForegroundStyleScale(["Vinte": Theme.win, "Perse": Theme.loss])
            .chartXAxis {
                AxisMarks(values: .stride(by: .month)) { _ in
                    AxisGridLine()
                    AxisValueLabel(format: .dateTime.month(.narrow))
                }
            }
            .frame(height: 200)
        }
    }

    private func trendChart(_ s: PadelStatistics) -> some View {
        Card(title: "% vittorie nel tempo") {
            Chart(s.winRateTrend) { point in
                LineMark(x: .value("Data", point.date), y: .value("% vittorie", point.percentage))
                    .interpolationMethod(.monotone)
                    .foregroundStyle(Theme.win)
                RuleMark(y: .value("Pareggio", 50))
                    .foregroundStyle(.secondary.opacity(0.4))
                    .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
            }
            .chartYScale(domain: 0...100)
            .frame(height: 180)
        }
    }

    // MARK: - Compagni e avversari

    private func partnersSection(_ s: PadelStatistics) -> some View {
        Card(title: "Classifica compagni") {
            if s.partners.isEmpty {
                Text("Indica il compagno nelle partite per vedere la classifica.")
                    .font(.subheadline).foregroundStyle(.secondary)
            } else {
                let best = s.bestPartner?.playerID
                VStack(spacing: 8) {
                    ForEach(s.partners) { p in
                        HStack {
                            if p.playerID == best {
                                Image(systemName: "star.fill").foregroundStyle(Theme.ball)
                            }
                            Text(p.name).fontWeight(p.playerID == best ? .bold : .regular)
                            Spacer()
                            Text("\(p.won)V \(p.lost)S").monospacedDigit().foregroundStyle(.secondary)
                            Text(p.winPercentage.formatted(.number.precision(.fractionLength(0))) + "%")
                                .monospacedDigit().bold().frame(width: 52, alignment: .trailing)
                        }
                        .padding(8)
                        .background(p.playerID == best ? Theme.win.opacity(0.15) : .clear, in: RoundedRectangle(cornerRadius: 8))
                    }
                    Text("Il miglior compagno serve almeno \(PadelStatistics.minimumMatchesForBestPartner) partite insieme.")
                        .font(.caption).foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }

    private func opponentsSection(_ s: PadelStatistics) -> some View {
        Card(title: "Bilancio contro gli avversari") {
            if s.opponents.isEmpty {
                Text("Indica gli avversari nelle partite per vedere il bilancio.")
                    .font(.subheadline).foregroundStyle(.secondary)
            } else {
                VStack(spacing: 8) {
                    ForEach(s.opponents) { o in
                        HStack {
                            Text(o.name)
                            Spacer()
                            Text("\(o.won) – \(o.lost)")
                                .monospacedDigit().bold()
                                .foregroundStyle(o.won > o.lost ? Theme.win : o.won < o.lost ? Theme.loss : .primary)
                        }
                    }
                }
            }
        }
    }
}

struct StatTile: View {
    let title: String
    let value: String
    var color: Color = .primary

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title).font(.caption).foregroundStyle(.secondary)
            Text(value)
                .font(.title2.bold().monospacedDigit())
                .foregroundStyle(color)
                .minimumScaleFactor(0.6)
                .lineLimit(1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(.fill.tertiary, in: RoundedRectangle(cornerRadius: 12))
    }
}

struct Card<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title).font(.headline)
            content
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.fill.quaternary, in: RoundedRectangle(cornerRadius: 16))
    }
}
