<?php
declare(strict_types=1);

namespace Studio;

/**
 * Letture per le schermate: disponibilita', prenotazioni, movimenti.
 *
 * Sta separata da Regole perche' qui non si decide nulla, si legge soltanto.
 */
final class Calendario
{
    /**
     * Lezioni prenotabili nei prossimi giorni, raggruppate per data locale.
     *
     * Restituisce anche le lezioni piene: al cliente va mostrato che
     * quell'orario esiste ma e' occupato, altrimenti crede che tu non lavori
     * il martedi'.
     *
     * @return array<string, list<array>> chiave = data locale Y-m-d
     */
    public static function disponibilita(string $clienteId): array
    {
        $giorni   = Regole::impostazione('giorni_visibili');
        $anticipo = Regole::impostazione('anticipo_minimo_ore');

        $q = Db::pdo()->prepare(
            "SELECT d.*,
                    EXISTS (SELECT 1 FROM prenotazioni p
                             WHERE p.slot_id = d.id AND p.cliente_id = :cliente
                               AND p.stato <> 'disdetta') AS mia
               FROM slot_disponibilita d
              WHERE d.stato = 'aperto'
                AND d.inizio > UTC_TIMESTAMP() + INTERVAL :anticipo HOUR
                AND d.inizio < UTC_TIMESTAMP() + INTERVAL :giorni DAY
              ORDER BY d.inizio"
        );
        $q->bindValue(':cliente', $clienteId);
        $q->bindValue(':anticipo', $anticipo, \PDO::PARAM_INT);
        $q->bindValue(':giorni', $giorni, \PDO::PARAM_INT);
        $q->execute();

        $righe   = $q->fetchAll();
        $maestri = self::maestriPerSlot(array_column($righe, 'id'));

        $perGiorno = [];
        foreach ($righe as $slot) {
            $locale = Vista::locale($slot['inizio']);
            $perGiorno[$locale->format('Y-m-d')][] = $slot + [
                'locale'  => $locale,
                'maestri' => $maestri[$slot['id']] ?? [],
            ];
        }

        return $perGiorno;
    }

    /**
     * I maestri candidati per ciascuno slot, quelli tenuti anche se nel
     * frattempo disattivati: uno slot gia' pubblicato resta valido cosi'
     * com'e'.
     *
     * @param list<string> $slotIds
     * @return array<string, list<array{id:string,nome:string}>>
     */
    private static function maestriPerSlot(array $slotIds): array
    {
        if ($slotIds === []) {
            return [];
        }

        $segnaposto = implode(',', array_fill(0, count($slotIds), '?'));
        $q = Db::pdo()->prepare(
            "SELECT sm.slot_id, m.id, m.nome FROM slot_maestri sm
               JOIN maestri m ON m.id = sm.maestro_id
              WHERE sm.slot_id IN ($segnaposto)
              ORDER BY m.nome"
        );
        $q->execute($slotIds);

        $perSlot = [];
        foreach ($q->fetchAll() as $r) {
            $perSlot[$r['slot_id']][] = ['id' => $r['id'], 'nome' => $r['nome']];
        }
        return $perSlot;
    }

    /** @return list<array> prenotazioni future, dalla piu' vicina */
    public static function prossime(string $clienteId): array
    {
        $q = Db::pdo()->prepare(
            "SELECT p.id, p.stato, s.inizio, s.fine, s.tipo, s.capienza,
                    m.nome AS maestro_nome
               FROM prenotazioni p JOIN slot s ON s.id = p.slot_id
               LEFT JOIN maestri m ON m.id = p.maestro_id
              WHERE p.cliente_id = ? AND p.stato = 'prenotata'
                AND s.inizio > UTC_TIMESTAMP()
              ORDER BY s.inizio"
        );
        $q->execute([$clienteId]);

        $finestra = Regole::impostazione('finestra_disdetta_ore');
        $adesso   = new \DateTimeImmutable('now', new \DateTimeZone('UTC'));

        return array_map(function (array $p) use ($finestra, $adesso): array {
            $inizio = new \DateTimeImmutable($p['inizio'], new \DateTimeZone('UTC'));
            $p['locale']            = Vista::locale($p['inizio']);
            $p['disdetta_gratuita'] = $adesso <= $inizio->modify("-{$finestra} hours");
            $p['scadenza_disdetta'] = Vista::locale(
                $inizio->modify("-{$finestra} hours")->format('Y-m-d H:i:s')
            );
            return $p;
        }, $q->fetchAll());
    }

    /** @return list<array> lezioni gia' svolte, dalla piu' recente */
    public static function passate(string $clienteId, int $quante = 20): array
    {
        $q = Db::pdo()->prepare(
            "SELECT p.id, p.stato, s.inizio, s.tipo
               FROM prenotazioni p JOIN slot s ON s.id = p.slot_id
              WHERE p.cliente_id = ? AND s.inizio <= UTC_TIMESTAMP()
                AND p.stato <> 'disdetta'
              ORDER BY s.inizio DESC
              LIMIT $quante"
        );
        $q->execute([$clienteId]);

        return array_map(function (array $p): array {
            $p['locale'] = Vista::locale($p['inizio']);
            return $p;
        }, $q->fetchAll());
    }

    /** Il registro dei crediti, cosi' com'e': e' la risposta a "perche'?". */
    public static function movimenti(string $clienteId, int $quanti = 50): array
    {
        $q = Db::pdo()->prepare(
            "SELECT m.*, s.inizio AS lezione_inizio
               FROM movimenti m
               LEFT JOIN prenotazioni p ON p.id = m.prenotazione_id
               LEFT JOIN slot s ON s.id = p.slot_id
              WHERE m.cliente_id = ?
              ORDER BY m.creato_il DESC, m.id DESC
              LIMIT $quanti"
        );
        $q->execute([$clienteId]);

        return array_map(function (array $m): array {
            $m['locale'] = Vista::locale($m['creato_il']);
            $m['etichetta'] = match ($m['causale']) {
                'acquisto'          => 'Ricarica',
                'omaggio'           => 'Lezione omaggio',
                'prenotazione'      => 'Lezione prenotata',
                'disdetta_in_tempo' => 'Disdetta entro i termini',
                'rettifica'         => 'Rettifica',
            };
            return $m;
        }, $q->fetchAll());
    }

    /** @return array{individuale:int, gruppo:int} */
    public static function saldi(string $clienteId): array
    {
        return [
            'individuale' => Regole::saldo($clienteId, 'individuale'),
            'gruppo'      => Regole::saldo($clienteId, 'gruppo'),
        ];
    }

    /**
     * Il piano scritto dall'amministratore per questo cliente, se c'e'.
     *
     * @return array{alimentare:?string, allenamento:?string, aggiornato_il:?\DateTimeImmutable}|null
     *         null se non e' mai stato scritto nulla — diverso da un piano
     *         vuoto, che invece si mostrerebbe come "nessun piano ancora".
     */
    public static function piano(string $clienteId): ?array
    {
        $q = Db::pdo()->prepare(
            'SELECT piano_alimentare, piano_allenamento, piano_aggiornato_il
               FROM utenti WHERE id = ?'
        );
        $q->execute([$clienteId]);
        $riga = $q->fetch();

        if (!$riga || $riga['piano_aggiornato_il'] === null) {
            return null;
        }

        return [
            'alimentare'    => $riga['piano_alimentare'],
            'allenamento'   => $riga['piano_allenamento'],
            'aggiornato_il' => Vista::locale($riga['piano_aggiornato_il']),
        ];
    }
}
