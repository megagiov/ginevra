<?php
declare(strict_types=1);

/**
 * Legge il contenuto REALE di admin-clienti.php cosi' come sta sul disco
 * del server, senza eseguirlo. Serve a distinguere due cose che sembrano
 * identiche da fuori:
 *
 *  - il file caricato via FTP non e' quello giusto (si vedrebbe qui)
 *  - il file e' giusto ma il server esegue una versione compilata vecchia,
 *    tenuta in memoria (l'opcache di PHP) — qui si vedrebbe giusto, ma la
 *    pagina vera continuerebbe a comportarsi in modo diverso
 *
 * Cancellalo dal server appena finito, come verifica.php.
 */

header('Content-Type: text/plain; charset=utf-8');

$file = __DIR__ . '/pagine/admin-clienti.php';

if (!is_file($file)) {
    echo "Il file non esiste in questo percorso: $file\n";
    exit;
}

echo "Percorso:         $file\n";
echo "Ultima modifica:  " . date('d/m/Y H:i:s', filemtime($file)) . "\n";
echo "Dimensione:       " . filesize($file) . " byte\n\n";

echo "--- Righe che contengono \"admin/cliente\" ---\n";
foreach (file($file) as $numero => $riga) {
    if (str_contains($riga, 'admin/cliente')) {
        printf("%4d: %s", $numero + 1, $riga);
    }
}

echo "\n--- Stato dell'opcache di PHP ---\n";
if (function_exists('opcache_get_status')) {
    $stato = opcache_get_status(false);
    echo "Opcache attiva: " . ($stato === false ? 'no' : 'si') . "\n";

    if ($stato !== false && function_exists('opcache_is_script_cached')) {
        $inCache = opcache_is_script_cached($file);
        echo "Questo file e' nella cache compilata: " . ($inCache ? 'SI' : 'no') . "\n";

        if ($inCache) {
            echo "\nQuesto e' probabilmente il problema: il server sta eseguendo\n"
               . "una versione compilata del file che non si aggiorna da sola.\n"
               . "Aggiungendo ?svuota=1 a questo indirizzo provo a svuotarla.\n";
        }
    }
} else {
    echo "La funzione opcache_get_status non e' disponibile da qui:\n"
       . "l'opcache potrebbe comunque essere attiva a livello del server.\n";
}

if (isset($_GET['svuota']) && function_exists('opcache_reset')) {
    $riuscito = opcache_reset();
    echo "\n--- Tentativo di svuotamento ---\n";
    echo $riuscito ? "Fatto: la cache compilata e' stata svuotata.\n"
                   : "Non riuscito: il server nega il permesso da qui.\n";
}
