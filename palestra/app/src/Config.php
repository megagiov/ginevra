<?php
declare(strict_types=1);

namespace Studio;

/**
 * Configurazione: legge config.php se esiste, altrimenti le variabili
 * d'ambiente (usate dai test).
 */
final class Config
{
    private static ?array $valori = null;

    public static function tutto(): array
    {
        if (self::$valori !== null) {
            return self::$valori;
        }

        $percorso = dirname(__DIR__) . '/config.php';
        $daFile = is_readable($percorso) ? require $percorso : [];

        self::$valori = $daFile + [
            'db_host'        => getenv('DB_HOST') ?: 'localhost',
            'db_name'        => getenv('DB_NAME') ?: 'studio',
            'db_user'        => getenv('DB_USER') ?: 'root',
            'db_password'    => getenv('DB_PASSWORD') ?: '',
            'db_port'        => getenv('DB_PORT') ?: '3306',
            'session_secret' => getenv('SESSION_SECRET') ?: 'prova-non-usare-in-produzione',
            'base_url'       => getenv('BASE_URL') ?: 'http://localhost:8000',
            'smtp_host'      => getenv('SMTP_HOST') ?: '',
            'smtp_port'      => (int) (getenv('SMTP_PORT') ?: 465),
            'smtp_user'      => getenv('SMTP_USER') ?: '',
            'smtp_password'  => getenv('SMTP_PASSWORD') ?: '',
            'smtp_mittente'  => getenv('SMTP_MITTENTE') ?: 'Studio <no-reply@localhost>',
            'fuso'           => 'Europe/Rome',
            'nome_studio'    => 'Studio',
        ];

        return self::$valori;
    }

    public static function v(string $chiave): mixed
    {
        return self::tutto()[$chiave] ?? null;
    }

    /** Solo per i test. */
    public static function imposta(array $valori): void
    {
        self::$valori = $valori + self::tutto();
    }
}
