import SwiftUI
import PadelKit

struct SetupView: View {
    @Environment(MatchSession.self) private var session

    // Ricorda l'ultima scelta.
    @AppStorage("setup.deuceRule") private var deuceRule: DeuceRule = .goldenPoint
    @AppStorage("setup.format") private var format: MatchFormat = .bestOfThree
    @AppStorage("setup.firstServer") private var firstServer: Team = .us
    @AppStorage("setup.indoor") private var indoor = false

    var body: some View {
        List {
            Picker("Sul 40-40", selection: $deuceRule) {
                ForEach(DeuceRule.allCases, id: \.self) { Text($0.label).tag($0) }
            }
            Picker("Formato", selection: $format) {
                Text("Al meglio dei 3").tag(MatchFormat.bestOfThree)
                Text("2 set + STB a 10").tag(MatchFormat.twoSetsSuperTiebreak)
            }
            Picker("Serve prima", selection: $firstServer) {
                ForEach(Team.allCases, id: \.self) { Text($0.label).tag($0) }
            }
            Toggle("Campo coperto", isOn: $indoor)

            Button {
                session.start(rules: MatchRules(deuceRule: deuceRule, format: format,
                                                firstServer: firstServer, indoor: indoor))
            } label: {
                Label("Inizia partita", systemImage: "play.fill")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
            }
            .listRowBackground(Theme.us)
            .foregroundStyle(.black)
        }
        .navigationTitle("Padel")
    }
}
