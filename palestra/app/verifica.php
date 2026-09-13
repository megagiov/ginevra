<?php
declare(strict_types=1);

/**
 * Diagnostica dell'installazione.
 *
 * Si carica sul server, si apre nel browser, si legge, e POI SI CANCELLA.
 * Serve a trasformare un "non funziona" in una risposta precisa.
 *
 * Non stampa mai password ne' altri valori riservati: solo se una cosa
 * funziona o no. Resta comunque un file da rimuovere appena finito, perche'
 * rivela quali componenti sono installati.
 */

header('Content-Type: text/html; charset=utf-8');

$esiti = [];

// Sottocartella in cui gira l'app, per mostrare i link giusti.
$cartella = str_replace('\\', '/', dirname((string) ($_SERVER['SCRIPT_NAME'] ?? '/')));
$base = ($cartella === '/' || $cartella === '.') ? '' : rtrim($cartella, '/');

/** @param 'ok'|'errore'|'avviso' $stato */
function esito(string $cosa, string $stato, string $dettaglio = ''): void
{
    global $esiti;
    $esiti[] = compact('cosa', 'stato', 'dettaglio');
}

// ---------------------------------------------------------------------------
// 1. PHP
// ---------------------------------------------------------------------------

PHP_VERSION_ID >= 80100
    ? esito('Versione di PHP', 'ok', PHP_VERSION)
    : esito('Versione di PHP', 'errore', PHP_VERSION . ' — ne serve almeno la 8.1');

foreach (['pdo_mysql' => true, 'openssl' => true, 'mbstring' => true, 'gd' => false] as $ext => $necessaria) {
    if (extension_loaded($ext)) {
        esito("Estensione $ext", 'ok');
    } else {
        esito("Estensione $ext", $necessaria ? 'errore' : 'avviso',
              $necessaria ? 'indispensabile' : 'serve solo per rigenerare le icone');
    }
}

// ---------------------------------------------------------------------------
// 2. Connessione HTTPS e riscrittura degli indirizzi
// ---------------------------------------------------------------------------

