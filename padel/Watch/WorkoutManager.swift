import Foundation
import Observation

/// Dati mostrati nella pagina "Dati" e salvati nel riepilogo.
@MainActor
@Observable
final class WorkoutMetrics {
    var heartRate: Double?
    var averageHeartRate: Double?
    var maxHeartRate: Double?
    var activeCalories: Double?
    var isRunning = false
    var message: String?

    func reset() {
        heartRate = nil
        averageHeartRate = nil
        maxHeartRate = nil
        activeCalories = nil
        isRunning = false
        message = nil
    }
}

#if HEALTHKIT_YES
import HealthKit

/// Sessione di allenamento per tutta la partita: tiene l'app attiva al
/// polso e salva l'allenamento in Salute. HealthKit non ha il padel, si
/// usa il tennis.
///
/// Swift 6: i delegate di HealthKit arrivano su code private, quindi sono
/// `nonisolated`; estraggono valori `Sendable` e saltano sul MainActor.
/// Le API con completion handler evitano di passare oggetti HealthKit
/// non-Sendable fuori dal MainActor.
@MainActor
final class WorkoutManager: NSObject {
    static let isHealthKitEnabled = true

    let metrics = WorkoutMetrics()
    private let store = HKHealthStore()
    private var session: HKWorkoutSession?
    private var builder: HKLiveWorkoutBuilder?

    func start(indoor: Bool, at date: Date) async {
        guard session == nil else { return }
        guard HKHealthStore.isHealthDataAvailable() else {
            metrics.message = "Salute non disponibile su questo dispositivo"
            return
        }
        let authorized = await requestAuthorization()
        guard authorized else {
            metrics.message = "Autorizza Salute per battito e calorie"
            return
        }

        let configuration = HKWorkoutConfiguration()
        configuration.activityType = .tennis
        configuration.locationType = indoor ? .indoor : .outdoor

        do {
            let session = try HKWorkoutSession(healthStore: store, configuration: configuration)
            let builder = session.associatedWorkoutBuilder()
            builder.dataSource = HKLiveWorkoutDataSource(healthStore: store, workoutConfiguration: configuration)
            session.delegate = self
            builder.delegate = self
            self.session = session
            self.builder = builder
            session.startActivity(with: date)
            builder.beginCollection(withStart: date) { _, error in
                let text = error?.localizedDescription
                Task { @MainActor in
                    if let text { self.metrics.message = "Registrazione non avviata: \(text)" }
                }
            }
        } catch {
            metrics.message = "Allenamento non avviato: \(error.localizedDescription)"
        }
    }

    func stop(at date: Date) async {
        guard let session, let builder else { return }
        session.end()
        await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
            builder.endCollection(withEnd: date) { _, _ in continuation.resume() }
        }
        await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
            builder.finishWorkout { _, _ in continuation.resume() }
        }
        self.session = nil
        self.builder = nil
        metrics.isRunning = false
    }

    func reset() {
        metrics.reset()
    }

    private func requestAuthorization() async -> Bool {
        let share: Set<HKSampleType> = [HKObjectType.workoutType()]
        let read: Set<HKObjectType> = [
            HKQuantityType(.heartRate),
            HKQuantityType(.activeEnergyBurned),
            HKObjectType.workoutType()
        ]
        return await withCheckedContinuation { (continuation: CheckedContinuation<Bool, Never>) in
            store.requestAuthorization(toShare: share, read: read) { success, _ in
                continuation.resume(returning: success)
            }
        }
    }

    fileprivate struct Snapshot: Sendable {
        var heartRate: Double?
        var averageHeartRate: Double?
        var maxHeartRate: Double?
        var activeCalories: Double?
    }

    fileprivate func apply(_ s: Snapshot) {
        if let v = s.heartRate { metrics.heartRate = v }
        if let v = s.averageHeartRate { metrics.averageHeartRate = v }
        if let v = s.maxHeartRate { metrics.maxHeartRate = v }
        if let v = s.activeCalories { metrics.activeCalories = v }
    }
}

extension WorkoutManager: HKWorkoutSessionDelegate {
    nonisolated func workoutSession(_ workoutSession: HKWorkoutSession, didChangeTo toState: HKWorkoutSessionState,
                                    from fromState: HKWorkoutSessionState, date: Date) {
        let running = toState == .running
        Task { @MainActor in self.metrics.isRunning = running }
    }

    nonisolated func workoutSession(_ workoutSession: HKWorkoutSession, didFailWithError error: Error) {
        let text = error.localizedDescription
        Task { @MainActor in self.metrics.message = "Errore allenamento: \(text)" }
    }
}

extension WorkoutManager: HKLiveWorkoutBuilderDelegate {
    nonisolated func workoutBuilderDidCollectEvent(_ workoutBuilder: HKLiveWorkoutBuilder) {}

    nonisolated func workoutBuilder(_ workoutBuilder: HKLiveWorkoutBuilder, didCollectDataOf collectedTypes: Set<HKSampleType>) {
        let bpm = HKUnit.count().unitDivided(by: .minute())
        var snapshot = Snapshot()
        if let hr = workoutBuilder.statistics(for: HKQuantityType(.heartRate)) {
            snapshot.heartRate = hr.mostRecentQuantity()?.doubleValue(for: bpm)
            snapshot.averageHeartRate = hr.averageQuantity()?.doubleValue(for: bpm)
            snapshot.maxHeartRate = hr.maximumQuantity()?.doubleValue(for: bpm)
        }
        if let energy = workoutBuilder.statistics(for: HKQuantityType(.activeEnergyBurned)) {
            snapshot.activeCalories = energy.sumQuantity()?.doubleValue(for: .kilocalorie())
        }
        let result = snapshot
        Task { @MainActor in self.apply(result) }
    }
}

#else

/// Versione senza HealthKit (PADEL_HEALTHKIT = NO): stessa interfaccia,
/// nessun dato di salute. Il resto dell'app funziona uguale.
@MainActor
final class WorkoutManager {
    static let isHealthKitEnabled = false

    let metrics = WorkoutMetrics()

    func start(indoor: Bool, at date: Date) async {
        metrics.isRunning = true
        metrics.message = "HealthKit disattivato in questa build"
    }

    func stop(at date: Date) async {
        metrics.isRunning = false
    }

    func reset() {
        metrics.reset()
    }
}

#endif
