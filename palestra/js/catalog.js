/* Catalogo esercizi con foto: 876 schede da free-exercise-db (dominio
 * pubblico). Il file data/catalog.json viene caricato solo quando apri il
 * catalogo la prima volta, poi resta in cache. Le foto stanno sul CDN e il
 * service worker le conserva man mano che le apri. */
const Catalog = (function () {
  let data = null;
  let loading = null;

  function load() {
    if (data) return Promise.resolve(data);
    if (loading) return loading;
    loading = fetch('data/catalog.json')
      .then((r) => {
        if (!r.ok) throw new Error('catalogo non raggiungibile (HTTP ' + r.status + ')');
        return r.json();
      })
      .then((json) => { data = json; loading = null; return data; })
      .catch((e) => { loading = null; throw e; });
    return loading;
  }

  // L'indirizzo delle foto non deve dipendere dal catalogo: all'apertura la
  // lista si disegna prima che il catalogo sia caricato, e senza questo
  // l'indirizzo usciva monco (relativo) e tutte le foto sparivano.
  const CDN = 'https://cdn.jsdelivr.net/gh/yuhonas/free-exercise-db@main/exercises/';

  function imageUrl(rel) {
    if (!rel) return '';
    if (/^https?:\/\//.test(rel)) return rel;
    return ((data && data.cdn) || CDN) + rel;
  }

  function normalize(s) {
    return String(s || '').toLowerCase()
      .normalize('NFD').replace(/[̀-ͯ]/g, '');
  }

  // Cerca su nome inglese + chiavi italiane, filtra per muscolo e attrezzo.
  function search(query, filters) {
    if (!data) return [];
    const f = filters || {};
    const q = normalize(query).trim();
    const terms = q ? q.split(/\s+/) : [];
    return data.items.filter((it) => {
      if (f.muscle && it.m.indexOf(f.muscle) === -1 && it.s.indexOf(f.muscle) === -1) return false;
      if (f.equipment && it.eq !== f.equipment) return false;
      if (!terms.length) return true;
      // nome italiano e inglese: in palestra molti nomi si dicono in inglese
      const hay = normalize(it.n + ' ' + (it.en || '') + ' ' + it.k + ' ' + it.m.join(' ') + ' ' + it.eq);
      return terms.every((t) => hay.indexOf(t) !== -1);
    });
  }

  function get(id) {
    if (!data) return null;
    return data.items.filter((i) => i.id === id)[0] || null;
  }

  function muscles() {
    if (!data) return [];
    const set = {};
    data.items.forEach((i) => i.m.forEach((m) => { set[m] = (set[m] || 0) + 1; }));
    return Object.keys(set).sort((a, b) => a.localeCompare(b, 'it'));
  }

  function equipment() {
    if (!data) return [];
    const set = {};
    data.items.forEach((i) => { set[i.eq] = (set[i.eq] || 0) + 1; });
    return Object.keys(set).sort((a, b) => a.localeCompare(b, 'it'));
  }

  // Unita' di misura sensata a partire dall'attrezzo.
  function unitFor(item) {
    if (!item) return 'kg';
    if (item.cat === 'Stretching') return 'time';
    if (item.eq === 'Corpo libero') return 'bw';
    return 'kg';
  }

  return { load, search, get, imageUrl, muscles, equipment, unitFor, loaded: () => !!data };
})();
