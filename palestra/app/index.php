<?php
declare(strict_types=1);

/**
 * Punto d'ingresso unico. Tutte le richieste passano di qui: l'.htaccess
 * accanto a questo file le reindirizza tutte, cosi' gli indirizzi restano
 * puliti e non c'e' un file PHP per pagina da proteggere uno per uno.
 */

foreach (['Config', 'Db', 'Posta', 'Regole', 'Accesso', 'Vista', 'Calendario',
          'Amministrazione'] as $classe) {
    require __DIR__ . "/src/$classe.php";
}

use Studio\Accesso;
use Studio\Amministrazione;
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

// L'indirizzo richiesto puo' contenere la sottocartella in cui l'app e'
// installata: la si toglie qui, una volta, cosi' le rotte restano scritte
// come se l'app fosse alla radice.
$richiesto = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
$prefisso  = Vista::base();

if ($prefisso !== '' && str_starts_with($richiesto, $prefisso)) {
    $richiesto = substr($richiesto, strlen($prefisso));
}

$percorso = '/' . trim($richiesto, '/');
$metodo   = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$utente   = Accesso::corrente();

/** Redirect con messaggio, per non ripresentare un POST al ricaricamento. */
function vaiA(string $dove, ?string $esito = null, ?string $errore = null): never
{
    $q = [];
    if ($esito  !== null) { $q['esito']  = $esito; }
    if ($errore !== null) { $q['errore'] = $errore; }

    header('Location: ' . Vista::u($dove) . ($q ? '?' . http_build_query($q) : ''), true, 303);
    exit;
}

function esigiAdmin(?array $utente): array
{
    $utente = richiediAccesso($utente);

    if ($utente['ruolo'] !== 'admin') {
        http_response_code(403);
        exit('Area riservata.');
    }
    return $utente;
}

/** Giorno locale richiesto dall'URL, oggi se assente o malformato. */
function giornoRichiesto(?string $valore): DateTimeImmutable
{
    $fuso = new DateTimeZone((string) Studio\Config::v('fuso'));

    if ($valore !== null && $valore !== '') {
        $d = DateTimeImmutable::createFromFormat('Y-m-d', $valore, $fuso);
        if ($d !== false) {
            return $d->setTime(0, 0);
        }
    }
    return new DateTimeImmutable('today', $fuso);
}

function lunediRichiesto(?string $valore): DateTimeImmutable
{
    return giornoRichiesto($valore)->modify('monday this week');
}

