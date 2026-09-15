<?php
declare(strict_types=1);

namespace Studio;

use PDO;

/**
 * Violazione di una regola di prenotazione.
 *
 * Il messaggio e' pensato per essere mostrato al cliente cosi' com'e': deve
 * dire cosa e' successo, non "errore 500".
 */
final class RegolaViolata extends \RuntimeException {}

/**
 * Le regole dello studio.
 *
 * Su PostgreSQL vivevano in funzioni del database e nessun percorso poteva
 * scavalcarle. Su MySQL vivono qui, e questa classe e' l'unico punto da cui
 * si scrive su `prenotazioni` e `movimenti`: nessun'altra parte del codice
 * deve inserire in quelle tabelle direttamente.
 *
 * Gli orari sono sempre UTC.
 */
final class Regole
{
    // ------------------------------------------------------------------
    // Lettura delle impostazioni
    // ------------------------------------------------------------------

    public static function impostazione(string $chiave): int
    {
        static $cache = [];

        if (!isset($cache[$chiave])) {
            $q = Db::pdo()->prepare('SELECT valore FROM impostazioni WHERE chiave = ?');
            $q->execute([$chiave]);
            $v = $q->fetchColumn();

            if ($v === false) {
                throw new \RuntimeException("Impostazione mancante: $chiave");
            }
            $cache[$chiave] = (int) $v;
        }

        return $cache[$chiave];
    }

    public static function saldo(string $clienteId, string $tipo): int
    {
        $q = Db::pdo()->prepare(
            'SELECT COALESCE(SUM(delta), 0) FROM movimenti
              WHERE cliente_id = ? AND tipo = ?'
        );
        $q->execute([$clienteId, $tipo]);

        return (int) $q->fetchColumn();
    }

    private static function eAdmin(string $utenteId): bool
    {
        $q = Db::pdo()->prepare(
            "SELECT 1 FROM utenti WHERE id = ? AND ruolo = 'admin' AND attivo = 1"
        );
        $q->execute([$utenteId]);

        return (bool) $q->fetchColumn();
    }

    // ------------------------------------------------------------------
    // prenota
    // ------------------------------------------------------------------

