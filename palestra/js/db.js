/* Livello dati: IndexedDB. Nessuna dipendenza, funziona offline.
 *
 * Store:
 *   exercises  {id, name, muscle, equipment, unit, archived, createdAt}
 *   routines   {id, name, items:[{exerciseId, sets, reps, note}], createdAt}
 *   sessions   {id, date, name, routineId, startedAt, endedAt, note}
 *   sets       {id, sessionId, exerciseId, weight, reps, rpe, warmup, note, ts}
 *   meta       {k, v}
 */
const DB = (function () {
  const NAME = 'palestra';
  const VERSION = 1;
  let dbp = null;

  function uid() {
    if (self.crypto && crypto.randomUUID) return crypto.randomUUID();
    return 'x' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
  }

  function open() {
    if (dbp) return dbp;
    dbp = new Promise((resolve, reject) => {
      const req = indexedDB.open(NAME, VERSION);
      req.onupgradeneeded = (ev) => {
        const db = req.result;
        if (!db.objectStoreNames.contains('exercises')) {
          const s = db.createObjectStore('exercises', { keyPath: 'id' });
          s.createIndex('by_name', 'name', { unique: false });
        }
        if (!db.objectStoreNames.contains('routines')) {
          db.createObjectStore('routines', { keyPath: 'id' });
        }
        if (!db.objectStoreNames.contains('sessions')) {
          const s = db.createObjectStore('sessions', { keyPath: 'id' });
          s.createIndex('by_started', 'startedAt', { unique: false });
        }
        if (!db.objectStoreNames.contains('sets')) {
          const s = db.createObjectStore('sets', { keyPath: 'id' });
          s.createIndex('by_session', 'sessionId', { unique: false });
          s.createIndex('by_exercise', 'exerciseId', { unique: false });
        }
        if (!db.objectStoreNames.contains('meta')) {
          db.createObjectStore('meta', { keyPath: 'k' });
        }
        void ev;
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
      req.onblocked = () => reject(new Error('Database bloccato da un altra scheda aperta'));
    });
    return dbp;
  }

  function tx(stores, mode, fn) {
    return open().then((db) => new Promise((resolve, reject) => {
      const t = db.transaction(stores, mode);
      let out;
      t.oncomplete = () => resolve(out);
      t.onerror = () => reject(t.error);
      t.onabort = () => reject(t.error || new Error('Transazione annullata'));
      out = fn(t);
      if (out && typeof out.then === 'function') {
        throw new Error('fn deve essere sincrona: usa le richieste della transazione');
      }
    }));
  }

  function reqp(request) {
    return new Promise((resolve, reject) => {
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  /* ---- primitive ---- */

  function getAll(store, index, query) {
    return open().then((db) => {
      const t = db.transaction(store, 'readonly');
      const src = index ? t.objectStore(store).index(index) : t.objectStore(store);
      return reqp(src.getAll(query === undefined ? null : query));
    });
  }

  function get(store, id) {
    return open().then((db) => reqp(db.transaction(store, 'readonly').objectStore(store).get(id)));
  }

  function put(store, value) {
    return tx([store], 'readwrite', (t) => { t.objectStore(store).put(value); }).then(() => value);
  }

  function putMany(store, values) {
    return tx([store], 'readwrite', (t) => {
      const os = t.objectStore(store);
      values.forEach((v) => os.put(v));
    }).then(() => values);
  }

  function del(store, id) {
    return tx([store], 'readwrite', (t) => { t.objectStore(store).delete(id); });
  }

  function clearAll() {
    return tx(['exercises', 'routines', 'sessions', 'sets', 'meta'], 'readwrite', (t) => {
      ['exercises', 'routines', 'sessions', 'sets', 'meta'].forEach((s) => t.objectStore(s).clear());
    });
  }

  /* ---- impostazioni ---- */

  const DEFAULT_SETTINGS = {
    restSeconds: 120,
    sound: true,
    vibrate: true,
    autoRest: true,
    unit: 'kg'
  };

  function getSettings() {
    return get('meta', 'settings').then((row) => Object.assign({}, DEFAULT_SETTINGS, (row && row.v) || {}));
  }

  function saveSettings(patch) {
    return getSettings().then((cur) => {
      const next = Object.assign({}, cur, patch);
      return put('meta', { k: 'settings', v: next }).then(() => next);
    });
  }

  /* ---- esercizi ---- */

  function listExercises(includeArchived) {
    return getAll('exercises').then((rows) => rows
      .filter((e) => includeArchived || !e.archived)
      .sort((a, b) => a.name.localeCompare(b.name, 'it')));
  }

  function createExercise(data) {
    const ex = {
      id: uid(),
      name: (data.name || '').trim(),
      muscle: data.muscle || 'Altro',
      equipment: data.equipment || '',
      unit: data.unit || 'kg',
      catalogId: data.catalogId || null,
      img: data.img || null,
      archived: false,
      createdAt: Date.now()
    };
    if (!ex.name) return Promise.reject(new Error('Serve un nome esercizio'));
    return put('exercises', ex);
  }

  /* ---- schede ---- */

  function listRoutines() {
    return getAll('routines').then((r) => r.sort((a, b) => a.createdAt - b.createdAt));
  }

  function createRoutine(name) {
    const r = { id: uid(), name: (name || 'Nuova scheda').trim(), items: [], createdAt: Date.now() };
    return put('routines', r);
  }

  /* ---- sessioni ---- */

  function listSessions() {
    return getAll('sessions').then((r) => r.sort((a, b) => b.startedAt - a.startedAt));
  }

  function activeSession() {
    return listSessions().then((rows) => rows.find((s) => !s.endedAt) || null);
  }

  function startSession(data) {
    const now = Date.now();
    const s = {
      id: uid(),
      date: new Date(now).toISOString().slice(0, 10),
      name: data.name || 'Allenamento',
      routineId: data.routineId || null,
      plan: data.plan || [],
      startedAt: now,
      endedAt: null,
      note: ''
    };
    return put('sessions', s);
  }

  function endSession(id) {
    return get('sessions', id).then((s) => {
      if (!s) return null;
      s.endedAt = Date.now();
      return put('sessions', s);
    });
  }

  function deleteSession(id) {
    return getAll('sets', 'by_session', IDBKeyRange.only(id)).then((rows) =>
      tx(['sessions', 'sets'], 'readwrite', (t) => {
        t.objectStore('sessions').delete(id);
        const os = t.objectStore('sets');
        rows.forEach((r) => os.delete(r.id));
      }));
  }

  /* ---- serie ---- */

  function setsOfSession(sessionId) {
    return getAll('sets', 'by_session', IDBKeyRange.only(sessionId))
      .then((rows) => rows.sort((a, b) => a.ts - b.ts));
  }

  function setsOfExercise(exerciseId) {
    return getAll('sets', 'by_exercise', IDBKeyRange.only(exerciseId))
      .then((rows) => rows.sort((a, b) => a.ts - b.ts));
  }

  function addSet(data) {
    const s = {
      id: uid(),
      sessionId: data.sessionId,
      exerciseId: data.exerciseId,
      weight: Number(data.weight) || 0,
      reps: Number(data.reps) || 0,
      rpe: data.rpe === '' || data.rpe == null ? null : Number(data.rpe),
      warmup: !!data.warmup,
      note: data.note || '',
      ts: Date.now()
    };
    return put('sets', s);
  }

  function updateSet(s) { return put('sets', s); }
  function deleteSet(id) { return del('sets', id); }

  /* ---- export / import ---- */

  function exportAll() {
    return Promise.all([
      getAll('exercises'), getAll('routines'), getAll('sessions'), getAll('sets'), getAll('meta')
    ]).then(([exercises, routines, sessions, sets, meta]) => ({
      format: 'palestra-backup',
      version: 1,
      exportedAt: new Date().toISOString(),
      exercises, routines, sessions, sets, meta
    }));
  }

  // mode: 'replace' azzera tutto, 'merge' aggiunge senza toccare quello che c'e'
  function importAll(data, mode) {
    if (!data || data.format !== 'palestra-backup') {
      return Promise.reject(new Error('File non riconosciuto: manca il marcatore palestra-backup'));
    }
    const step = mode === 'replace' ? clearAll() : Promise.resolve();
    return step.then(() => tx(['exercises', 'routines', 'sessions', 'sets', 'meta'], 'readwrite', (t) => {
      ['exercises', 'routines', 'sessions', 'sets', 'meta'].forEach((name) => {
        const rows = data[name] || [];
        const os = t.objectStore(name);
        rows.forEach((r) => os.put(r));
      });
    })).then(() => ({
      exercises: (data.exercises || []).length,
      sessions: (data.sessions || []).length,
      sets: (data.sets || []).length
    }));
  }

  return {
    uid, open, get, getAll, put, putMany, del, clearAll,
    getSettings, saveSettings,
    listExercises, createExercise,
    listRoutines, createRoutine,
    listSessions, activeSession, startSession, endSession, deleteSession,
    setsOfSession, setsOfExercise, addSet, updateSet, deleteSet,
    exportAll, importAll
  };
})();
