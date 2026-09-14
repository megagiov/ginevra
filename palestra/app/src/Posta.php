<?php
declare(strict_types=1);

namespace Studio;

/**
 * Invio email via SMTP, senza librerie esterne.
 *
 * Su un hosting con solo FTP non si puo' installare Composer, quindi niente
 * PHPMailer: qui c'e' il minimo indispensabile per parlare con un server
 * SMTP autenticato.
 *
 * Non si usa la funzione mail() di PHP perche' su hosting condiviso i
 * messaggi partono da un IP promiscuo e finiscono nello spam. Autenticandosi
 * sulla casella del dominio, invece, arrivano in posta in arrivo.
 */
final class Posta
{
    /** @var list<array{a:string,oggetto:string,testo:string}> messaggi raccolti in modalita' prova */
    public static array $inviateInProva = [];

    /**
     * Motivo dell'ultimo invio fallito.
     *
     * Serve alla pagina di diagnostica: il solo "invio fallito" non basta a
     * capire se il server rifiuta le credenziali, se non risponde o se il
     * certificato non va. Il messaggio SMTP non contiene mai la password.
     */
    public static ?string $ultimoErrore = null;

    public static function invia(string $a, string $oggetto, string $testoHtml, string $testoSemplice): bool
    {
        $cfg = Config::tutto();

        // Senza SMTP configurato (sviluppo e test) non si manda nulla: il
        // messaggio si raccoglie in memoria e si scrive nel log.
        if (($cfg['smtp_host'] ?? '') === '') {
            self::$inviateInProva[] = ['a' => $a, 'oggetto' => $oggetto, 'testo' => $testoSemplice];
            error_log("[posta non inviata: SMTP non configurato] $a — $oggetto");
            return true;
        }

        $confine = 'confine_' . bin2hex(random_bytes(8));

        $intestazioni = [
            'From: ' . $cfg['smtp_mittente'],
            'To: ' . $a,
            'Subject: =?UTF-8?B?' . base64_encode($oggetto) . '?=',
            'MIME-Version: 1.0',
            'Content-Type: multipart/alternative; boundary="' . $confine . '"',
            'Date: ' . date('r'),
        ];

        $corpo = "--$confine\r\n"
               . "Content-Type: text/plain; charset=UTF-8\r\n"
               . "Content-Transfer-Encoding: base64\r\n\r\n"
               . chunk_split(base64_encode($testoSemplice)) . "\r\n"
               . "--$confine\r\n"
               . "Content-Type: text/html; charset=UTF-8\r\n"
               . "Content-Transfer-Encoding: base64\r\n\r\n"
               . chunk_split(base64_encode($testoHtml)) . "\r\n"
               . "--$confine--\r\n";

        return self::parla($cfg, $a, implode("\r\n", $intestazioni) . "\r\n\r\n" . $corpo);
    }

    private static function parla(array $cfg, string $destinatario, string $messaggio): bool
    {
        $porta = (int) ($cfg['smtp_port'] ?? 465);
        $host  = $porta === 465 ? 'ssl://' . $cfg['smtp_host'] : $cfg['smtp_host'];

        $socket = @fsockopen($host, $porta, $errno, $errstr, 15);
        if (!$socket) {
            self::$ultimoErrore = "server non raggiungibile su $host:$porta — $errstr ($errno)";
            error_log('SMTP: ' . self::$ultimoErrore);
            return false;
        }
        stream_set_timeout($socket, 15);

        $mittente = self::soloIndirizzo($cfg['smtp_mittente']);

        try {
            self::attendi($socket, '220');
            $saluto = 'EHLO ' . (parse_url($cfg['base_url'], PHP_URL_HOST) ?: 'localhost');
            self::comanda($socket, $saluto, '250', 'saluto iniziale (EHLO)');

            // Sulla 587 la connessione parte in chiaro e va promossa a TLS.
            if ($porta === 587) {
                self::comanda($socket, 'STARTTLS', '220', 'avvio della cifratura (STARTTLS)');
                if (!stream_socket_enable_crypto($socket, true, STREAM_CRYPTO_METHOD_TLS_CLIENT)) {
                    throw new \RuntimeException('cifratura STARTTLS non riuscita');
                }
                self::comanda($socket, $saluto, '250', 'saluto dopo la cifratura');
            }

            self::comanda($socket, 'AUTH LOGIN', '334', 'richiesta di autenticazione');
            self::comanda($socket, base64_encode((string) $cfg['smtp_user']), '334',
                          'utente rifiutato');
            self::comanda($socket, base64_encode((string) $cfg['smtp_password']), '235',
                          'password rifiutata');

            self::comanda($socket, "MAIL FROM:<$mittente>", '250', 'indirizzo mittente rifiutato');
            self::comanda($socket, "RCPT TO:<$destinatario>", '250', 'indirizzo destinatario rifiutato');
            self::comanda($socket, 'DATA', '354', 'invio del messaggio');

            // Un punto a inizio riga chiuderebbe il messaggio in anticipo.
            fwrite($socket, preg_replace('/^\./m', '..', $messaggio) . "\r\n.\r\n");
            self::attendi($socket, '250');

            self::comanda($socket, 'QUIT', '221', 'chiusura');
        } catch (\Throwable $e) {
            self::$ultimoErrore = $e->getMessage();
            error_log('Invio email fallito: ' . self::$ultimoErrore);
            fclose($socket);
            return false;
        }

        fclose($socket);
        return true;
    }

    /**
     * Manda un comando e verifica la risposta.
     *
     * L'etichetta e' quella che comparira' nell'errore, e va passata sempre
     * a mano: ricavarla dal comando significherebbe stampare le righe
     * dell'AUTH, che contengono utenza e password in base64 — cioe' in
     * chiaro, per chiunque sappia decodificarle.
     */
    private static function comanda($socket, string $comando, string $atteso, string $etichetta): void
    {
        fwrite($socket, $comando . "\r\n");

        try {
            self::attendi($socket, $atteso);
        } catch (\Throwable $e) {
            throw new \RuntimeException("$etichetta: " . $e->getMessage());
        }
    }

    private static function attendi($socket, string $atteso): void
    {
        $risposta = '';
        while (($riga = fgets($socket, 515)) !== false) {
            $risposta .= $riga;
            // Le risposte multiriga hanno un trattino dopo il codice.
            if (strlen($riga) < 4 || $riga[3] !== '-') {
                break;
            }
        }

        if (!str_starts_with($risposta, $atteso)) {
            throw new \RuntimeException("Atteso $atteso, ricevuto: " . trim($risposta));
        }
    }

    private static function soloIndirizzo(string $mittente): string
    {
        return preg_match('/<([^>]+)>/', $mittente, $m) ? $m[1] : trim($mittente);
    }
}
