#!/usr/bin/env node
/* Genera le icone PNG dell'app (manubrio arancione su fondo scuro).
 * Disegnate qui invece che scaricate: cosi' restano nitide a ogni misura
 * e non dipendiamo da nessun file esterno.
 *
 *   node tools/make-icons.js
 */
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const BG = [0x0B, 0x0D, 0x11];
const FG = [0xF9, 0x73, 0x16];

function crc32(buf) {
  let c, crc = 0xFFFFFFFF;
  for (let n = 0; n < buf.length; n++) {
    c = (crc ^ buf[n]) & 0xFF;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
    crc = c ^ (crc >>> 8);
  }
  return (crc ^ 0xFFFFFFFF) >>> 0;
}

function chunk(type, data) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length, 0);
  const body = Buffer.concat([Buffer.from(type, 'ascii'), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body), 0);
  return Buffer.concat([len, body, crc]);
}

function encodePng(width, height, rgba) {
  const raw = Buffer.alloc((width * 4 + 1) * height);
  for (let y = 0; y < height; y++) {
    raw[y * (width * 4 + 1)] = 0;   // filtro 0: nessuno
    rgba.copy(raw, y * (width * 4 + 1) + 1, y * width * 4, (y + 1) * width * 4);
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;    // bit depth
  ihdr[9] = 6;    // RGBA
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]),
    chunk('IHDR', ihdr),
    chunk('IDAT', zlib.deflateSync(raw, { level: 9 })),
    chunk('IEND', Buffer.alloc(0))
  ]);
}

// Disegno vettoriale minimo: rettangoli con angoli arrotondati, antialias 3x3.
function draw(size, safe) {
  const S = 3;                  // supersampling
  const W = size * S;
  const acc = new Float32Array(W * W * 3);
  const cov = new Float32Array(W * W);

  function rrect(x, y, w, h, r, color) {
    const x0 = Math.round(x * S), y0 = Math.round(y * S);
    const x1 = Math.round((x + w) * S), y1 = Math.round((y + h) * S);
    const rr = r * S;
    for (let py = Math.max(0, y0); py < Math.min(W, y1); py++) {
      for (let px = Math.max(0, x0); px < Math.min(W, x1); px++) {
        const dx = Math.max(x0 + rr - px - 0.5, 0, px + 0.5 - (x1 - rr));
        const dy = Math.max(y0 + rr - py - 0.5, 0, py + 0.5 - (y1 - rr));
        if (dx * dx + dy * dy > rr * rr) continue;
        const i = py * W + px;
        acc[i * 3] = color[0]; acc[i * 3 + 1] = color[1]; acc[i * 3 + 2] = color[2];
        cov[i] = 1;
      }
    }
  }

  // fondo
  rrect(0, 0, size, size, safe ? 0 : size * 0.22, BG);

  // manubrio, dentro la zona sicura per le icone mascherate
  const m = safe ? size * 0.26 : size * 0.18;   // margine
  const cy = size / 2;
  const barH = size * 0.085;
  const plateH = size * 0.36;
  const innerH = size * 0.22;
  const plateW = size * 0.10;
  const innerW = size * 0.055;
  const r = size * 0.03;

  rrect(m, cy - plateH / 2, plateW, plateH, r, FG);
  rrect(m + plateW, cy - innerH / 2, innerW, innerH, r * 0.7, FG);
  rrect(m + plateW + innerW, cy - barH / 2, size - 2 * m - 2 * (plateW + innerW), barH, r * 0.6, FG);
  rrect(size - m - plateW - innerW, cy - innerH / 2, innerW, innerH, r * 0.7, FG);
  rrect(size - m - plateW, cy - plateH / 2, plateW, plateH, r, FG);

  // riduzione a dimensione finale
  const out = Buffer.alloc(size * size * 4);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      let r0 = 0, g0 = 0, b0 = 0, a0 = 0;
      for (let sy = 0; sy < S; sy++) {
        for (let sx = 0; sx < S; sx++) {
          const i = (y * S + sy) * W + (x * S + sx);
          r0 += acc[i * 3]; g0 += acc[i * 3 + 1]; b0 += acc[i * 3 + 2]; a0 += cov[i];
        }
      }
      const n = S * S;
      const o = (y * size + x) * 4;
      out[o] = Math.round(r0 / n);
      out[o + 1] = Math.round(g0 / n);
      out[o + 2] = Math.round(b0 / n);
      out[o + 3] = Math.round((a0 / n) * 255);
    }
  }
  return out;
}

const dir = path.join(__dirname, '..', 'icons');
fs.mkdirSync(dir, { recursive: true });
[[192, false, 'icon-192.png'], [512, false, 'icon-512.png'], [512, true, 'icon-maskable-512.png']]
  .forEach(([size, safe, name]) => {
    fs.writeFileSync(path.join(dir, name), encodePng(size, size, draw(size, safe)));
    console.log('Scritto icons/' + name);
  });
