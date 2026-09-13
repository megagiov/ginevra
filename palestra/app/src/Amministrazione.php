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
            "SELECT p.id, p.slot_id, p.stato, u.id AS cliente_id, u.nome, u.telefono
               FROM prenotazioni p JOIN utenti u ON u.id = p.cliente_id
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
    public static function creaSlot(
        string $attoreId,
        string $data,          // Y-m-d, ora locale
        string $ora,           // H:i,   ora locale
        string $tipo,
        int    $capienza,
        int    $ripetizioni = 1
    ): array {
        self::esigiAdmin($attoreId);

        if (!in_array($tipo, ['individuale', 'gruppo'], true)) {
            throw new RegolaViolata('Tipo di lezione non valido');
        }

        $capienza = $tipo === 'individuale' ? 1 : $capienza;

        if ($tipo === 'gruppo' && ($capienza < 2 || $capienza > 4)) {
            throw new RegolaViolata('Un gruppo puo\' avere da 2 a 4 posti');
        }

        $ripetizioni = max(1, min(52, $ripetizioni));

        $inizio = \DateTimeImmutable::createFromFormat(
            'Y-m-d H:i', "$data $ora", self::fuso()
        );

        if ($inizio === false) {
            throw new RegolaViolata('Data od ora non valide');
        }

        $creati = 0;
        $saltati = [];

        for ($i = 0; $i < $ripetizioni; $i++) {
            // Si aggiungono settimane sull'ora locale, non sull'UTC: cosi'
            // dopo il cambio d'ora la lezione resta alle 18:00 per il
            // cliente, invece di spostarsi alle 17:00.
            $questo = $inizio->modify('+' . ($i * 7) . ' days');

            try {
                Db::pdo()->prepare(
                    'INSERT INTO slot (id, inizio, fine, tipo, capienza) VALUES (?,?,?,?,?)'
                )->execute([
                    Db::uuid(),
                    self::utc($questo),
                    self::utc($questo->modify('+' . self::DURATA_MINUTI . ' minutes')),
                    $tipo,
                    $capienza,
                ]);
                $creati++;
            } catch (PDOException $e) {
                // 45000 e' il trigger anti-sovrapposizione; 23000 l'unicita'
                // sull'orario di inizio. In entrambi i casi la sala e' gia'
                // occupata a quell'ora.
                if (in_array($e->getCode(), ['45000', '23000'], true)) {
                    $saltati[] = Vista::giorno($questo) . ' alle ' . $questo->format('H:i');
                    continue;
                }
                throw $e;
            }
        }

        return ['creati' => $creati, 'saltati' => $saltati];
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
