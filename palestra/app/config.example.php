<?php
/**
 * Copiare come config.php e compilare. config.php non va versionato.
 *
 * Su Aruba i valori del database si leggono nel pannello, sezione "Database".
 */

return [
    // Database DEDICATO all'app: mai quello di WordPress, mai le sue credenziali.
    'db_host'     => 'localhost',
    'db_name'     => '',
    'db_user'     => '',
    'db_password' => '',

    // Stringa lunga e casuale, usata per firmare le sessioni.
    // Generala con:  php -r "echo bin2hex(random_bytes(32));"
    'session_secret' => '',

    // Indirizzo pubblico dell'app, senza barra finale.
    'base_url' => 'https://studio.esempio.it',

    // Posta: i link di accesso partono da qui. Usando una casella del
    // dominio le email arrivano in posta in arrivo invece che nello spam.
    'smtp_host'     => 'smtps.aruba.it',
    'smtp_port'     => 465,
    'smtp_user'     => '',
    'smtp_password' => '',
    'smtp_mittente' => 'Studio <no-reply@esempio.it>',

    // Fuso di visualizzazione. Nel database gli orari sono sempre UTC.
    'fuso' => 'Europe/Rome',
];
