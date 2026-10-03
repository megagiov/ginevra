/* Catalogo esercizi iniziale. Serve solo al primo avvio: dopo puoi
 * aggiungere, rinominare o archiviare quello che vuoi dalle impostazioni. */
const SEED = (function () {
  const EXERCISES = [
    // [nome italiano, gruppo, attrezzo, unita', id nel catalogo con foto]
    // Petto
    ['Panca piana bilanciere', 'Petto', 'Bilanciere', 'kg', 'barbell-bench-press-medium-grip'],
    ['Panca inclinata manubri', 'Petto', 'Manubri', 'kg', 'incline-dumbbell-press'],
    ['Croci ai cavi', 'Petto', 'Cavi', 'kg', 'cable-crossover'],
    ['Chest press', 'Petto', 'Macchina', 'kg', 'leverage-chest-press'],
    ['Piegamenti', 'Petto', 'Corpo libero', 'bw', 'pushups'],
    // Schiena
    ['Stacco da terra', 'Schiena', 'Bilanciere', 'kg', 'barbell-deadlift'],
    ['Trazioni alla sbarra', 'Schiena', 'Corpo libero', 'bw', 'pullups'],
    ['Lat machine', 'Schiena', 'Macchina', 'kg', 'wide-grip-lat-pulldown'],
    ['Rematore bilanciere', 'Schiena', 'Bilanciere', 'kg', 'bent-over-barbell-row'],
    ['Pulley basso', 'Schiena', 'Cavi', 'kg', 'seated-cable-rows'],
    // Gambe
    ['Squat bilanciere', 'Gambe', 'Bilanciere', 'kg', 'barbell-squat'],
    ['Pressa 45 gradi', 'Gambe', 'Macchina', 'kg', 'leg-press'],
    ['Affondi manubri', 'Gambe', 'Manubri', 'kg', 'dumbbell-lunges'],
    ['Leg extension', 'Gambe', 'Macchina', 'kg', 'leg-extensions'],
    ['Leg curl', 'Gambe', 'Macchina', 'kg', 'lying-leg-curls'],
    ['Stacco rumeno', 'Gambe', 'Bilanciere', 'kg', 'romanian-deadlift'],
    ['Calf in piedi', 'Gambe', 'Macchina', 'kg', 'standing-calf-raises'],
    // Spalle
    ['Military press', 'Spalle', 'Bilanciere', 'kg', 'standing-military-press'],
    ['Lento avanti manubri', 'Spalle', 'Manubri', 'kg', 'dumbbell-shoulder-press'],
    ['Alzate laterali', 'Spalle', 'Manubri', 'kg', 'side-lateral-raise'],
    ['Alzate posteriori', 'Spalle', 'Manubri', 'kg', 'reverse-flyes'],
    // Braccia
    ['Curl bilanciere', 'Braccia', 'Bilanciere', 'kg', 'barbell-curl'],
    ['Curl manubri', 'Braccia', 'Manubri', 'kg', 'dumbbell-bicep-curl'],
    ['Curl a martello', 'Braccia', 'Manubri', 'kg', 'hammer-curls'],
    ['French press', 'Braccia', 'Bilanciere', 'kg', 'ez-bar-skullcrusher'],
    ['Push down ai cavi', 'Braccia', 'Cavi', 'kg', 'triceps-pushdown'],
    ['Dip alle parallele', 'Braccia', 'Corpo libero', 'bw', 'dips-triceps-version'],
    // Core
    ['Crunch', 'Core', 'Corpo libero', 'bw', 'crunches'],
    ['Plank', 'Core', 'Corpo libero', 'time', 'plank'],
    ['Leg raise', 'Core', 'Corpo libero', 'bw', 'hanging-leg-raise']
  ];

  const ROUTINES = [
    ['Push (petto, spalle, tricipiti)', [
      ['Panca piana bilanciere', 4, '6-8'],
      ['Panca inclinata manubri', 3, '8-10'],
      ['Lento avanti manubri', 3, '8-10'],
      ['Alzate laterali', 3, '12-15'],
      ['Push down ai cavi', 3, '10-12']
    ]],
    ['Pull (schiena, bicipiti)', [
      ['Trazioni alla sbarra', 4, 'max'],
      ['Rematore bilanciere', 4, '6-8'],
      ['Pulley basso', 3, '10-12'],
      ['Curl bilanciere', 3, '8-10'],
      ['Curl a martello', 3, '10-12']
    ]],
    ['Gambe', [
      ['Squat bilanciere', 4, '5-8'],
      ['Stacco rumeno', 3, '8-10'],
      ['Pressa 45 gradi', 3, '10-12'],
      ['Leg curl', 3, '10-12'],
      ['Calf in piedi', 4, '12-15']
    ]]
  ];

  // Popola il database solo se e' vuoto.
  function ensure() {
    return DB.listExercises(true).then((rows) => {
      if (rows.length) return { seeded: false };
      const exercises = EXERCISES.map(([name, muscle, equipment, unit, catalogId]) => ({
        id: DB.uid(),
        name, muscle, equipment,
        unit: unit || 'kg',
        catalogId: catalogId || null,
        archived: false,
        createdAt: Date.now()
      }));
      const byName = {};
      exercises.forEach((e) => { byName[e.name] = e.id; });
      const routines = ROUTINES.map(([name, items], i) => ({
        id: DB.uid(),
        name,
        items: items
          .filter(([exName]) => byName[exName])
          .map(([exName, sets, reps]) => ({ exerciseId: byName[exName], sets, reps, note: '' })),
        createdAt: Date.now() + i
      }));
      return DB.putMany('exercises', exercises)
        .then(() => DB.putMany('routines', routines))
        .then(() => ({ seeded: true, exercises: exercises.length, routines: routines.length }));
    });
  }

  return { ensure, EXERCISES, ROUTINES };
})();
