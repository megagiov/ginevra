<?php
declare(strict_types=1);

namespace Studio;

use PDO;
use PDOException;

/**
 * Operazioni e letture riservate all'amministratore.
 *
 * Sta separata da Regole perche' quelle valgono per tutti: qui invece ogni
 * metodo comincia col verificare chi sta agendo. Nessuna eccezione, nemmeno
 * per le sole letture — l'elenco clienti e' un elenco di dati sanitari.
 */
final class Amministrazione
{
    private const DURATA_MINUTI = 60;

    private static function esigiAdmin(string $attoreId): void
    {
        $q = Db::pdo()->prepare(
            "SELECT 1 FROM utenti WHERE id = ? AND ruolo = 'admin' AND attivo = 1"
        );
        $q->execute([$attoreId]);

        if (!$q->fetchColumn()) {
            throw new RegolaViolata('Riservato all\'amministratore');
        }
    }

    private static function utc(\DateTimeImmutable $locale): string
    {
        return $locale->setTimezone(new \DateTimeZone('UTC'))->format('Y-m-d H:i:s');
    }

    private static function fuso(): \DateTimeZone
    {
        return new \DateTimeZone((string) Config::v('fuso'));
    }

    // ------------------------------------------------------------------
    // Agenda del giorno
    // ------------------------------------------------------------------

    /**
     * Le lezioni di un giorno con i rispettivi partecipanti.
     *
     * E' la schermata su cui si lavora in sala: deve dire in un colpo
     * d'occhio chi arriva e a che ora.
     */
    public static function agenda(string $attoreId, \DateTimeImmutable $giornoLocale): array
    {
        self::esigiAdmin($attoreId);

        $da = $giornoLocale->setTime(0, 0);
        $a  = $da->modify('+1 day');

        $q = Db::pdo()->prepare(
            'SELECT d.* FROM slot_disponibilita d
              WHERE d.inizio >= ? AND d.inizio < ?
              ORDER BY d.inizio'
        );
        $q->execute([self::utc($da), self::utc($a)]);
        $slot = $q->fetchAll();

        if ($slot === []) {
            return [];
        }

        $segnaposto = implode(',', array_fill(0, count($slot), '?'));
        $p = Db::pdo()->prepare(
            "SELECT p.id, p.slot_id, p.stato, u.id AS cliente_id, u.nome, u.telefono,
                    m.nome AS maestro_nome
               FROM prenotazioni p JOIN utenti u ON u.id = p.cliente_id
               LEFT JOIN maestri m ON m.id = p.maestro_id
              WHERE p.slot_id IN ($segnaposto) AND p.stato <> 'disdetta'
              ORDER BY u.nome"
        );
        $p->execute(array_column($slot, 'id'));

        $perSlot = [];
        foreach ($p->fetchAll() as $riga) {
            $perSlot[$riga['slot_id']][] = $riga;
        }

        return array_map(fn(array $s): array => $s + [
            'locale'        => Vista::locale($s['inizio']),
            'partecipanti'  => $perSlot[$s['id']] ?? [],
        ], $slot);
    }

    /** Le lezioni di una settimana, raggruppate per giorno locale. */
    public static function settimana(string $attoreId, \DateTimeImmutable $lunediLocale): array
    {
        self::esigiAdmin($attoreId);

        $da = $lunediLocale->setTime(0, 0);
        $a  = $da->modify('+7 days');

        $q = Db::pdo()->prepare(
            'SELECT * FROM slot_disponibilita
              WHERE inizio >= ? AND inizio < ? ORDER BY inizio'
        );
        $q->execute([self::utc($da), self::utc($a)]);

        $perGiorno = [];
        for ($i = 0; $i < 7; $i++) {
            $perGiorno[$da->modify("+$i days")->format('Y-m-d')] = [];
        }

        foreach ($q->fetchAll() as $s) {
            $locale = Vista::locale($s['inizio']);
            $perGiorno[$locale->format('Y-m-d')][] = $s + ['locale' => $locale];
        }

        return $perGiorno;
    }

    // ------------------------------------------------------------------
    // Pubblicazione della disponibilita'
    // ------------------------------------------------------------------

