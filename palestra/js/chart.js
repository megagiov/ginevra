/* Grafico a linea in SVG, scritto a mano: nessuna libreria da scaricare,
 * quindi funziona anche senza rete. Restituisce una stringa SVG. */
const Chart = (function () {
  const W = 320, H = 170;
  const PAD = { top: 12, right: 10, bottom: 22, left: 34 };

  function esc(s) {
    return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  }

  function niceTicks(min, max, count) {
    if (min === max) { min -= 1; max += 1; }
    const raw = (max - min) / count;
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const norm = raw / mag;
    const step = (norm >= 5 ? 10 : norm >= 2 ? 5 : norm >= 1 ? 2 : 1) * mag;
    const start = Math.floor(min / step) * step;
    const ticks = [];
    for (let v = start; v <= max + step * 0.5; v += step) ticks.push(Math.round(v * 100) / 100);
    return ticks;
  }

  function fmtDate(ts) {
    const d = new Date(ts);
    return d.getDate() + '/' + (d.getMonth() + 1);
  }

  // points: [{x: timestamp, y: numero}]
  function line(points, opts) {
    const o = opts || {};
    if (!points || points.length === 0) {
      return '<p class="empty">Nessun dato ancora: registra qualche serie e il grafico si riempie.</p>';
    }
    if (points.length === 1) {
      const p = points[0];
      return '<p class="empty">Una sola sessione registrata (' + esc(fmtDate(p.x)) + ': ' +
        esc(o.format ? o.format(p.y) : p.y) + '). Dalla seconda in poi vedi la curva.</p>';
    }

    const xs = points.map((p) => p.x);
    const ys = points.map((p) => p.y);
    const xMin = Math.min.apply(null, xs), xMax = Math.max.apply(null, xs);
    const yMinRaw = Math.min.apply(null, ys), yMaxRaw = Math.max.apply(null, ys);
    const ticks = niceTicks(yMinRaw, yMaxRaw, 4);
    const yMin = Math.min(ticks[0], yMinRaw), yMax = Math.max(ticks[ticks.length - 1], yMaxRaw);

    const plotW = W - PAD.left - PAD.right;
    const plotH = H - PAD.top - PAD.bottom;
    const sx = (x) => PAD.left + (xMax === xMin ? plotW / 2 : ((x - xMin) / (xMax - xMin)) * plotW);
    const sy = (y) => PAD.top + plotH - (yMax === yMin ? plotH / 2 : ((y - yMin) / (yMax - yMin)) * plotH);

    let out = '<svg viewBox="0 0 ' + W + ' ' + H + '" class="chart' + (o.cls ? ' ' + o.cls : '') +
      '" preserveAspectRatio="none" role="img" aria-label="' + esc(o.label || 'Andamento nel tempo') + '">';

    ticks.forEach((t) => {
      const y = sy(t);
      out += '<line x1="' + PAD.left + '" y1="' + y.toFixed(1) + '" x2="' + (W - PAD.right) +
        '" y2="' + y.toFixed(1) + '" class="grid"/>';
      out += '<text x="' + (PAD.left - 5) + '" y="' + (y + 3.5).toFixed(1) + '" class="axis" text-anchor="end">' +
        esc(t) + '</text>';
    });

    const d = points.map((p, i) => (i ? 'L' : 'M') + sx(p.x).toFixed(1) + ' ' + sy(p.y).toFixed(1)).join(' ');
    const area = d + ' L' + sx(points[points.length - 1].x).toFixed(1) + ' ' + (PAD.top + plotH) +
      ' L' + sx(points[0].x).toFixed(1) + ' ' + (PAD.top + plotH) + ' Z';
    out += '<path d="' + area + '" class="area"/>';
    out += '<path d="' + d + '" class="line"/>';

    points.forEach((p) => {
      out += '<circle cx="' + sx(p.x).toFixed(1) + '" cy="' + sy(p.y).toFixed(1) + '" r="2.6" class="dot"><title>' +
        esc(fmtDate(p.x) + ' — ' + (o.format ? o.format(p.y) : p.y)) + '</title></circle>';
    });

    const first = points[0], last = points[points.length - 1];
    out += '<text x="' + PAD.left + '" y="' + (H - 6) + '" class="axis">' + esc(fmtDate(first.x)) + '</text>';
    out += '<text x="' + (W - PAD.right) + '" y="' + (H - 6) + '" class="axis" text-anchor="end">' +
      esc(fmtDate(last.x)) + '</text>';
    out += '</svg>';
    return out;
  }

  return { line };
})();
