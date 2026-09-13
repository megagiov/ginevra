<?php
declare(strict_types=1);

namespace Studio;

use PDO;
use PDOException;

/**
 * Connessione al database e confine transazionale.
 *
 * Tutto cio' che tocca piu' di una tabella passa da transazione(): su MySQL
 * le regole non sono piu' garantite dal database come su PostgreSQL, quindi
 * l'atomicita' e' l'unica cosa che impedisce a un errore a meta' strada di
 * lasciare una prenotazione senza il suo movimento di credito.
 */
final class Db
{
    private static ?PDO $pdo = null;

    public static function pdo(): PDO
    {
        if (self::$pdo instanceof PDO) {
            return self::$pdo;
        }

        $cfg = Config::tutto();

        $dsn = sprintf(
            'mysql:host=%s;port=%s;dbname=%s;charset=utf8mb4',
            $cfg['db_host'], $cfg['db_port'], $cfg['db_name']
        );
        $user = $cfg['db_user'];
        $pass = $cfg['db_password'];

        try {
            self::$pdo = new PDO($dsn, $user, $pass, [
                PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                // Prepared statement veri, non emulati: senza questo i
                // parametri vengono interpolati da PDO e i tipi si perdono.
                PDO::ATTR_EMULATE_PREPARES   => false,
            ]);
        } catch (PDOException $e) {
            // Il messaggio di PDO contiene la stringa di connessione, e quindi
            // l'utenza del database: non deve mai arrivare al browser.
            error_log('Connessione al database fallita: ' . $e->getMessage());
            throw new \RuntimeException('Database non raggiungibile');
        }

        // Il server puo' avere qualunque fuso: lo si fissa a UTC per la
        // sessione, cosi' NOW() e le colonne DATETIME parlano la stessa lingua.
        self::$pdo->exec("SET time_zone = '+00:00'");

        return self::$pdo;
    }

    /**
     * Esegue $operazione dentro una transazione, con commit automatico e
     * rollback su qualunque errore.
     *
     * @template T
     * @param callable(PDO): T $operazione
     * @return T
     */
    public static function transazione(callable $operazione): mixed
    {
        $pdo = self::pdo();
        $pdo->beginTransaction();

        try {
            $esito = $operazione($pdo);
            $pdo->commit();
            return $esito;
        } catch (\Throwable $e) {
            if ($pdo->inTransaction()) {
                $pdo->rollBack();
            }
            throw $e;
        }
    }

    /** Identificatore non indovinabile: gli id finiscono negli URL. */
    public static function uuid(): string
    {
        $b = random_bytes(16);
        $b[6] = chr((ord($b[6]) & 0x0f) | 0x40);   // versione 4
        $b[8] = chr((ord($b[8]) & 0x3f) | 0x80);   // variante RFC 4122
        return vsprintf('%s%s-%s-%s-%s-%s%s%s', str_split(bin2hex($b), 4));
    }

    /** Solo per i test. */
    public static function usa(PDO $pdo): void
    {
        self::$pdo = $pdo;
        $pdo->exec("SET time_zone = '+00:00'");
    }
}