    /**
     * Crea una lezione, eventualmente ripetuta per piu' settimane.
     *
     * Le ripetizioni che cadrebbero sopra una lezione gia' in calendario
     * vengono saltate e riportate: meglio dire quali giorni non sono
     * passati che rifiutare tutto il blocco.
     *
     * @return array{creati:int, saltati:list<string>}
     */
    /** Da valore del modulo ('1'..'7', come DateTime::format('N')) a offset in giorni dal lunedi'. */
    private const GIORNI_SETTIMANA_VALIDI = ['1', '2', '3', '4', '5', '6', '7'];

    /**
     * Crea lezioni per piu' giorni della settimana e piu' orari in un colpo
     * solo, di un tipo o di entrambi, eventualmente ripetute per piu'
     * settimane.
     *
     * Pensato per organizzare tutta una settimana tipo in una volta sola:
     * si spuntano i giorni (come le ore) invece di ripetere il modulo una
     * volta per ogni combinazione. "Entrambi" pubblica un'individuale e un
     * gruppo nello stesso orario, per chi ha un secondo maestro disponibile.
     *
     * @param string $lunediSettimana Y-m-d, il lunedi' della settimana da cui partire (ora locale)
     * @param list<string> $giorni '1' (lunedi') .. '7' (domenica)
     * @param list<string> $ore 'H:i', ora locale
     * @param array{individuale?:list<string>, gruppo?:list<string>} $maestriPerTipo
     *        id dei maestri candidati per ciascun tipo creato, applicati a
     *        tutte le lezioni di questo invio. Con uno solo per tipo
     *        l'assegnazione e' automatica alla prenotazione; con zero non
     *        cambia nulla rispetto a prima di avere i maestri in app.
     */
    public static function creaSlot(
        string $attoreId,
        string $lunediSettimana,
        array  $giorni,
        array  $ore,
        string $tipo,
        int    $capienza,
        int    $ripetizioni = 1,
        array  $maestriPerTipo = []
    ): array {
        self::esigiAdmin($attoreId);

        if (!in_array($tipo, ['individuale', 'gruppo', 'entrambi'], true)) {
            throw new RegolaViolata('Tipo di lezione non valido');
        }

        $tipiDaCreare = $tipo === 'entrambi' ? ['individuale', 'gruppo'] : [$tipo];

        if (in_array('gruppo', $tipiDaCreare, true) && ($capienza < 2 || $capienza > 4)) {
            throw new RegolaViolata('Un gruppo puo\' avere da 2 a 4 posti');
        }

        if ($giorni === [] || $ore === []) {
            throw new RegolaViolata('Scegli almeno un giorno e un\'ora');
        }

        if (array_diff($giorni, self::GIORNI_SETTIMANA_VALIDI) !== []) {
            throw new RegolaViolata('Giorno della settimana non valido');
        }

        foreach ($ore as $ora) {
            if (!preg_match('/^([01]\d|2[0-3]):00$/', $ora)) {
                throw new RegolaViolata('Ora non valida');
            }
        }

        $ripetizioni = max(1, min(52, $ripetizioni));

        $lunedi = \DateTimeImmutable::createFromFormat('Y-m-d', $lunediSettimana, self::fuso());
        if ($lunedi === false) {
            throw new RegolaViolata('Data non valida');
        }
        $lunedi = $lunedi->setTime(0, 0);

        $creati = 0;
        $saltati = [];

        for ($settimana = 0; $settimana < $ripetizioni; $settimana++) {
            foreach ($giorni as $giornoIso) {
                // Si aggiungono giorni sull'ora locale, non sull'UTC: cosi'
                // dopo il cambio d'ora la lezione resta alla sua ora per il
                // cliente, invece di spostarsi di un'ora.
                $giornoData = $lunedi->modify('+' . ((int) $giornoIso - 1 + $settimana * 7) . ' days');

                foreach ($ore as $ora) {
                    $inizio = \DateTimeImmutable::createFromFormat(
                        'Y-m-d H:i', $giornoData->format('Y-m-d') . " $ora", self::fuso()
                    );

                    foreach ($tipiDaCreare as $unTipo) {
                        $capienzaEffettiva = $unTipo === 'individuale' ? 1 : $capienza;
                        $slotId = Db::uuid();
                        $maestri = $maestriPerTipo[$unTipo] ?? [];

                        try {
                            Db::transazione(function (\PDO $pdo) use (
                                $slotId, $inizio, $unTipo, $capienzaEffettiva, $maestri
                            ): void {
                                $pdo->prepare(
                                    'INSERT INTO slot (id, inizio, fine, tipo, capienza) VALUES (?,?,?,?,?)'
                                )->execute([
                                    $slotId,
                                    self::utc($inizio),
                                    self::utc($inizio->modify('+' . self::DURATA_MINUTI . ' minutes')),
                                    $unTipo,
                                    $capienzaEffettiva,
                                ]);

                                $q = $pdo->prepare(
                                    'INSERT INTO slot_maestri (slot_id, maestro_id) VALUES (?, ?)'
                                );
                                foreach ($maestri as $maestroId) {
                                    $q->execute([$slotId, $maestroId]);
                                }
                            });
                            $creati++;
                        } catch (PDOException $e) {
                            // 45000 e' il trigger anti-sovrapposizione dello
                            // stesso tipo; 23000 l'unicita' su orario+tipo
                            // (o un maestro inesistente). In tutti i casi
                            // non si crea la lezione.
                            if (in_array($e->getCode(), ['45000', '23000'], true)) {
                                $saltati[] = Vista::giorno($inizio) . ' alle ' . $inizio->format('H:i')
                                           . (count($tipiDaCreare) > 1 ? " ($unTipo)" : '');
                                continue;
                            }
                            throw $e;
                        }
                    }
                }
            }
        }

        return ['creati' => $creati, 'saltati' => $saltati];
    }

