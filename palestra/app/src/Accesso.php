<?php
declare(strict_types=1);

namespace Studio;

/**
 * Accesso senza password.
 *
 * Il cliente scrive la sua email, riceve un link, entra. Non ci sono
 * password da ricordare, da reimpostare o da rubare, e chi fa assistenza
 * sei tu mentre stai allenando qualcuno: ogni password dimenticata sarebbe
 * una telefonata.
 *
 * Il link vale mezz'ora e una volta sola. La sessione dura tre mesi, cosi'
 * in pratica l'app si apre gia' sbloccata.
 */
final class Accesso
{
    private const VALIDITA_CODICE_MINUTI = 30;
    private const DURATA_SESSIONE_GIORNI = 90;
    private const MAX_RICHIESTE_ORA      = 5;
    private const COOKIE                 = 'studio_sessione';

    private static ?array $utente = null;

    // ------------------------------------------------------------------
    // Richiesta del link
    // ------------------------------------------------------------------

    /**
     * Genera e invia il link di accesso.
     *
     * Restituisce sempre true, anche per un'email sconosciuta: altrimenti la
     * pagina di accesso direbbe a chiunque quali indirizzi sono clienti dello
     * studio.
     *
     * @return string|null il token generato — solo per i test, in produzione
     *                     non viene mai mostrato
     */
    public static function richiediLink(string $email, ?string $ip = null): ?string
    {
        $email = mb_strtolower(trim($email));

        $q = Db::pdo()->prepare('SELECT id, nome, email FROM utenti WHERE email = ? AND attivo = 1');
        $q->execute([$email]);
        $utente = $q->fetch();

        if (!$utente) {
            return null;
        }

        // Un limite alle richieste: senza, l'indirizzo di un cliente puo'
        // essere sommerso di email da chiunque conosca la pagina.
        $q = Db::pdo()->prepare(
            'SELECT COUNT(*) FROM codici_accesso
              WHERE utente_id = ? AND creato_il > UTC_TIMESTAMP() - INTERVAL 1 HOUR'
        );
        $q->execute([$utente['id']]);

        if ((int) $q->fetchColumn() >= self::MAX_RICHIESTE_ORA) {
            error_log('Troppe richieste di accesso per ' . $email);
            return null;
        }

        $token = bin2hex(random_bytes(32));

        Db::pdo()->prepare(
            'INSERT INTO codici_accesso (utente_id, hash_codice, scade_il, ip_richiesta)
             VALUES (?, ?, UTC_TIMESTAMP() + INTERVAL ? MINUTE, ?)'
        )->execute([$utente['id'], hash('sha256', $token), self::VALIDITA_CODICE_MINUTI, $ip]);

        self::inviaEmail($utente, $token);

        return $token;
    }

    private static function inviaEmail(array $utente, string $token): void
    {
        $link = rtrim((string) Config::v('base_url'), '/') . '/entra?token=' . $token;
        $nome = htmlspecialchars($utente['nome'], ENT_QUOTES, 'UTF-8');
        $linkHtml = htmlspecialchars($link, ENT_QUOTES, 'UTF-8');
        $minuti = self::VALIDITA_CODICE_MINUTI;

        $html = <<<HTML
            <p>Ciao $nome,</p>
            <p>ecco il link per entrare:</p>
            <p><a href="$linkHtml"
                  style="display:inline-block;padding:14px 22px;background:#0284C7;
                         color:#fff;text-decoration:none;border-radius:8px;
                         font-family:system-ui,sans-serif">Entra</a></p>
            <p style="color:#475569;font-size:14px">
              Il link vale $minuti minuti e una volta sola.<br>
              Se non hai chiesto tu di entrare, ignora questa email.
            </p>
            HTML;

        $testo = "Ciao $nome,\n\necco il link per entrare:\n$link\n\n"
               . "Il link vale $minuti minuti e una volta sola.\n"
               . "Se non hai chiesto tu di entrare, ignora questa email.\n";

        Posta::invia($utente['email'], 'Il tuo link di accesso', $html, $testo);
    }

    // ------------------------------------------------------------------
    // Uso del link
    // ------------------------------------------------------------------

    /**
     * Consuma il token e apre la sessione.
     *
     * @return string|null il token di sessione da mettere nel cookie
     */
    /**
     * Il link vale senza consumarlo, in vista di essere mostrato.
     *
     * Serve al primo tocco: molti client di posta (Gmail e gli antivirus in
     * particolare) aprono da soli i link dentro un'email per controllarli
     * prima che l'utente li clicchi davvero. Se quell'apertura consumasse il
     * codice monouso, l'utente vero si troverebbe sempre un link "gia'
     * usato" — sembra un loop, ma e' lo scanner che arriva prima.
     */
    public static function tokenValido(string $token): bool
    {
        $q = Db::pdo()->prepare(
            'SELECT scade_il FROM codici_accesso WHERE hash_codice = ? AND usato_il IS NULL'
        );
        $q->execute([hash('sha256', $token)]);
        $scadeIl = $q->fetchColumn();

        if ($scadeIl === false) {
            return false;
        }

        $scadenza = new \DateTimeImmutable($scadeIl, new \DateTimeZone('UTC'));
        return $scadenza >= new \DateTimeImmutable('now', new \DateTimeZone('UTC'));
    }