function richiediAccesso(?array $utente): array
{
    if ($utente === null) {
        header('Location: ' . Vista::u('/accedi'), true, 302);
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
            header('Location: ' . Vista::u('/accedi?inviata=1'), true, 303);
            exit;

        // Il link nell'email non accede da solo: mostra una pagina che
        // aspetta un tocco vero sul pulsante "Entra". Nessun invio
        // automatico via JavaScript: alcuni controlli antiphishing aprono
        // il link ed eseguono anche lo script della pagina, quindi un invio
        // automatico verrebbe consumato da loro allo stesso modo di un GET
        // semplice. Solo un tocco reale del cliente apre la sessione.
        case 'GET /entra':
            $token = (string) ($_GET['token'] ?? '');

            if ($token === '' || !Accesso::tokenValido($token)) {
                vaiA('/accedi', null, 'Link scaduto o gia\' usato. Chiedine un altro.');
            }

            require __DIR__ . '/pagine/entra.php';
            break;

        case 'POST /entra':
            $token = (string) ($_POST['token'] ?? '');
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
            $utente = richiediAccesso($utente);

            if ($utente['ruolo'] === 'admin') {
                header('Location: ' . Vista::u('/admin'), true, 302);
                exit;
            }

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

        // ---------------------------------------------------------------
        // Amministrazione
        // ---------------------------------------------------------------

        case 'GET /admin':
            $utente    = esigiAdmin($utente);
            $giorno    = giornoRichiesto($_GET['giorno'] ?? null);
            $agenda    = Amministrazione::agenda($utente['id'], $giorno);
            $riepilogo = Amministrazione::riepilogo($utente['id'], $giorno);
            require __DIR__ . '/pagine/admin-oggi.php';
            break;

        case 'POST /admin/presenza':
            $utente = esigiAdmin($utente);
            verificaGettone();
            $ritorno = '/admin?giorno=' . urlencode((string) ($_POST['giorno'] ?? ''));

            try {
                Regole::segnaPresenza(
                    (string) ($_POST['prenotazione'] ?? ''),
                    ($_POST['presente'] ?? '') === '1',
                    $utente['id']
                );
                vaiA($ritorno, 'Presenza registrata.');
            } catch (RegolaViolata $e) {
                vaiA($ritorno, null, $e->getMessage());
            }

        case 'GET /admin/calendario':
            $utente    = esigiAdmin($utente);
            $lunedi    = lunediRichiesto($_GET['da'] ?? null);
            $settimana = Amministrazione::settimana($utente['id'], $lunedi);
            require __DIR__ . '/pagine/admin-calendario.php';
            break;

        case 'POST /admin/slot':
            $utente = esigiAdmin($utente);
            verificaGettone();
            $ritorno = '/admin/calendario?da=' . urlencode((string) ($_POST['da'] ?? ''));

            try {
                $esito = Amministrazione::creaSlot(
                    $utente['id'],
                    (string) ($_POST['data'] ?? ''),
                    (string) ($_POST['ora'] ?? ''),
                    (string) ($_POST['tipo'] ?? ''),
                    (int) ($_POST['capienza'] ?? 4),
                    (int) ($_POST['ripetizioni'] ?? 1)
                );

                $messaggio = $esito['creati'] === 1
                    ? 'Lezione pubblicata.'
                    : $esito['creati'] . ' lezioni pubblicate.';

                if ($esito['saltati'] !== []) {
                    $messaggio .= ' Saltate perche\' la sala era gia\' occupata: '
                                . implode('; ', $esito['saltati']) . '.';
                }

                $esito['creati'] > 0
                    ? vaiA($ritorno, $messaggio)
                    : vaiA($ritorno, null, 'Nessuna lezione pubblicata. ' . $messaggio);
            } catch (RegolaViolata $e) {
                vaiA($ritorno, null, $e->getMessage());
            }

        case 'POST /admin/slot/stato':
            $utente = esigiAdmin($utente);
            verificaGettone();
            $ritorno = '/admin/calendario?da=' . urlencode((string) ($_POST['da'] ?? ''));

            try {
                $stato = (string) ($_POST['stato'] ?? '');
                Amministrazione::cambiaStatoSlot($utente['id'], (string) ($_POST['slot'] ?? ''), $stato);
                vaiA($ritorno, $stato === 'chiuso'
                    ? 'Lezione chiusa alle prenotazioni.'
                    : 'Lezione riaperta.');
            } catch (RegolaViolata $e) {
                vaiA($ritorno, null, $e->getMessage());
            }

        case 'POST /admin/slot/elimina':
            $utente = esigiAdmin($utente);
            verificaGettone();
            $ritorno = '/admin/calendario?da=' . urlencode((string) ($_POST['da'] ?? ''));

            try {
                Amministrazione::eliminaSlot($utente['id'], (string) ($_POST['slot'] ?? ''));
                vaiA($ritorno, 'Lezione eliminata.');
            } catch (RegolaViolata $e) {
                vaiA($ritorno, null, $e->getMessage());
            }

        case 'GET /admin/clienti':
            $utente  = esigiAdmin($utente);
            $elenco  = Amministrazione::clienti($utente['id'], isset($_GET['tutti']));
            require __DIR__ . '/pagine/admin-clienti.php';
            break;

        case 'POST /admin/clienti':
            $utente = esigiAdmin($utente);
            verificaGettone();

            try {
                $id = Amministrazione::creaCliente(
                    $utente['id'],
                    (string) ($_POST['nome'] ?? ''),
                    (string) ($_POST['email'] ?? ''),
                    (string) ($_POST['telefono'] ?? ''),
                    (string) ($_POST['note'] ?? '')
                );
                vaiA('/admin/cliente?id=' . urlencode($id), 'Cliente creato.');
            } catch (RegolaViolata $e) {
                vaiA('/admin/clienti', null, $e->getMessage());
            }

        case 'GET /admin/cliente':
            $utente  = esigiAdmin($utente);
            $scheda  = Amministrazione::cliente($utente['id'], (string) ($_GET['id'] ?? ''));

            if ($scheda === null) {
                vaiA('/admin/clienti', null, 'Cliente inesistente.');
            }

            $prenotabili = Calendario::disponibilita($scheda['anagrafica']['id']);
            require __DIR__ . '/pagine/admin-cliente.php';
            break;

        case 'POST /admin/accredita':
            $utente  = esigiAdmin($utente);
            verificaGettone();
            $cliente = (string) ($_POST['cliente'] ?? '');
            $ritorno = '/admin/cliente?id=' . urlencode($cliente);

            try {
                $quantita = (int) ($_POST['quantita'] ?? 0);
                $causale  = (string) ($_POST['causale'] ?? 'acquisto');
                $importo  = ($_POST['importo'] ?? '') !== '' ? (float) $_POST['importo'] : null;

                Regole::accredita(
                    $cliente,
                    (string) ($_POST['tipo'] ?? 'individuale'),
                    $quantita,
                    $utente['id'],
                    $importo,
                    (string) ($_POST['nota'] ?? '') ?: null,
                    $causale
                );
                vaiA($ritorno, 'Movimento registrato.');
            } catch (RegolaViolata $e) {
                vaiA($ritorno, null, $e->getMessage());
            }

        case 'POST /admin/prenota':
            $utente  = esigiAdmin($utente);
            verificaGettone();
            $cliente = (string) ($_POST['cliente'] ?? '');
            $ritorno = '/admin/cliente?id=' . urlencode($cliente);

            try {
                Regole::prenota((string) ($_POST['slot'] ?? ''), $cliente, $utente['id']);
                vaiA($ritorno, 'Prenotazione registrata per il cliente.');
            } catch (RegolaViolata $e) {
                vaiA($ritorno, null, $e->getMessage());
            }

        case 'POST /admin/cliente/attivazione':
            $utente  = esigiAdmin($utente);
            verificaGettone();
            $cliente = (string) ($_POST['cliente'] ?? '');

            try {
                $attivo = ($_POST['attivo'] ?? '') === '1';
                Amministrazione::cambiaAttivazione($utente['id'], $cliente, $attivo);
                vaiA('/admin/cliente?id=' . urlencode($cliente),
                     $attivo ? 'Cliente riattivato.' : 'Cliente disattivato.');
            } catch (RegolaViolata $e) {
                vaiA('/admin/cliente?id=' . urlencode($cliente), null, $e->getMessage());
            }

        default:
            http_response_code(404);
            echo Vista::intestazione('Pagina non trovata', $utente);
            echo '<p class="vuoto">Questa pagina non esiste. '
               . '<a href="' . Vista::u('/') . '">Torna alle prenotazioni</a>.</p>';
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