    // ------------------------------------------------------------------
    // Maestri
    // ------------------------------------------------------------------

    /** Elenco maestri, i disattivati compresi se richiesto. */
    public static function maestri(string $attoreId, bool $ancheInattivi = false): array
    {
        self::esigiAdmin($attoreId);

        $filtro = $ancheInattivi ? '' : 'WHERE attivo = 1';
        return Db::pdo()->query("SELECT * FROM maestri $filtro ORDER BY nome")->fetchAll();
    }

    public static function creaMaestro(string $attoreId, string $nome): string
    {
        self::esigiAdmin($attoreId);

        $nome = trim($nome);
        if ($nome === '') {
            throw new RegolaViolata('Il nome del maestro e\' obbligatorio');
        }

        $id = Db::uuid();
        Db::pdo()->prepare('INSERT INTO maestri (id, nome) VALUES (?, ?)')->execute([$id, $nome]);

        return $id;
    }

    /**
     * Disattivare non tocca gli slot gia' pubblicati con questo maestro tra
     * i candidati: resta valido dove gia' assegnato, semplicemente non lo si
     * puo' piu' scegliere per le prossime lezioni.
     */
    public static function cambiaAttivazioneMaestro(string $attoreId, string $maestroId, bool $attivo): void
    {
        self::esigiAdmin($attoreId);

        Db::pdo()->prepare('UPDATE maestri SET attivo = ? WHERE id = ?')
                 ->execute([$attivo ? 1 : 0, $maestroId]);
    }

    public static function cambiaStatoSlot(string $attoreId, string $slotId, string $stato): void
    {
        self::esigiAdmin($attoreId);

        if (!in_array($stato, ['aperto', 'chiuso'], true)) {
            throw new RegolaViolata('Stato non valido');
        }

        Db::pdo()->prepare('UPDATE slot SET stato = ? WHERE id = ?')
                 ->execute([$stato, $slotId]);
    }

    /**
     * Elimina una lezione dal calendario.
     *
     * Si rifiuta se qualcuno l'ha prenotata: quella lezione va prima
     * disdetta, cosi' il credito torna al cliente invece di sparire.
     */
    public static function eliminaSlot(string $attoreId, string $slotId): void
    {
        self::esigiAdmin($attoreId);

        $q = Db::pdo()->prepare('SELECT COUNT(*) FROM prenotazioni WHERE slot_id = ?');
        $q->execute([$slotId]);

        if ((int) $q->fetchColumn() > 0) {
            throw new RegolaViolata(
                'Questa lezione ha prenotazioni: disdicile prima, cosi' .
                '\' il credito torna ai clienti. In alternativa chiudila.'
            );
        }

        Db::pdo()->prepare('DELETE FROM slot WHERE id = ?')->execute([$slotId]);
    }

    // ------------------------------------------------------------------
    // Clienti
    // ------------------------------------------------------------------

