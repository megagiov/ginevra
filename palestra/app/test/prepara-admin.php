<?php
declare(strict_types=1);
/** Database e dati di prova per test/admin.sh */

foreach (['Config', 'Db', 'Posta', 'Regole'] as $c) { require __DIR__ . "/../src/$c.php"; }
require __DIR__ . '/comune.php';

use Studio\Db;
use Studio\Regole;

$pdo = preparaDatabase();
Db::usa($pdo);

$pdo->exec("INSERT INTO utenti (id, email, nome, ruolo, telefono, note) VALUES
  ('a1', 'admin@studio.test', 'Il Trainer', 'admin', NULL, NULL),
  ('c1', 'anna@test.it',  'Anna Rossi',  'cliente', '333111', 'Spalla destra da riabilitare'),
  ('c2', 'bruno@test.it', 'Bruno Bianchi','cliente', NULL, NULL)");

// Una lezione oggi, gia' passata di un'ora: serve per le presenze.
$fuso = new DateTimeZone('Europe/Rome');
$utc  = fn(DateTimeImmutable $d) => $d->setTimezone(new DateTimeZone('UTC'))->format('Y-m-d H:i:s');
$ora  = new DateTimeImmutable('now', $fuso);

$passata = $ora->modify('-90 minutes')->setTime((int) $ora->modify('-90 minutes')->format('H'), 0);
$pdo->prepare('INSERT INTO slot (id, inizio, fine, tipo, capienza) VALUES (?,?,?,?,?)')
    ->execute(['oggi1', $utc($passata), $utc($passata->modify('+60 minutes')), 'gruppo', 4]);

// Una lezione fra tre giorni, libera.
$futura = (new DateTimeImmutable('+3 days', $fuso))->setTime(19, 0);
$pdo->prepare('INSERT INTO slot (id, inizio, fine, tipo, capienza) VALUES (?,?,?,?,?)')
    ->execute(['fut1', $utc($futura), $utc($futura->modify('+60 minutes')), 'individuale', 1]);

Regole::accredita('c1', 'gruppo', 5, 'a1', 120.00, 'Pacchetto iniziale');
Regole::accredita('c1', 'individuale', 1, 'a1', 45.00, 'Prova');
// La lezione di oggi e' gia' passata: prenota() la rifiuterebbe, giustamente.
// Qui si simula una prenotazione fatta giorni fa, scrivendo le due righe che
// prenota() avrebbe scritto insieme.
$pdo->prepare('INSERT INTO prenotazioni (id, slot_id, cliente_id) VALUES (?,?,?)')
    ->execute(['p_oggi', 'oggi1', 'c1']);
$pdo->prepare('INSERT INTO movimenti (cliente_id, tipo, delta, causale, prenotazione_id, autore_id)
               VALUES (?,?,?,?,?,?)')
    ->execute(['c1', 'gruppo', -1, 'prenotazione', 'p_oggi', 'c1']);

echo "preparato\n";
