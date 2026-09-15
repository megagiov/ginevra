<?php
declare(strict_types=1);

/**
 * Impalcatura condivisa dalle suite di test.
 *
 * Niente PHPUnit: sull'hosting di destinazione non c'e' Composer, e queste
 * suite devono poter girare anche li' con il solo PHP.
 */

$GLOBALS['esiti'] = [];

function ok(string $descrizione, bool $condizione): void
{
    $GLOBALS['esiti'][] = $condizione;
    printf("%s  %s\n", $condizione ? 'PASS' : 'FAIL', $descrizione);
}

/** L'operazione deve fallire, e il messaggio deve parlare della cosa giusta. */
function errore(string $descrizione, callable $operazione, string $frammento): void
{
    try {
        $operazione();
        ok($descrizione . ' — atteso errore, non e\' arrivato', false);
    } catch (\Studio\RegolaViolata $e) {
        ok($descrizione . '  [' . $e->getMessage() . ']',
           stripos($e->getMessage(), $frammento) !== false);
    } catch (\Throwable $e) {
        ok($descrizione . ' — eccezione inattesa: ' . $e->getMessage(), false);
    }
}

function utc(string $quando): string
{
    return (new DateTimeImmutable($quando, new DateTimeZone('UTC')))->format('Y-m-d H:i:s');
}

/**
 * I trigger nello schema usano DELIMITER, che e' una direttiva del client
 * mysql e non un comando del server: qui si ricostruiscono gli statement
 * rispettando il delimitatore in vigore.
 */
function spezzaSql(string $sql): array
{
    $out = [];
    $delimitatore = ';';
    $buffer = '';

    foreach (preg_split('/\R/', $sql) as $riga) {
        if (preg_match('/^\s*delimiter\s+(\S+)/i', $riga, $m)) {
            $delimitatore = $m[1];
            continue;
        }

        // I commenti si scartano subito: se finissero nel buffer, lo
        // statement che li segue sembrerebbe cominciare con "--".
        if (preg_match('/^\s*--/', $riga) || trim($riga) === '') {
            continue;
        }

        $buffer .= $riga . "\n";

        if (str_ends_with(rtrim($buffer), $delimitatore)) {
            $pezzo = trim(substr(rtrim($buffer), 0, -strlen($delimitatore)));
            if ($pezzo !== '') {
                $out[] = $pezzo;
            }
            $buffer = '';
        }
    }

    return $out;
}

function preparaDatabase(): PDO
{
    $db   = getenv('DB_NAME')     ?: 'studio_test';
    $host = getenv('DB_HOST')     ?: 'localhost';
    $user = getenv('DB_USER')     ?: 'root';
    $pass = getenv('DB_PASSWORD') ?: '';

    $root = new PDO("mysql:host=$host;charset=utf8mb4", $user, $pass,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
    $root->exec("DROP DATABASE IF EXISTS `$db`");
    $root->exec("CREATE DATABASE `$db` CHARACTER SET utf8mb4");

    $pdo = new PDO("mysql:host=$host;dbname=$db;charset=utf8mb4", $user, $pass, [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);

    // Tutte le migrazioni in ordine, cosi' il database di prova resta
    // identico a quello che si ottiene applicandole a mano da phpMyAdmin.
    $migrazioni = glob(__DIR__ . '/../../db/mysql/migrations/*.sql');
    sort($migrazioni);

    foreach ($migrazioni as $file) {
        foreach (spezzaSql(file_get_contents($file)) as $statement) {
            $pdo->exec($statement);
        }
    }

    return $pdo;
}

function esito(): void
{
    $totali  = count($GLOBALS['esiti']);
    $falliti = count(array_filter($GLOBALS['esiti'], fn($e) => !$e));

    printf("\n%d passati, %d falliti, %d totali\n", $totali - $falliti, $falliti, $totali);
    exit($falliti > 0 ? 1 : 0);
}
