<?php
declare(strict_types=1);
/** Database e dati di prova per test/schermate.sh */

foreach (['Config', 'Db', 'Posta', 'Regole'] as $c) { require __DIR__ . "/../src/$c.php"; }
require __DIR__ . '/comune.php';

use Studio\Db;
use Studio\Regole;

$pdo = preparaDatabase();
Db::usa($pdo);

$pdo->exec("INSERT INTO utenti (id, email, nome, ruolo) VALUES
  ('a1', 'admin@studio.test', 'Admin', 'admin'),
  ('c1', 'anna@test.it',      'Anna',  'cliente'),
  ('c2', 'bruno@test.it',     'Bruno', 'cliente')");

// Una lezione di gruppo alle 18:00 ora italiana, fra tre giorni.
$fuso   = new DateTimeZone('Europe/Rome');
$quando = (new DateTimeImmutable('+3 days', $fuso))->setTime(18, 0);
$utc    = fn(DateTimeImmutable $d) => $d->setTimezone(new DateTimeZone('UTC'))->format('Y-m-d H:i:s');

$pdo->prepare('INSERT INTO slot (id, inizio, fine, tipo, capienza) VALUES (?,?,?,?,?)')
    ->execute(['sg', $utc($quando), $utc($quando->modify('+60 minutes')), 'gruppo', 4]);

$pdo->prepare('INSERT INTO slot (id, inizio, fine, tipo, capienza) VALUES (?,?,?,?,?)')
    ->execute(['si', $utc($quando->modify('+1 day')),
                     $utc($quando->modify('+1 day +60 minutes')), 'individuale', 1]);

Regole::accredita('c1', 'gruppo', 10, 'a1', 250.00, 'Pacchetto 10 gruppo');
Regole::accredita('c1', 'individuale', 3, 'a1', 150.00, 'Pacchetto 3 individuali');
Regole::accredita('c2', 'gruppo', 5, 'a1', 130.00, 'Pacchetto Bruno');

// Una prenotazione di Bruno: serve a verificare che Anna non la veda.
Regole::prenota('sg', 'c2', 'a1');

echo "preparato\n";
