<?php
declare(strict_types=1);

/**
 * Punto d'ingresso unico. Tutte le richieste passano di qui: l'.htaccess
 * accanto a questo file le reindirizza tutte, cosi' gli indirizzi restano
 * puliti e non c'e' un file PHP per pagina da proteggere uno per uno.
 */

foreach (['Config', 'Db', 'Posta', 'Regole', 'Accesso', 'Vista', 'Calendario'] as $classe) {
    require __DIR__ . "/src/$classe.php";
}

use Studio\Accesso;
use Studio\Calendario;
use Studio\Config;
use Studio\Regole;
use Studio\RegolaViolata;
use Studio\Vista;

// Gli errori non si mostrano mai al visitatore: rivelerebbero percorsi,
// query e credenziali. Finiscono nel log dell'hosting.
ini_set('display_errors', '0');
ini_set('log_errors', '1');
error_reporting(E_ALL);

header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');
header('Referrer-Policy: same-origin');

$percorso = '/' . trim(parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/', '/');
$metodo   = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$utente   = Accesso::corrente();

/** Redirect con messaggio, per non ripresentare un POST al ricaricamento. */
function vaiA(string $dove, ?string $esito = null, ?string $errore = null): never
{
    $q = [];
    if ($esito  !== null) { $q['esito']  = $esito; }
    if ($errore !== null) { $q['errore'] = $errore; }

    header('Location: ' . $dove . ($q ? '?' . http_build_query($q) : ''), true, 303);
    exit;
}

function richiediAccesso(?array $utente): array
{
    if ($utente === null) {
        header('Location: /accedi', true, 302);
        exit;
    }
    return $utente;
}

/** Ogni POST porta il gettone: senza, si rifiuta senza fare nulla. */
function verificaGettone(): void
{
    if (!Vista::gettoneValido($_POST['gettone'] ?? null)) {
        http_response_code(400);
        exit('Richiesta non valida. Torna indietro e riprova.');
    }
}

try {
    switch ("$metodo $percorso") {

        // ---------------------------------------------------------------
        // Accesso
        // ---------------------------------------------------------------

        case 'GET /accedi':
            if ($utente !== null) { vaiA('/'); }
            $inviata = isset($_GET['inviata']);
            require __DIR__ . '/pagine/accedi.php';
            break;

        case 'POST /accedi':
            $email = trim((string) ($_POST['email'] ?? ''));

            if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
                vaiA('/accedi', null, 'Controlla l\'indirizzo email.');
            }

            Accesso::richiediLink($email, $_SERVER['REMOTE_ADDR'] ?? null);

            // Si risponde allo stesso modo per un indirizzo noto e per uno
            // sconosciuto: la pagina non deve rivelare chi e' cliente.
            header('Location: /accedi?inviata=1', true, 303);
            exit;

        case 'GET /entra':
            $token = (string) ($_GET['token'] ?? '');
            $sessione = $token !== ''
                ? Accesso::entra($token, $_SERVER['HTTP_USER_AGENT'] ?? null)
                : null;

            if ($sessione === null) {
                vaiA('/accedi', null, 'Link scaduto o gia\' usato. Chiedine un altro.');
            }

            Accesso::apriCookie($sessione);
            vaiA('/');

        case 'POST /esci':
            verificaGettone();
            Accesso::chiudiCookie();
            vaiA('/accedi');

        // ---------------------------------------------------------------
        // Prenota
        // ---------------------------------------------------------------

        case 'GET /':
            $utente  = richiediAccesso($utente);
            $giorni  = Calendario::disponibilita($utente['id']);
            $saldi   = Calendario::saldi($utente['id']);
            require __DIR__ . '/pagine/prenota.php';
            break;

        case 'POST /prenota':
            $utente = richiediAccesso($utente);
            verificaGettone();

            try {
                Regole::prenota((string) ($_POST['slot'] ?? ''), $utente['id'], $utente['id']);
                vaiA('/prenotazioni', 'Prenotazione confermata.');
            } catch (RegolaViolata $e) {
                vaiA('/', null, $e->getMessage());
            }

        // ---------------------------------------------------------------
        // Le mie prenotazioni
        // ---------------------------------------------------------------

        case 'GET /prenotazioni':
            $utente   = richiediAccesso($utente);
            $prossime = Calendario::prossime($utente['id']);
            $passate  = Calendario::passate($utente['id']);
            require __DIR__ . '/pagine/prenotazioni.php';
            break;

        case 'POST /disdici':
            $utente = richiediAccesso($utente);
            verificaGettone();

            try {
                $restituito = Regole::disdici((string) ($_POST['prenotazione'] ?? ''), $utente['id']);
                vaiA('/prenotazioni', $restituito
                    ? 'Disdetta registrata: la lezione torna sul tuo saldo.'
                    : 'Disdetta registrata. Essendo fuori dai termini, la lezione e\' stata scalata.');
            } catch (RegolaViolata $e) {
                vaiA('/prenotazioni', null, $e->getMessage());
            }

        // ---------------------------------------------------------------
        // Saldo
        // ---------------------------------------------------------------

        case 'GET /saldo':
            $utente    = richiediAccesso($utente);
            $saldi     = Calendario::saldi($utente['id']);
            $movimenti = Calendario::movimenti($utente['id']);
            require __DIR__ . '/pagine/saldo.php';
            break;

        default:
            http_response_code(404);
            echo Vista::intestazione('Pagina non trovata', $utente);
            echo '<p class="vuoto">Questa pagina non esiste. '
               . '<a href="/">Torna alle prenotazioni</a>.</p>';
            echo Vista::chiusura();
    }
} catch (Throwable $e) {
    error_log('Errore non gestito: ' . $e->getMessage() . ' in '
              . $e->getFile() . ':' . $e->getLine());
    http_response_code(500);
    echo Vista::intestazione('Errore', null);
    echo '<p class="avviso errore" role="alert">Si e\' verificato un problema. '
       . 'Riprova fra poco.</p>';
    echo Vista::chiusura();
}
