<?php
/**
 * Router per il server integrato di PHP che simula l'app installata in una
 * sottocartella, come su Aruba dentro www.startupmoda.com/studio.
 *
 * Apache imposterebbe SCRIPT_NAME a /studio/index.php: qui si fa lo stesso,
 * perche' e' da quel valore che l'app ricava il proprio prefisso.
 */
$radice   = getenv('RADICE_SITO') ?: sys_get_temp_dir() . '/sito';
$percorso = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$file     = $radice . $percorso;

// Come l'.htaccess: un file che esiste davvero viene servito cosi' com'e'
// (compresi i .php, che il server esegue). Solo il resto va a index.php.
if (is_file($file)) {
    return false;
}

$_SERVER['SCRIPT_NAME'] = '/studio/index.php';
require $radice . '/studio/index.php';