    /**
     * Occupa un posto e scala il credito.
     *
     * @param string $attoreId chi sta agendo: il cliente stesso oppure
     *                         l'amministratore che prenota per suo conto
     * @param ?string $maestroId chi ha scelto il cliente, quando lo slot ha
     *                           piu' di un maestro candidato. Con uno solo
     *                           candidato si assegna da solo, e questo
     *                           parametro viene ignorato; con zero resta
     *                           null, come prima di avere i maestri in app.
     * @return string id della prenotazione
     */
    public static function prenota(
        string $slotId,
        string $clienteId,
        string $attoreId,
        ?string $maestroId = null
    ): string {
        if ($attoreId !== $clienteId && !self::eAdmin($attoreId)) {
            throw new RegolaViolata('Non puoi prenotare per un altro cliente');
        }

        return Db::transazione(function (PDO $pdo) use ($slotId, $clienteId, $attoreId, $maestroId): string {

            $q = $pdo->prepare('SELECT id, attivo FROM utenti WHERE id = ? FOR UPDATE');
            $q->execute([$clienteId]);
            $cliente = $q->fetch();

            if (!$cliente || (int) $cliente['attivo'] !== 1) {
                throw new RegolaViolata('Cliente inesistente o non attivo');
            }

            $q = $pdo->prepare('SELECT * FROM slot WHERE id = ? FOR UPDATE');
            $q->execute([$slotId]);
            $slot = $q->fetch();

            if (!$slot) {
                throw new RegolaViolata('Lezione inesistente');
            }

            if ($slot['stato'] !== 'aperto') {
                throw new RegolaViolata('Questa lezione non e\' prenotabile');
            }

            $anticipo = self::impostazione('anticipo_minimo_ore');
            $limite   = new \DateTimeImmutable("+{$anticipo} hours", new \DateTimeZone('UTC'));
            $inizio   = new \DateTimeImmutable($slot['inizio'], new \DateTimeZone('UTC'));

            if ($inizio < $limite) {
                throw new RegolaViolata(
                    "Troppo tardi per prenotare: servono almeno $anticipo ore di anticipo"
                );
            }

            $q = $pdo->prepare(
                "SELECT COUNT(*) FROM prenotazioni
                  WHERE slot_id = ? AND cliente_id = ? AND stato <> 'disdetta'"
            );
            $q->execute([$slotId, $clienteId]);

            if ((int) $q->fetchColumn() > 0) {
                throw new RegolaViolata('Hai gia\' un posto in questa lezione');
            }

            $q = $pdo->prepare(
                "SELECT COUNT(*) FROM prenotazioni
                  WHERE slot_id = ? AND stato <> 'disdetta'"
            );
            $q->execute([$slotId]);

            if ((int) $q->fetchColumn() >= (int) $slot['capienza']) {
                throw new RegolaViolata('Nessun posto libero in questa lezione');
            }

            $q = $pdo->prepare(
                'SELECT COALESCE(SUM(delta), 0) FROM movimenti
                  WHERE cliente_id = ? AND tipo = ?'
            );
            $q->execute([$clienteId, $slot['tipo']]);

            if ((int) $q->fetchColumn() < 1) {
                throw new RegolaViolata(
                    "Credito esaurito per le lezioni di tipo {$slot['tipo']}"
                );
            }

            $massimo = self::impostazione('max_prenotazioni_aperte');
            $q = $pdo->prepare(
                "SELECT COUNT(*) FROM prenotazioni p
                   JOIN slot s ON s.id = p.slot_id
                  WHERE p.cliente_id = ? AND p.stato = 'prenotata' AND s.inizio > UTC_TIMESTAMP()"
            );
            $q->execute([$clienteId]);

            if ((int) $q->fetchColumn() >= $massimo) {
                throw new RegolaViolata("Hai gia' $massimo prenotazioni future aperte");
            }

            $q = $pdo->prepare('SELECT maestro_id FROM slot_maestri WHERE slot_id = ?');
            $q->execute([$slotId]);
            $candidati = $q->fetchAll(\PDO::FETCH_COLUMN);

            $maestroScelto = match (count($candidati)) {
                0       => null,
                1       => $candidati[0],
                default => in_array($maestroId, $candidati, true)
                    ? $maestroId
                    : throw new RegolaViolata('Scegli con quale maestro vuoi fare questa lezione'),
            };

            $id = Db::uuid();

            $pdo->prepare(
                'INSERT INTO prenotazioni (id, slot_id, cliente_id, maestro_id) VALUES (?, ?, ?, ?)'
            )->execute([$id, $slotId, $clienteId, $maestroScelto]);

            // Il credito si scala adesso, non alla presenza: altrimenti con un
            // credito solo si bloccherebbero quattro lezioni.
            $pdo->prepare(
                'INSERT INTO movimenti (cliente_id, tipo, delta, causale, prenotazione_id, autore_id)
                 VALUES (?, ?, -1, \'prenotazione\', ?, ?)'
            )->execute([$clienteId, $slot['tipo'], $id, $attoreId]);

            return $id;
        });
    }

    // ------------------------------------------------------------------
    // disdici
    // ------------------------------------------------------------------

    /**
     * Annulla una prenotazione.
     *
     * @return bool true se il credito e' stato restituito (disdetta in tempo)
     */
    public static function disdici(string $prenotazioneId, string $attoreId): bool
    {
        return Db::transazione(function (PDO $pdo) use ($prenotazioneId, $attoreId): bool {

            $q = $pdo->prepare(
                'SELECT p.*, s.inizio, s.tipo
                   FROM prenotazioni p JOIN slot s ON s.id = p.slot_id
                  WHERE p.id = ? FOR UPDATE'
            );
            $q->execute([$prenotazioneId]);
            $pren = $q->fetch();

            if (!$pren) {
                throw new RegolaViolata('Prenotazione inesistente');
            }

            if ($pren['cliente_id'] !== $attoreId && !self::eAdmin($attoreId)) {
                throw new RegolaViolata('Non puoi disdire la prenotazione di un altro cliente');
            }

            if ($pren['stato'] !== 'prenotata') {
                throw new RegolaViolata('Questa prenotazione non e\' piu\' disdicibile');
            }

            $utc    = new \DateTimeZone('UTC');
            $inizio = new \DateTimeImmutable($pren['inizio'], $utc);
            $adesso = new \DateTimeImmutable('now', $utc);

            if ($inizio <= $adesso) {
                throw new RegolaViolata('La lezione e\' gia\' iniziata');
            }

            $finestra = self::impostazione('finestra_disdetta_ore');
            $inTempo  = $adesso <= $inizio->modify("-{$finestra} hours");

            $pdo->prepare(
                "UPDATE prenotazioni SET stato = 'disdetta', disdetta_il = UTC_TIMESTAMP()
                  WHERE id = ?"
            )->execute([$prenotazioneId]);

            if ($inTempo) {
                $pdo->prepare(
                    'INSERT INTO movimenti (cliente_id, tipo, delta, causale, prenotazione_id, autore_id)
                     VALUES (?, ?, 1, \'disdetta_in_tempo\', ?, ?)'
                )->execute([$pren['cliente_id'], $pren['tipo'], $prenotazioneId, $attoreId]);
            }

            // Fuori finestra non si scrive nulla: il credito era gia' stato
            // scalato alla prenotazione e semplicemente non torna indietro.
            return $inTempo;
        });
    }

    // ------------------------------------------------------------------
    // presenze e crediti — riservate all'amministratore
    // ------------------------------------------------------------------

    public static function segnaPresenza(string $prenotazioneId, bool $presente, string $attoreId): void
    {
        if (!self::eAdmin($attoreId)) {
            throw new RegolaViolata('Riservato all\'amministratore');
        }

        $q = Db::pdo()->prepare(
            "UPDATE prenotazioni SET stato = ?
              WHERE id = ? AND stato IN ('prenotata', 'presente', 'assente')"
        );
        $q->execute([$presente ? 'presente' : 'assente', $prenotazioneId]);

        if ($q->rowCount() === 0) {
            // rowCount a 0 vale anche per un aggiornamento che non cambia
            // nulla, quindi si distingue leggendo lo stato attuale.
            $c = Db::pdo()->prepare('SELECT stato FROM prenotazioni WHERE id = ?');
            $c->execute([$prenotazioneId]);
            $stato = $c->fetchColumn();

            if ($stato === false || $stato === 'disdetta') {
                throw new RegolaViolata('Prenotazione inesistente o disdetta');
            }
        }
    }

    /**
     * Ricarica manuale concordata con il cliente.
     *
     * @return int id del movimento
     */
    public static function accredita(
        string  $clienteId,
        string  $tipo,
        int     $quantita,
        string  $attoreId,
        ?float  $importoEur = null,
        ?string $nota = null,
        string  $causale = 'acquisto'
    ): int {
        if (!self::eAdmin($attoreId)) {
            throw new RegolaViolata('Riservato all\'amministratore');
        }

        if ($quantita === 0) {
            throw new RegolaViolata('La quantita\' non puo\' essere zero');
        }

        if (!in_array($causale, ['acquisto', 'omaggio', 'rettifica'], true)) {
            throw new RegolaViolata('Causale non ammessa per una ricarica manuale');
        }

        if ($quantita < 0 && $causale !== 'rettifica') {
            throw new RegolaViolata('Solo una rettifica puo\' togliere crediti');
        }

        $pdo = Db::pdo();
        $pdo->prepare(
            'INSERT INTO movimenti (cliente_id, tipo, delta, causale, importo_eur, nota, autore_id)
             VALUES (?, ?, ?, ?, ?, ?, ?)'
        )->execute([$clienteId, $tipo, $quantita, $causale, $importoEur, $nota, $attoreId]);

        return (int) $pdo->lastInsertId();
    }
}
