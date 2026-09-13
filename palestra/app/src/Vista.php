<?php
declare(strict_types=1);

namespace Studio;

/**
 * Presentazione: scampo dell'HTML, formato delle date in italiano, guscio
 * della pagina e gettone anti-CSRF.
 *
 * Nel database gli orari sono UTC. Qui e solo qui diventano ora italiana.
 */
final class Vista
{
    private const GIORNI = ['domenica','lunedì','martedì','mercoledì','giovedì','venerdì','sabato'];
    private const MESI   = ['','gennaio','febbraio','marzo','aprile','maggio','giugno',
                            'luglio','agosto','settembre','ottobre','novembre','dicembre'];

    public static function e(?string $testo): string
    {
        return htmlspecialchars((string) $testo, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    }

    public static function locale(string $utc): \DateTimeImmutable
    {
        return (new \DateTimeImmutable($utc, new \DateTimeZone('UTC')))
            ->setTimezone(new \DateTimeZone((string) Config::v('fuso')));
    }

    /** "giovedi 19 marzo" */
    public static function giorno(\DateTimeImmutable $d): string
    {
        return self::GIORNI[(int) $d->format('w')] . ' ' . (int) $d->format('j')
             . ' ' . self::MESI[(int) $d->format('n')];
    }

    public static function ora(\DateTimeImmutable $d): string
    {
        return $d->format('H:i');
    }

    /** "oggi", "domani", altrimenti il giorno per esteso. */
    public static function giornoRelativo(\DateTimeImmutable $d): string
    {
        $fuso  = new \DateTimeZone((string) Config::v('fuso'));
        $oggi  = new \DateTimeImmutable('today', $fuso);
        $delta = (int) $oggi->diff($d->setTime(0, 0))->format('%r%a');

        return match ($delta) {
            0       => 'oggi',
            1       => 'domani',
            default => self::giorno($d),
        };
    }

    // ------------------------------------------------------------------
    // Gettone anti-CSRF
    //
    // Il cookie e' SameSite=Lax, che gia' blocca quasi tutte le richieste
    // ostili da altri siti. Questo e' il secondo giro di chiave: senza, un
    // link malevolo potrebbe far disdire una lezione al posto del cliente.
    // ------------------------------------------------------------------

    public static function gettone(): string
    {
        $sessione = $_COOKIE[Accesso::nomeCookie()] ?? '';
        return hash_hmac('sha256', 'modulo', (string) Config::v('session_secret') . $sessione);
    }

    public static function gettoneValido(?string $ricevuto): bool
    {
        return is_string($ricevuto) && hash_equals(self::gettone(), $ricevuto);
    }

    public static function campoGettone(): string
    {
        return '<input type="hidden" name="gettone" value="' . self::e(self::gettone()) . '">';
    }

    // ------------------------------------------------------------------
    // Guscio della pagina
    // ------------------------------------------------------------------

    public static function intestazione(string $titolo, ?array $utente = null, ?string $attiva = null): string
    {
        $studio = self::e((string) Config::v('nome_studio'));
        $t = self::e($titolo);

        $nav = '';
        if ($utente !== null) {
            $voci = [
                '/'             => ['Prenota',     'prenota'],
                '/prenotazioni' => ['Le mie',      'prenotazioni'],
                '/saldo'        => ['Saldo',       'saldo'],
            ];

            $nav = '<nav class="barra" aria-label="Sezioni">';
            foreach ($voci as $href => [$etichetta, $chiave]) {
                $corrente = $chiave === $attiva;
                $nav .= sprintf(
                    '<a href="%s"%s>%s</a>',
                    $href,
                    $corrente ? ' class="attiva" aria-current="page"' : '',
                    self::e($etichetta)
                );
            }
            $nav .= '</nav>';
        }

        return <<<HTML
            <!doctype html>
            <html lang="it">
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
              <title>$t · $studio</title>
              <link rel="manifest" href="/manifest.json">
              <link rel="stylesheet" href="/stile.css">
              <meta name="theme-color" content="#0284C7">
              <link rel="apple-touch-icon" href="/icona-180.png">
            </head>
            <body>
              <header class="testata">
                <span class="marchio">$studio</span>
              </header>
              $nav
              <main>
            HTML;
    }

    public static function chiusura(): string
    {
        return <<<HTML
              </main>
              <script>
                if ('serviceWorker' in navigator) {
                  navigator.serviceWorker.register('/sw.js').catch(() => {});
                }
              </script>
            </body>
            </html>
            HTML;
    }

    /** Messaggio di esito, passato fra pagine con un parametro nell'URL. */
    public static function avviso(?string $tipo, ?string $testo): string
    {
        if ($testo === null || $testo === '') {
            return '';
        }

        $classe = $tipo === 'errore' ? 'avviso errore' : 'avviso esito';
        $ruolo  = $tipo === 'errore' ? 'alert' : 'status';

        return sprintf('<p class="%s" role="%s">%s</p>', $classe, $ruolo, self::e($testo));
    }
}