    public static function entra(string $token, ?string $userAgent = null): ?string
    {
        return Db::transazione(function (\PDO $pdo) use ($token, $userAgent): ?string {
            $q = $pdo->prepare(
                'SELECT * FROM codici_accesso WHERE hash_codice = ? FOR UPDATE'
            );
            $q->execute([hash('sha256', $token)]);
            $codice = $q->fetch();

            if (!$codice || $codice['usato_il'] !== null) {
                return null;
            }

            $scadenza = new \DateTimeImmutable($codice['scade_il'], new \DateTimeZone('UTC'));
            if ($scadenza < new \DateTimeImmutable('now', new \DateTimeZone('UTC'))) {
                return null;
            }

            // Monouso: bruciato qui, dentro la stessa transazione che apre la
            // sessione. Un link inoltrato per sbaglio non vale una seconda volta.
            $pdo->prepare('UPDATE codici_accesso SET usato_il = UTC_TIMESTAMP() WHERE id = ?')
                ->execute([$codice['id']]);

            $sessione = bin2hex(random_bytes(32));

            $pdo->prepare(
                'INSERT INTO sessioni (id, utente_id, scade_il, ultimo_uso_il, user_agent)
                 VALUES (?, ?, UTC_TIMESTAMP() + INTERVAL ? DAY, UTC_TIMESTAMP(), ?)'
            )->execute([
                hash('sha256', $sessione),
                $codice['utente_id'],
                self::DURATA_SESSIONE_GIORNI,
                $userAgent !== null ? mb_substr($userAgent, 0, 255) : null,
            ]);

            $pdo->prepare('UPDATE utenti SET ultimo_accesso_il = UTC_TIMESTAMP() WHERE id = ?')
                ->execute([$codice['utente_id']]);

            return $sessione;
        });
    }

    // ------------------------------------------------------------------
    // Sessione
    // ------------------------------------------------------------------

    public static function utenteDaSessione(string $sessione): ?array
    {
        $q = Db::pdo()->prepare(
            'SELECT u.* FROM sessioni s JOIN utenti u ON u.id = s.utente_id
              WHERE s.id = ? AND s.scade_il > UTC_TIMESTAMP() AND u.attivo = 1'
        );
        $q->execute([hash('sha256', $sessione)]);
        $utente = $q->fetch();

        if (!$utente) {
            return null;
        }

        Db::pdo()->prepare('UPDATE sessioni SET ultimo_uso_il = UTC_TIMESTAMP() WHERE id = ?')
                 ->execute([hash('sha256', $sessione)]);

        return $utente;
    }

    public static function esci(string $sessione): void
    {
        Db::pdo()->prepare('DELETE FROM sessioni WHERE id = ?')
                 ->execute([hash('sha256', $sessione)]);
    }

    /** Rimuove codici scaduti e sessioni morte. Da chiamare dal cron. */
    public static function pulisci(): void
    {
        Db::pdo()->exec(
            'DELETE FROM codici_accesso
              WHERE scade_il < UTC_TIMESTAMP() - INTERVAL 7 DAY'
        );
        Db::pdo()->exec('DELETE FROM sessioni WHERE scade_il < UTC_TIMESTAMP()');
    }

    // ------------------------------------------------------------------
    // Uso dal browser
    // ------------------------------------------------------------------

    public static function corrente(): ?array
    {
        if (self::$utente !== null) {
            return self::$utente;
        }

        $cookie = $_COOKIE[self::COOKIE] ?? '';
        if ($cookie === '') {
            return null;
        }

        return self::$utente = self::utenteDaSessione($cookie);
    }

    public static function eAdmin(): bool
    {
        return (self::corrente()['ruolo'] ?? null) === 'admin';
    }

    public static function apriCookie(string $sessione): void
    {
        setcookie(self::COOKIE, $sessione, [
            'expires'  => time() + self::DURATA_SESSIONE_GIORNI * 86400,
            'path'     => Vista::base() . '/',
            'secure'   => !str_starts_with((string) Config::v('base_url'), 'http://'),
            'httponly' => true,     // fuori portata di JavaScript
            'samesite' => 'Lax',
        ]);
    }

    public static function chiudiCookie(): void
    {
        if (isset($_COOKIE[self::COOKIE])) {
            self::esci($_COOKIE[self::COOKIE]);
        }
        setcookie(self::COOKIE, '', ['expires' => time() - 3600, 'path' => Vista::base() . '/']);
        self::$utente = null;
    }

    public static function nomeCookie(): string
    {
        return self::COOKIE;
    }
}