    /** Elenco con i due saldi accanto: e' il primo dato che serve. */
    public static function clienti(string $attoreId, bool $ancheInattivi = false): array
    {
        self::esigiAdmin($attoreId);

        $filtro = $ancheInattivi ? '' : 'WHERE u.attivo = 1';

        return Db::pdo()->query(
            // I saldi restano NULL quando il cliente non ha mai avuto lezioni
            // di quel tipo: e' diverso da zero, e l'elenco lo mostra diverso.
            "SELECT u.*,
                    si.saldo AS saldo_individuale,
                    sg.saldo AS saldo_gruppo,
                    (SELECT MAX(s.inizio) FROM prenotazioni p JOIN slot s ON s.id = p.slot_id
                      WHERE p.cliente_id = u.id AND p.stato = 'presente') AS ultima_presenza
               FROM utenti u
               LEFT JOIN saldi si ON si.cliente_id = u.id AND si.tipo = 'individuale'
               LEFT JOIN saldi sg ON sg.cliente_id = u.id AND sg.tipo = 'gruppo'
               $filtro
              ORDER BY u.nome"
        )->fetchAll();
    }

    public static function cliente(string $attoreId, string $clienteId): ?array
    {
        self::esigiAdmin($attoreId);

        $q = Db::pdo()->prepare('SELECT * FROM utenti WHERE id = ?');
        $q->execute([$clienteId]);
        $cliente = $q->fetch();

        if (!$cliente) {
            return null;
        }

        return [
            'anagrafica' => $cliente,
            'saldi'      => Calendario::saldi($clienteId),
            'movimenti'  => Calendario::movimenti($clienteId),
            'prossime'   => Calendario::prossime($clienteId),
            'passate'    => Calendario::passate($clienteId, 10),
        ];
    }

    public static function creaCliente(
        string  $attoreId,
        string  $nome,
        string  $email,
        ?string $telefono = null,
        ?string $note = null
    ): string {
        self::esigiAdmin($attoreId);

        $nome  = trim($nome);
        $email = mb_strtolower(trim($email));

        if ($nome === '') {
            throw new RegolaViolata('Il nome e\' obbligatorio');
        }

        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            throw new RegolaViolata('Email non valida');
        }

        $id = Db::uuid();

        try {
            Db::pdo()->prepare(
                'INSERT INTO utenti (id, nome, email, telefono, note) VALUES (?,?,?,?,?)'
            )->execute([$id, $nome, $email, $telefono ?: null, $note ?: null]);
        } catch (PDOException $e) {
            if ($e->getCode() === '23000') {
                throw new RegolaViolata('Esiste gia\' un cliente con questa email');
            }
            throw $e;
        }

