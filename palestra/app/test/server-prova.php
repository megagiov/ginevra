<?php
/**
 * Router per il server integrato di PHP, usato solo dai test: riproduce il
 * comportamento dell'.htaccess (file reali serviti cosi' come sono, tutto
 * il resto a index.php).
 */
$percorso = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$file = dirname(__DIR__) . $percorso;

if ($percorso !== '/' && is_file($file) && !str_ends_with($file, '.php')) {
    return false;
}

require dirname(__DIR__) . '/index.php';