$httpsAttivo = (($_SERVER['HTTPS'] ?? '') === 'on')
            || (($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https');

$httpsAttivo
    ? esito('HTTPS', 'ok', 'la PWA si potra\' installare sul telefono')
    : esito('HTTPS', 'errore', 'senza certificato la PWA non si installa ne\' su iPhone ne\' su Android');

if (function_exists('apache_get_modules')) {
    in_array('mod_rewrite', apache_get_modules(), true)
        ? esito('Riscrittura indirizzi (mod_rewrite)', 'ok')
        : esito('Riscrittura indirizzi (mod_rewrite)', 'errore', 'l\'.htaccess non puo\' funzionare');
} else {
    esito('Riscrittura indirizzi', 'avviso',
          "non verificabile da qui: provalo aprendo $base/accedi — se risponde, funziona");
}

// ---------------------------------------------------------------------------
// 3. Configurazione
// ---------------------------------------------------------------------------

$cfg = null;

if (!is_readable(__DIR__ . '/config.php')) {
    esito('File config.php', 'errore', 'manca: copialo da config.example.php e compilalo');
} else {
    $cfg = require __DIR__ . '/config.php';

    $mancanti = array_values(array_filter(
        ['db_host', 'db_name', 'db_user', 'db_password', 'session_secret', 'base_url'],
        fn(string $k): bool => empty($cfg[$k])
    ));

    $mancanti === []
        ? esito('File config.php', 'ok', 'tutti i valori compilati')
        : esito('File config.php', 'errore', 'valori mancanti: ' . implode(', ', $mancanti));

    if (($cfg['session_secret'] ?? '') !== '' && strlen((string) $cfg['session_secret']) < 32) {
        esito('Chiave di sessione', 'avviso', 'piu\' corta di 32 caratteri: generane una piu\' lunga');
    }
}

// ---------------------------------------------------------------------------
// 4. Database
// ---------------------------------------------------------------------------

$pdo = null;

if ($cfg !== null && !empty($cfg['db_host'])) {
    // Si mostra con quali dati si sta provando, cosi' un errore di
    // credenziali si riconosce subito. La password non si stampa mai: se ne
    // riporta solo la lunghezza, che basta a capire se e' quella giusta o se
    // e' rimasto il segnaposto.
    $pwd = (string) ($cfg['db_password'] ?? '');
    esito('Dati usati per la connessione', 'avviso', sprintf(
        'utente "%s" · host "%s" · database "%s" · password di %d caratteri',
        $cfg['db_user'], $cfg['db_host'], $cfg['db_name'], strlen($pwd)
    ));

    if (stripos($pwd, 'SCRIVI_QUI') !== false) {
        esito('Password del database', 'errore',
              'nel file c\'e\' ancora il segnaposto, non la password vera');
    }

    if ($pwd !== trim($pwd)) {
        esito('Password del database', 'errore',
              'comincia o finisce con uno spazio: toglilo');
    }

    try {
        $pdo = new PDO(
            sprintf('mysql:host=%s;dbname=%s;charset=utf8mb4', $cfg['db_host'], $cfg['db_name']),
            (string) $cfg['db_user'],
            $pwd,
            [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_TIMEOUT => 8]
        );
        $versione = (string) $pdo->query('SELECT VERSION()')->fetchColumn();
        esito('Connessione al database', 'ok', "MySQL $versione");
    } catch (PDOException $e) {
        // Il messaggio di MySQL non contiene mai la password, ma dice quale
        // utente e' stato rifiutato e se una password e' stata inviata:
        // e' esattamente cio' che serve per capire dove si sbaglia.
        $codice = (string) $e->getCode();

        $spiegazione = match ($codice) {
            '1045'  => 'utente o password rifiutati dal server',
            '1049'  => 'il database indicato non esiste: controlla il nome',
            '2002'  => 'il server non risponde: controlla l\'hostname',
            '2005'  => 'hostname sconosciuto',
            default => 'errore di connessione',
        };

        esito('Connessione al database', 'errore', "$spiegazione — " . $e->getMessage());

        if ($codice === '1045') {
            esito('Cosa fare', 'avviso',
                  'Reimposta la password dal pannello Aruba (Database → "Non ricordi '
                  . 'la password?"), attendi qualche minuto perche\' diventi attiva, '
                  . 'poi riscrivila nel file e ricaricalo.');
        }
    }
}

if ($pdo !== null) {
    $attese = ['utenti', 'slot', 'prenotazioni', 'movimenti', 'impostazioni',
               'codici_accesso', 'sessioni'];
    $presenti = $pdo->query('SHOW TABLES')->fetchAll(PDO::FETCH_COLUMN);
    $mancanti = array_values(array_diff($attese, $presenti));

    $mancanti === []
        ? esito('Tabelle', 'ok', count($attese) . ' tabelle presenti')
        : esito('Tabelle', 'errore', 'mancano: ' . implode(', ', $mancanti)
                . ' — importa 0001_schema.sql da phpMyAdmin');

    // La verifica che conta: MySQL 5.7 accetta i CHECK e poi li ignora in
    // silenzio. Qui si prova a inserire una lezione che finisce prima di
    // iniziare: il server DEVE rifiutarla.
    if ($mancanti === []) {
        try {
            $pdo->exec(
                "INSERT INTO slot (id, inizio, fine, tipo, capienza)
                 VALUES ('__verifica__', '2027-01-04 09:00:00', '2027-01-04 08:00:00', 'individuale', 1)"
            );
            $pdo->exec("DELETE FROM slot WHERE id = '__verifica__'");
            esito('Vincoli CHECK applicati', 'errore',
                  'il server li ha ignorati: meta\' delle garanzie non esiste. Avvisami.');
        } catch (PDOException) {
            esito('Vincoli CHECK applicati', 'ok', 'una lezione incoerente viene rifiutata');
        }

        $trigger = $pdo->query("SHOW TRIGGERS LIKE 'slot'")->fetchAll();
        count($trigger) >= 2
            ? esito('Trigger anti-sovrapposizione', 'ok', count($trigger) . ' attivi')
            : esito('Trigger anti-sovrapposizione', 'errore',
                    'assenti: due lezioni potrebbero sovrapporsi in sala. '
                    . 'Reimporta lo schema da phpMyAdmin, non da un client che scarta i DELIMITER.');

        $admin = (int) $pdo->query("SELECT COUNT(*) FROM utenti WHERE ruolo = 'admin'")->fetchColumn();
        $admin > 0
            ? esito('Utente amministratore', 'ok', "$admin presente/i")
            : esito('Utente amministratore', 'errore',
                    'nessuno: creane uno con la INSERT indicata nel README');
    }
}

// ---------------------------------------------------------------------------
// 5. Fuso orario
// ---------------------------------------------------------------------------

try {
    new DateTimeZone('Europe/Rome');
    esito('Fuso orario Europe/Rome', 'ok', 'ora locale: '
        . (new DateTimeImmutable('now', new DateTimeZone('Europe/Rome')))->format('d/m/Y H:i'));
} catch (Throwable) {
    esito('Fuso orario Europe/Rome', 'errore', 'database dei fusi orari non disponibile');
}

// ---------------------------------------------------------------------------
// 6. Posta (solo se richiesto: manda una email vera)
// ---------------------------------------------------------------------------

$provaPosta = isset($_GET['posta']) && $cfg !== null;

if ($provaPosta) {
    foreach (['Config', 'Posta'] as $classe) {
        require_once __DIR__ . "/src/$classe.php";
    }

    $a = (string) $_GET['posta'];

    if (!filter_var($a, FILTER_VALIDATE_EMAIL)) {
        esito('Invio email', 'errore', 'indirizzo non valido');
    } elseif (empty($cfg['smtp_host'])) {
        esito('Invio email', 'errore', 'SMTP non configurato in config.php');
    } else {
        Studio\Posta::invia($a, 'Prova di invio', '<p>Funziona.</p>', 'Funziona.')
            ? esito('Invio email', 'ok', "messaggio inviato a $a — controlla la posta, anche lo spam")
            : esito('Invio email', 'errore', 'invio fallito: controlla i dati SMTP nel log degli errori');
    }
}

$errori  = count(array_filter($esiti, fn(array $e): bool => $e['stato'] === 'errore'));
$avvisi  = count(array_filter($esiti, fn(array $e): bool => $e['stato'] === 'avviso'));
?>
<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Verifica installazione</title>
<style>
  body { font: 16px/1.5 system-ui, sans-serif; margin: 0; padding: 1.5rem;
         background: #F8FAFC; color: #0F172A; }
  main { max-width: 680px; margin: 0 auto; }
  h1 { font-size: 1.6rem; }
  ul { list-style: none; padding: 0; }
  li { display: flex; gap: .75rem; align-items: flex-start;
       padding: .7rem .9rem; margin-bottom: .4rem; background: #fff;
       border: 1px solid #E2E8F0; border-left: 4px solid; border-radius: 10px; }
  li.ok      { border-left-color: #059669; }
  li.errore  { border-left-color: #B91C1C; }
  li.avviso  { border-left-color: #D97706; }
  .simbolo { font-weight: 700; min-width: 1.3rem; }
  li.ok .simbolo     { color: #059669; }
  li.errore .simbolo { color: #B91C1C; }
  li.avviso .simbolo { color: #D97706; }
  .dettaglio { display: block; color: #475569; font-size: .9rem; }
  .cartello { padding: 1rem; border-radius: 10px; margin-bottom: 1.2rem; font-weight: 600; }
  .bene { background: #ECFDF5; color: #065F46; }
  .male { background: #FEF2F2; color: #991B1B; }
  .nota { background: #FFFBEB; color: #92400E; padding: 1rem; border-radius: 10px;
          margin-top: 2rem; font-size: .92rem; }
</style>
</head>
<body>
<main>
  <h1>Verifica installazione</h1>

  <?php if ($errori === 0): ?>
    <p class="cartello bene">
      Tutto a posto<?= $avvisi > 0 ? " ($avvisi avviso/i da leggere)" : '' ?>.
      Apri <a href="<?= htmlspecialchars($base, ENT_QUOTES) ?>/accedi">
      <?= htmlspecialchars($base, ENT_QUOTES) ?>/accedi</a> e prova a entrare.
    </p>
  <?php else: ?>
    <p class="cartello male"><?= $errori ?> problema/i da risolvere.</p>
  <?php endif; ?>

  <ul>
  <?php foreach ($esiti as $e): ?>
    <li class="<?= $e['stato'] ?>">
      <span class="simbolo"><?= ['ok' => '✓', 'errore' => '✕', 'avviso' => '!'][$e['stato']] ?></span>
      <span>
        <?= htmlspecialchars($e['cosa'], ENT_QUOTES, 'UTF-8') ?>
        <?php if ($e['dettaglio'] !== ''): ?>
          <span class="dettaglio"><?= htmlspecialchars($e['dettaglio'], ENT_QUOTES, 'UTF-8') ?></span>
        <?php endif; ?>
      </span>
    </li>
  <?php endforeach; ?>
  </ul>

  <?php if (!$provaPosta): ?>
    <p>Per provare anche l'invio delle email, aggiungi il tuo indirizzo
       all'indirizzo di questa pagina:
       <code>verifica.php?posta=tua@email.it</code></p>
  <?php endif; ?>

  <p class="nota">
    <strong>Cancella questo file dal server quando hai finito.</strong>
    Non mostra password, ma dice a chiunque lo apra quali componenti sono
    installati: e' un'informazione che non serve a nessuno tranne che a te,
    adesso.
  </p>
</main>
</body>
</html>