        return $id;
    }

    /**
     * Scrive o aggiorna il piano alimentare e di allenamento a casa del
     * cliente. Testo libero, non validato oltre la lunghezza: e' consiglio
     * del personal trainer, non una regola dell'app.
     */
    public static function salvaPiano(
        string $attoreId,
        string $clienteId,
        ?string $alimentare,
        ?string $allenamento
    ): void {
        self::esigiAdmin($attoreId);

        $alimentare  = trim((string) $alimentare) ?: null;
        $allenamento = trim((string) $allenamento) ?: null;

        $q = Db::pdo()->prepare(
            'UPDATE utenti SET piano_alimentare = ?, piano_allenamento = ?,
                    piano_aggiornato_il = UTC_TIMESTAMP()
              WHERE id = ?'
        );
        $q->execute([$alimentare, $allenamento, $clienteId]);

        if ($q->rowCount() === 0) {
            // rowCount a 0 vale anche per un salvataggio che non cambia
            // nulla rispetto a prima: non e' un errore, si distingue
            // controllando se il cliente esiste davvero.
            $c = Db::pdo()->prepare('SELECT 1 FROM utenti WHERE id = ?');
            $c->execute([$clienteId]);
            if (!$c->fetchColumn()) {
                throw new RegolaViolata('Cliente inesistente');
            }
        }
    }

    public static function cambiaAttivazione(string $attoreId, string $clienteId, bool $attivo): void
    {
        self::esigiAdmin($attoreId);

        if ($clienteId === $attoreId) {
            throw new RegolaViolata('Non puoi disattivare te stesso');
        }

        Db::pdo()->prepare('UPDATE utenti SET attivo = ? WHERE id = ?')
                 ->execute([$attivo ? 1 : 0, $clienteId]);

        // Disattivare significa togliere l'accesso subito, non al prossimo
        // giro: le sessioni aperte vanno chiuse.
        if (!$attivo) {
            Db::pdo()->prepare('DELETE FROM sessioni WHERE utente_id = ?')->execute([$clienteId]);
        }
    }

    // ------------------------------------------------------------------
    // Impostazioni
    //
    // Le stesse quattro chiavi lette da Regole::impostazione(), ma con
    // un'etichetta leggibile ed estremi larghi ma sensati: servono a non
    // far scrivere per sbaglio un valore che romperebbe le prenotazioni
    // (zero prenotazioni aperte, mesi di anticipo minimo), non a imporre
    // una policy di gestione.
    // ------------------------------------------------------------------

    private const CAMPI_IMPOSTAZIONI = [
        'finestra_disdetta_ore'   => ['etichetta' => 'Finestra di disdetta (ore)',              'min' => 0, 'max' => 168],
        'anticipo_minimo_ore'     => ['etichetta' => 'Anticipo minimo per prenotare (ore)',      'min' => 0, 'max' => 168],
        'max_prenotazioni_aperte' => ['etichetta' => 'Prenotazioni future aperte per cliente',   'min' => 1, 'max' => 20],
        'giorni_visibili'         => ['etichetta' => 'Giorni di calendario mostrati al cliente', 'min' => 1, 'max' => 60],
    ];

    /** Le impostazioni nell'ordine in cui ha senso leggerle, non alfabetico. */
    public static function impostazioni(string $attoreId): array
    {
        self::esigiAdmin($attoreId);

        $q = Db::pdo()->query('SELECT chiave, valore, nota FROM impostazioni');
        $perChiave = [];
        foreach ($q->fetchAll() as $r) {
            $perChiave[$r['chiave']] = $r;
        }

        $righe = [];
        foreach (self::CAMPI_IMPOSTAZIONI as $chiave => $info) {
            if (isset($perChiave[$chiave])) {
                $righe[] = $perChiave[$chiave] + $info;
            }
        }
        return $righe;
    }

    /** @param array<string,mixed> $valori chiave => nuovo valore, dal modulo */
    public static function salvaImpostazioni(string $attoreId, array $valori): void
    {
        self::esigiAdmin($attoreId);

        $nuovi = [];
        foreach (self::CAMPI_IMPOSTAZIONI as $chiave => $info) {
            $v = filter_var($valori[$chiave] ?? null, FILTER_VALIDATE_INT);

            if ($v === false || $v < $info['min'] || $v > $info['max']) {
                throw new RegolaViolata(
                    "«{$info['etichetta']}» deve essere un numero tra {$info['min']} e {$info['max']}"
                );
            }
            $nuovi[$chiave] = $v;
        }

        Db::transazione(function (PDO $pdo) use ($nuovi): void {
            $q = $pdo->prepare('UPDATE impostazioni SET valore = ? WHERE chiave = ?');
            foreach ($nuovi as $chiave => $valore) {
                $q->execute([$valore, $chiave]);
            }
        });
    }

    // ------------------------------------------------------------------
    // Riepilogo per la schermata di oggi
    // ------------------------------------------------------------------

    /** @return array{lezioni:int, persone:int, da_registrare:int, in_esaurimento:int} */
    public static function riepilogo(string $attoreId, \DateTimeImmutable $giornoLocale): array
    {
        self::esigiAdmin($attoreId);

        $agenda   = self::agenda($attoreId, $giornoLocale);
        $persone  = 0;
        $daSegnare = 0;

        foreach ($agenda as $slot) {
            foreach ($slot['partecipanti'] as $p) {
                $persone++;
                if ($p['stato'] === 'prenotata' && $slot['locale'] < new \DateTimeImmutable('now', self::fuso())) {
                    $daSegnare++;
                }
            }
        }

        // Chi sta per restare senza lezioni: e' l'avviso che evita di
        // accorgersi troppo tardi che un pacchetto e' finito.
        $q = Db::pdo()->query(
            "SELECT COUNT(DISTINCT u.id) FROM utenti u
               JOIN saldi s ON s.cliente_id = u.id
              WHERE u.attivo = 1 AND u.ruolo = 'cliente' AND s.saldo <= 2"
        );

        return [
            'lezioni'        => count($agenda),
            'persone'        => $persone,
            'da_registrare'  => $daSegnare,
            'in_esaurimento' => (int) $q->fetchColumn(),
        ];
    }
}
