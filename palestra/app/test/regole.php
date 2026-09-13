<?php
declare(strict_types=1);

/**
 * Verifica delle regole di prenotazione sull'implementazione PHP/MySQL.
 *
 * Ricrea il database da zero a ogni esecuzione, quindi non lasciare mai
 * puntare DB_NAME a un database vero.
 *
 * Uso:  php app/test/regole.php
 */

foreach (['Config', 'Db', 'Posta', 'Regole'] as $classe) {
    require __DIR__ . "/../src/$classe.php";
}

use Studio\Db;
use Studio\Regole;
use Studio\RegolaViolata;

require __DIR__ . '/comune.php';

$pdo = preparaDatabase();
Db::usa($pdo);
$pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);

// ---------------------------------------------------------------------------
// Dati di prova
// ---------------------------------------------------------------------------

const ADMIN = 'a1';
const ANNA  = 'c1';
const BRUNO = 'c2';

$pdo->exec("INSERT INTO utenti (id, email, nome, ruolo) VALUES
  ('" . ADMIN . "', 'admin@studio.test', 'Admin', 'admin'),
  ('" . ANNA  . "', 'anna@test.it',      'Anna',  'cliente'),
  ('" . BRUNO . "', 'bruno@test.it',     'Bruno', 'cliente')");

/** Lezioni sempre da 60 minuti, orari in UTC. */
function creaSlot(PDO $pdo, string $id, string $quando, string $tipo, int $capienza): void
{
    $inizio = utc($quando);
    $fine   = utc($quando . ' +60 minutes');
    $pdo->prepare('INSERT INTO slot (id, inizio, fine, tipo, capienza) VALUES (?,?,?,?,?)')
        ->execute([$id, $inizio, $fine, $tipo, $capienza]);
}

creaSlot($pdo, 's_ind',    '+3 days',   'individuale', 1);
creaSlot($pdo, 's_gruppo', '+4 days',   'gruppo',      4);
creaSlot($pdo, 's_presto', '+30 minutes','individuale', 1);   // sotto l'anticipo minimo
creaSlot($pdo, 's_vicino', '+10 hours', 'individuale', 1);    // dentro le 24h
creaSlot($pdo, 's_a',      '+5 days',   'individuale', 1);
creaSlot($pdo, 's_b',      '+6 days',   'individuale', 1);
creaSlot($pdo, 's_c',      '+7 days',   'individuale', 1);
creaSlot($pdo, 's_d',      '+8 days',   'individuale', 1);

// ---------------------------------------------------------------------------
// 1. Crediti
// ---------------------------------------------------------------------------

Regole::accredita(ANNA, 'individuale', 5, ADMIN, 200.00, 'Pacchetto 5 lezioni');
Regole::accredita(ANNA, 'gruppo',     10, ADMIN, 250.00, 'Pacchetto 10 gruppo');

ok('Il saldo e\' la somma dei movimenti (Anna individuale = 5)',
   Regole::saldo(ANNA, 'individuale') === 5);

errore('Un cliente non puo\' accreditarsi da solo',
   fn() => Regole::accredita(ANNA, 'individuale', 50, ANNA),
   'amministratore');

errore('Un acquisto non puo\' essere negativo',
   fn() => Regole::accredita(ANNA, 'gruppo', -3, ADMIN),
   'rettifica');

Regole::accredita(BRUNO, 'gruppo', 1, ADMIN, 30.00, 'Lezione singola');
Regole::accredita(BRUNO, 'gruppo', -1, ADMIN, null, 'Storno', 'rettifica');

ok('Una rettifica negativa azzera il saldo di Bruno',
   Regole::saldo(BRUNO, 'gruppo') === 0);

// ---------------------------------------------------------------------------
// 2. Prenotazione
// ---------------------------------------------------------------------------

$p1 = Regole::prenota('s_ind', ANNA, ANNA);
ok('Anna prenota un individuale', $p1 !== '');

ok('Il credito si scala subito (5 -> 4)', Regole::saldo(ANNA, 'individuale') === 4);

errore('Non si prenota due volte la stessa lezione',
   fn() => Regole::prenota('s_ind', ANNA, ANNA),
   'gia');

errore('Serve l\'anticipo minimo di 2 ore',
   fn() => Regole::prenota('s_presto', ANNA, ANNA),
   'anticipo');

errore('Un cliente non puo\' prenotare per un altro',
   fn() => Regole::prenota('s_gruppo', BRUNO, ANNA),
   'un altro cliente');

errore('Senza credito non si prenota',
   fn() => Regole::prenota('s_gruppo', BRUNO, BRUNO),
   'credito esaurito');

// ---------------------------------------------------------------------------
// 3. Tetto alle prenotazioni aperte
// ---------------------------------------------------------------------------

Regole::prenota('s_a', ANNA, ANNA);
Regole::prenota('s_b', ANNA, ANNA);
Regole::prenota('s_c', ANNA, ANNA);

errore('Massimo 4 prenotazioni future aperte',
   fn() => Regole::prenota('s_d', ANNA, ANNA),
   'prenotazioni future');

// ---------------------------------------------------------------------------
// 4. Disdetta
// ---------------------------------------------------------------------------

$q = $pdo->prepare("SELECT id FROM prenotazioni WHERE slot_id = ? AND cliente_id = ? AND stato = 'prenotata'");

$q->execute(['s_a', ANNA]);
$pa = $q->fetchColumn();

ok('Disdetta oltre 24h: il credito torna',
   Regole::disdici($pa, ANNA) === true);

ok('Dopo la disdetta si puo\' riprenotare la stessa lezione',
   Regole::prenota('s_a', ANNA, ANNA) !== '');

// libera un posto nel tetto per poter prenotare s_vicino
$q->execute(['s_b', ANNA]);
Regole::disdici($q->fetchColumn(), ANNA);

Regole::prenota('s_vicino', ANNA, ANNA);
$q->execute(['s_vicino', ANNA]);
$pv = $q->fetchColumn();

ok('Disdetta sotto le 24h: il credito NON torna',
   Regole::disdici($pv, ANNA) === false);

errore('Una prenotazione gia\' disdetta non si disdice di nuovo',
   fn() => Regole::disdici($pv, ANNA),
   'disdicibile');

$n = $pdo->query("SELECT COUNT(*) FROM movimenti
                   WHERE cliente_id = '" . ANNA . "' AND causale = 'disdetta_in_tempo'")
         ->fetchColumn();
ok('I movimenti di restituzione sono solo quelli delle disdette in tempo (2)',
   (int) $n === 2);

// ---------------------------------------------------------------------------
// 5. Capienza del gruppo
// ---------------------------------------------------------------------------

foreach (['c3' => 'carla', 'c4' => 'dario', 'c5' => 'elena', 'c6' => 'fabio'] as $id => $nome) {
    $pdo->prepare('INSERT INTO utenti (id, email, nome) VALUES (?,?,?)')
        ->execute([$id, "$nome@test.it", ucfirst($nome)]);
    Regole::accredita($id, 'gruppo', 2, ADMIN);
}

// L'amministratore prenota per conto dei clienti: e' la schermata
// "prenota per conto di", quella che tiene l'app allineata alle telefonate.
Regole::prenota('s_gruppo', 'c3', ADMIN);
Regole::prenota('s_gruppo', 'c4', ADMIN);
Regole::prenota('s_gruppo', 'c5', ADMIN);
ok('L\'amministratore puo\' prenotare per conto di un cliente',
   Regole::prenota('s_gruppo', 'c6', ADMIN) !== '');

$liberi = $pdo->query("SELECT posti_liberi FROM slot_disponibilita WHERE id = 's_gruppo'")
              ->fetchColumn();
ok('Il gruppo risulta pieno (0 posti liberi)', (int) $liberi === 0);

Regole::accredita(BRUNO, 'gruppo', 1, ADMIN);
errore('Il quinto posto in un gruppo da 4 viene rifiutato',
   fn() => Regole::prenota('s_gruppo', BRUNO, ADMIN),
   'nessun posto');

// ---------------------------------------------------------------------------
// 6. Presenze
// ---------------------------------------------------------------------------

$q->execute(['s_gruppo', 'c3']);
$pc3 = $q->fetchColumn();

errore('Un cliente non puo\' segnare le presenze',
   fn() => Regole::segnaPresenza($pc3, true, ANNA),
   'amministratore');

Regole::segnaPresenza($pc3, true, ADMIN);
$stato = $pdo->query("SELECT stato FROM prenotazioni WHERE id = '$pc3'")->fetchColumn();
ok('L\'amministratore segna la presenza', $stato === 'presente');

ok('Segnare la presenza non muove crediti',
   (int) $pdo->query("SELECT COUNT(*) FROM movimenti WHERE cliente_id = 'c3'")->fetchColumn() === 2);

// ---------------------------------------------------------------------------
// 7. Atomicita'
// ---------------------------------------------------------------------------

// Una prenotazione rifiutata non deve lasciare traccia: ne' la riga, ne' il
// movimento di scalo. E' il motivo per cui tutto passa da una transazione.
$movPrima = (int) $pdo->query("SELECT COUNT(*) FROM movimenti")->fetchColumn();
$preProma = (int) $pdo->query("SELECT COUNT(*) FROM prenotazioni")->fetchColumn();

try { Regole::prenota('s_gruppo', BRUNO, ADMIN); } catch (RegolaViolata) {}

ok('Una prenotazione rifiutata non lascia movimenti orfani',
   (int) $pdo->query("SELECT COUNT(*) FROM movimenti")->fetchColumn() === $movPrima);
ok('Una prenotazione rifiutata non lascia righe orfane',
   (int) $pdo->query("SELECT COUNT(*) FROM prenotazioni")->fetchColumn() === $preProma);

esito();
