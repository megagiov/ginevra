#!/usr/bin/env node
/* Aggiorna la versione dell'app nel service worker.
 *
 *   node tools/versione.js           scrive la versione giusta
 *   node tools/versione.js --check   fallisce se e' rimasta vecchia
 *
 * Perche' esiste: il service worker serve l'app dalla memoria del telefono,
 * e il telefono scarica una versione nuova solo se cambia il file sw.js.
 * Senza questo passaggio un aggiornamento pubblicato non arriva mai a chi
 * ha gia' installato l'app: e' successo davvero.
 *
 * La versione e' un'impronta del contenuto dei file, quindi cambia da sola
 * quando cambia qualcosa, e non cambia se non cambia niente.
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const ROOT = path.join(__dirname, '..');
const SW = path.join(ROOT, 'sw.js');
const VERSION_JS = path.join(ROOT, 'js', 'version.js');

function impronta(files) {
  const h = crypto.createHash('sha256');
  files.forEach((f) => {
    h.update(f + '\0');
    h.update(fs.readFileSync(path.join(ROOT, f)));
  });
  return h.digest('hex').slice(0, 10);
}

const sw = fs.readFileSync(SW, 'utf8');
const lista = sw.match(/const SHELL_FILES = \[([\s\S]*?)\];/);
if (!lista) { console.error('Non trovo SHELL_FILES in sw.js'); process.exit(1); }
const files = lista[1].match(/'([^']+)'/g).map((s) => s.slice(1, -1))
  .filter((f) => f !== './' && f !== 'js/version.js');   // './' e' index.html; version.js e' derivato

const VERSION = impronta(files);
const DATA_VERSION = impronta(['data/catalog.json']);

const attuale = (sw.match(/const VERSION = '([^']*)'/) || [])[1];
const attualeData = (sw.match(/const DATA_VERSION = '([^']*)'/) || [])[1];
const attualeJs = fs.existsSync(VERSION_JS) ? (fs.readFileSync(VERSION_JS, 'utf8').match(/'([^']*)'/) || [])[1] : null;

if (process.argv.includes('--check')) {
  if (attuale !== VERSION || attualeData !== DATA_VERSION || attualeJs !== VERSION) {
    console.error('VERSIONE VECCHIA: sw.js dice ' + attuale + '/' + attualeData + ', i file sono ' + VERSION + '/' + DATA_VERSION + '.');
    console.error('Lancia "node tools/versione.js" prima di pubblicare, altrimenti i telefoni non si aggiornano.');
    process.exit(1);
  }
  console.log('Versione aggiornata: ' + VERSION + ' (catalogo ' + DATA_VERSION + ')');
  process.exit(0);
}

const nuovo = sw
  .replace(/const VERSION = '[^']*';/, "const VERSION = '" + VERSION + "';")
  .replace(/const DATA_VERSION = '[^']*';/, "const DATA_VERSION = '" + DATA_VERSION + "';");
fs.writeFileSync(SW, nuovo);
fs.writeFileSync(VERSION_JS, "/* Generato da tools/versione.js: non modificare a mano. */\nwindow.APP_VERSION = '" + VERSION + "';\n");
console.log((attuale === VERSION ? 'Invariata: ' : 'Nuova versione: ') + VERSION + ' (catalogo ' + DATA_VERSION + ')');
