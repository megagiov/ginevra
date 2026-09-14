<?php
declare(strict_types=1);

/**
 * Verifica dell'accesso senza password.
 *
 * Ricrea il database a ogni esecuzione: non puntare mai DB_NAME a un
 * database vero.
 *
 * Uso:  php app/test/accesso.php
 */

foreach (['Config', 'Db', 'Posta', 'Regole', 'Accesso'] as $classe) {
    require __DIR__ . "/../src/$classe.php";
}

use Studio\Accesso;
use Studio\Config;
use Studio\Db;
use Studio\Posta;

require __DIR__ . '/comune.php';

$pdo = preparaDatabase();
Db::usa($pdo);
Config::imposta(['base_url' => 'https://studio.esempio.it', 'smtp_host' => '']);

$pdo->exec("INSERT INTO utenti (id, email, nome, ruolo) VALUES
  ('a1', 'admin@studio.test', 'Admin', 'admin'),
  ('c1', 'anna@test.it',      'Anna',  'cliente'),
  ('c2', 'bruno@test.it',     'Bruno', 'cliente')");

$pdo->exec("INSERT INTO utenti (id, email, nome, attivo) VALUES
  ('c9', 'uscita@test.it', 'Ex cliente', 0)");

$pdo->exec("INSERT INTO utenti (id, email, nome) VALUES
  ('c8', 'carla@test.it', 'Carla')");

// ---------------------------------------------------------------------------
// 1. Richiesta del link
// ---------------------------------------------------------------------------

Posta::$inviateInProva = [];
$token = Accesso::richiediLink('anna@test.it', '203.0.113.10');

ok('Un cliente noto riceve un token', is_string($token) && strlen($token) === 64);
ok('Ed e\' partita una sola email, al suo indirizzo',
   count(Posta::$inviateInProva) === 1 && Posta::$inviateInProva[0]['a'] === 'anna@test.it');

ok('L\'email contiene il link con il token',
   str_contains(Posta::$inviateInProva[0]['testo'], "https://studio.esempio.it/entra?token=$token"));

$q = $pdo->query("SELECT hash_codice FROM codici_accesso");
$salvato = $q->fetchColumn();
ok('Nel database c\'e\' l\'impronta, non il token in chiaro',
   $salvato === hash('sha256', $token) && !str_contains((string) $salvato, $token));

Posta::$inviateInProva = [];
ok('Un\'email sconosciuta non produce token', Accesso::richiediLink('nessuno@test.it') === null);
ok('E non fa partire nessuna email', count(Posta::$inviateInProva) === 0);

ok('Un cliente disattivato non puo\' piu\' entrare',
   Accesso::richiediLink('uscita@test.it') === null);

ok('L\'email non e\' sensibile alle maiuscole',
   is_string(Accesso::richiediLink('  ANNA@Test.it  ')));

// Un tetto alle richieste: l'indirizzo di un cliente non deve poter essere
// sommerso di email da chiunque conosca la pagina di accesso.
$bloccato = false;
for ($i = 0; $i < 10; $i++) {
    if (Accesso::richiediLink('bruno@test.it') === null) { $bloccato = true; break; }
}
ok('Dopo 5 richieste in un\'ora le successive vengono rifiutate', $bloccato);

// ---------------------------------------------------------------------------
// 2. Uso del link
// ---------------------------------------------------------------------------

// La verifica non consuma nulla: e' la pagina che uno scanner di posta
// apre da solo prima che il cliente clicchi davvero. Ripeterla non deve
// bruciare il codice.
ok('Il link e\' valido prima di essere usato', Accesso::tokenValido($token));
ok('Controllarlo piu\' volte non lo consuma', Accesso::tokenValido($token));

$sessione = Accesso::entra($token, 'Mozilla/5.0 Prova');
ok('Il token apre la sessione', is_string($sessione) && strlen($sessione) === 64);

ok('Dopo l\'uso non e\' piu\' valido', !Accesso::tokenValido($token));

$utente = Accesso::utenteDaSessione($sessione);
ok('La sessione identifica il cliente giusto', ($utente['email'] ?? null) === 'anna@test.it');

ok('Lo stesso link non vale una seconda volta', Accesso::entra($token) === null);

ok('Un token inventato non apre nulla', Accesso::entra(bin2hex(random_bytes(32))) === null);
ok('Un token inventato non risulta valido', !Accesso::tokenValido(bin2hex(random_bytes(32))));

$s = $pdo->query("SELECT id FROM sessioni")->fetchColumn();
ok('Anche della sessione si salva solo l\'impronta', $s === hash('sha256', $sessione));

ok('L\'accesso aggiorna la data di ultimo ingresso',
   $pdo->query("SELECT ultimo_accesso_il FROM utenti WHERE id = 'c1'")->fetchColumn() !== null);

// ---------------------------------------------------------------------------
// 2b. Lo scenario reale: uno scanner di posta apre il link da solo
// ---------------------------------------------------------------------------

$tGmail = Accesso::richiediLink('carla@test.it');

// Gmail (o un antivirus) apre il link piu' volte per controllarlo, di
// solito nei secondi dopo la consegna, ben prima che l'utente lo clicchi.
Accesso::tokenValido($tGmail);
Accesso::tokenValido($tGmail);
Accesso::tokenValido($tGmail);

ok('Dopo le aperture automatiche dello scanner il link e\' ancora valido',
   Accesso::tokenValido($tGmail));

$sessioneVera = Accesso::entra($tGmail, 'Mozilla/5.0 Cliente vero');
ok('Il cliente vero riesce comunque a entrare', is_string($sessioneVera));

// ---------------------------------------------------------------------------
// 3. Scadenze
// ---------------------------------------------------------------------------

$scaduto = Accesso::richiediLink('admin@studio.test');
$pdo->prepare('UPDATE codici_accesso SET scade_il = UTC_TIMESTAMP() - INTERVAL 1 MINUTE
                WHERE hash_codice = ?')->execute([hash('sha256', $scaduto)]);

ok('Un link scaduto non apre la sessione', Accesso::entra($scaduto) === null);

$pdo->prepare("UPDATE sessioni SET scade_il = UTC_TIMESTAMP() - INTERVAL 1 DAY WHERE id = ?")
    ->execute([hash('sha256', $sessione)]);
ok('Una sessione scaduta non identifica piu\' nessuno',
   Accesso::utenteDaSessione($sessione) === null);

// ---------------------------------------------------------------------------
// 4. Uscita e pulizia
// ---------------------------------------------------------------------------

$t2 = Accesso::richiediLink('anna@test.it');
$s2 = Accesso::entra($t2);
ok('Nuovo accesso riuscito', is_string($s2));

Accesso::esci($s2);
ok('Dopo l\'uscita la sessione non vale piu\'', Accesso::utenteDaSessione($s2) === null);

$pdo->exec("UPDATE codici_accesso SET scade_il = UTC_TIMESTAMP() - INTERVAL 30 DAY");
Accesso::pulisci();
ok('La pulizia rimuove codici vecchi e sessioni scadute',
   (int) $pdo->query("SELECT COUNT(*) FROM codici_accesso")->fetchColumn() === 0);

// ---------------------------------------------------------------------------
// 5. Un cliente disattivato dopo l'accesso perde la sessione
// ---------------------------------------------------------------------------

$t3 = Accesso::richiediLink('anna@test.it');
$s3 = Accesso::entra($t3);
$pdo->exec("UPDATE utenti SET attivo = 0 WHERE id = 'c1'");

ok('Disattivare un cliente invalida subito le sue sessioni',
   Accesso::utenteDaSessione($s3) === null);

esito();
