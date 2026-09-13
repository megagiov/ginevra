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
            error_log("SMTP non raggiungibile: $errstr ($errno)");
            return false;
        }
        stream_set_timeout($socket, 15);

        $mittente = self::soloIndirizzo($cfg['smtp_mittente']);

        try {
            self::attendi($socket, '220');
            self::comanda($socket, 'EHLO ' . (parse_url($cfg['base_url'], PHP_URL_HOST) ?: 'localhost'), '250');

            // Sulla 587 la connessione parte in chiaro e va promossa a TLS.
            if ($porta === 587) {
                self::comanda($socket, 'STARTTLS', '220');
                if (!stream_socket_enable_crypto($socket, true, STREAM_CRYPTO_METHOD_TLS_CLIENT)) {
                    throw new \RuntimeException('STARTTLS fallito');
                }
                self::comanda($socket, 'EHLO ' . (parse_url($cfg['base_url'], PHP_URL_HOST) ?: 'localhost'), '250');
            }

            self::comanda($socket, 'AUTH LOGIN', '334');
            self::comanda($socket, base64_encode((string) $cfg['smtp_user']), '334');
            self::comanda($socket, base64_encode((string) $cfg['smtp_password']), '235');

            self::comanda($socket, "MAIL FROM:<$mittente>", '250');
            self::comanda($socket, "RCPT TO:<$destinatario>", '250');
            self::comanda($socket, 'DATA', '354');

            // Un punto a inizio riga chiuderebbe il messaggio in anticipo.
            fwrite($socket, preg_replace('/^\./m', '..', $messaggio) . "\r\n.\r\n");
            self::attendi($socket, '250');

            self::comanda($socket, 'QUIT', '221');
        } catch (\Throwable $e) {
            error_log('Invio email fallito: ' . $e->getMessage());
            fclose($socket);
            return false;
        }

        fclose($socket);
        return true;
    }

    private static function comanda($socket, string $comando, string $atteso): void
    {
        fwrite($socket, $comando . "\r\n");
        self::attendi($socket, $atteso);
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
