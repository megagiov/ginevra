<?php
declare(strict_types=1);
/** Stampa un token di accesso valido per l'email indicata. Solo per i test. */

foreach (['Config', 'Db', 'Posta', 'Regole', 'Accesso'] as $c) { require __DIR__ . "/../src/$c.php"; }

use Studio\Accesso;
use Studio\Config;

Config::imposta(['smtp_host' => '']);
echo Accesso::richiediLink($argv[1] ?? '') ?? '';
