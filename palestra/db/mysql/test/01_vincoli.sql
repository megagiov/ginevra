-- ============================================================================
--  Cosa il database garantisce da solo, su MySQL / MariaDB.
--
--  Le regole di prenotazione (24 ore, credito, tetto alle aperte) vivono nel
--  codice PHP e hanno la loro suite separata. Qui si verifica solo cio' che
--  nessun bug applicativo puo' aggirare, perche' sta sotto.
--
--  Uso:  mariadb studio_test < 01_vincoli.sql
-- ============================================================================

set names utf8mb4;

drop table if exists t_esiti;
create table t_esiti (
  id int auto_increment primary key,
  descrizione varchar(200),
  passato tinyint(1)
) engine=innodb;

-- Esegue uno statement che DEVE fallire. Se fallisce, il vincolo tiene.
-- Se passa, il vincolo non c'e' o non e' applicato: e' il caso di MySQL 5.7,
-- che accetta la sintassi dei CHECK e poi li ignora in silenzio.
delimiter //
create procedure t_errore(in descrizione varchar(200), in sql_da_provare text)
begin
  declare esploso tinyint default 0;
  declare continue handler for sqlexception set esploso = 1;

  set @s = sql_da_provare;
  prepare stmt from @s;
  execute stmt;
  deallocate prepare stmt;

  insert into t_esiti (descrizione, passato) values (descrizione, esploso);
end//

create procedure t_ok(in descrizione varchar(200), in condizione tinyint)
begin
  insert into t_esiti (descrizione, passato) values (descrizione, coalesce(condizione, 0));
end//
delimiter ;

-- ---------------------------------------------------------------------------
-- Prerequisito: i CHECK devono essere davvero applicati
-- ---------------------------------------------------------------------------

call t_errore('I vincoli CHECK sono applicati dal server',
  "insert into slot (id, inizio, fine, tipo, capienza)
   values ('chk-0000-0000-0000-000000000000', '2027-01-04 09:00:00',
           '2027-01-04 08:00:00', 'individuale', 1)");

-- ---------------------------------------------------------------------------
-- Dati di prova
-- ---------------------------------------------------------------------------

insert into utenti (id, email, nome, ruolo) values
  ('a1', 'admin@studio.test', 'Admin', 'admin'),
  ('c1', 'anna@test.it',      'Anna',  'cliente'),
  ('c2', 'bruno@test.it',     'Bruno', 'cliente');

-- Orari in UTC, come tutta la colonna
insert into slot (id, inizio, fine, tipo, capienza) values
  ('s1', '2027-03-01 09:00:00', '2027-03-01 10:00:00', 'individuale', 1),
  ('s2', '2027-03-01 18:00:00', '2027-03-01 19:00:00', 'gruppo',      4);

-- ---------------------------------------------------------------------------
-- 1. Una sala, al massimo un'individuale e un gruppo insieme
--
--    Con un secondo maestro disponibile, un'individuale e una di gruppo
--    possono girare in parallelo nello stesso orario. Due dello stesso
--    tipo insieme restano vietate: servirebbe un secondo maestro per lo
--    stesso tipo, caso che questa app non prevede.
-- ---------------------------------------------------------------------------

call t_errore('Due individuali non possono sovrapporsi',
  "insert into slot (id, inizio, fine, tipo, capienza)
   values ('x1', '2027-03-01 09:30:00', '2027-03-01 10:30:00', 'individuale', 1)");

call t_errore('Nemmeno un individuale che ne contiene un altro',
  "insert into slot (id, inizio, fine, tipo, capienza)
   values ('x2', '2027-03-01 08:00:00', '2027-03-01 12:00:00', 'individuale', 1)");

call t_errore('Nemmeno due individuali che iniziano insieme',
  "insert into slot (id, inizio, fine, tipo, capienza)
   values ('x3', '2027-03-01 09:00:00', '2027-03-01 09:30:00', 'individuale', 1)");

-- Un'individuale e un gruppo nello stesso orario: due maestri, due lezioni.
insert into slot (id, inizio, fine, tipo, capienza, note)
values ('x4', '2027-03-01 09:00:00', '2027-03-01 10:00:00', 'gruppo', 4, 'doppio-maestro');

call t_ok('Un gruppo puo\' coesistere con un individuale nello stesso orario',
  (select count(*) = 1 from slot where note = 'doppio-maestro'));

call t_errore('Ma due gruppi nello stesso orario restano vietati',
  "insert into slot (id, inizio, fine, tipo, capienza)
   values ('x5', '2027-03-01 18:30:00', '2027-03-01 19:30:00', 'gruppo', 4)");

-- Il confronto e' stretto su entrambi i lati: due lezioni dello stesso tipo
-- di fila devono restare possibili, altrimenti l'agenda e' inutilizzabile.
insert into slot (id, inizio, fine, tipo, capienza, note)
values ('s3', '2027-03-01 10:00:00', '2027-03-01 11:00:00', 'individuale', 1, 'adiacente');

call t_ok('Slot consecutivi dello stesso tipo (fine = inizio) restano ammessi',
  (select count(*) = 1 from slot where note = 'adiacente'));

call t_errore('Nemmeno spostando un individuale sopra un altro dello stesso tipo (update)',
  "update slot set inizio = '2027-03-01 10:30:00', fine = '2027-03-01 11:30:00'
    where id = 's1'");

-- ---------------------------------------------------------------------------
-- 2. Forma degli slot
-- ---------------------------------------------------------------------------

call t_errore('Il gruppo non puo superare i 4 posti',
  "insert into slot (id, inizio, fine, tipo, capienza)
   values ('x4', '2027-04-01 09:00:00', '2027-04-01 10:00:00', 'gruppo', 5)");

call t_errore('Un individuale ha esattamente un posto',
  "insert into slot (id, inizio, fine, tipo, capienza)
   values ('x5', '2027-04-02 09:00:00', '2027-04-02 10:00:00', 'individuale', 2)");

call t_errore('Uno slot non puo finire prima di iniziare',
  "insert into slot (id, inizio, fine, tipo, capienza)
   values ('x6', '2027-04-03 10:00:00', '2027-04-03 09:00:00', 'individuale', 1)");

-- ---------------------------------------------------------------------------
-- 3. Prenotazioni
-- ---------------------------------------------------------------------------

insert into prenotazioni (id, slot_id, cliente_id) values ('p1', 's2', 'c1');

call t_errore('Un cliente non puo occupare due posti nello stesso slot',
  "insert into prenotazioni (id, slot_id, cliente_id) values ('p2', 's2', 'c1')");

-- Dopo una disdetta il posto si libera e si puo' riprenotare: e' il
-- comportamento che l'indice unico parziale garantiva su PostgreSQL.
update prenotazioni set stato = 'disdetta', disdetta_il = now() where id = 'p1';

insert into prenotazioni (id, slot_id, cliente_id) values ('p3', 's2', 'c1');
call t_ok('Dopo la disdetta lo stesso cliente puo riprenotare',
  (select count(*) = 1 from prenotazioni where slot_id = 's2' and stato = 'prenotata'));

call t_ok('Le disdette non consumano posti',
  (select posti_liberi = 3 from slot_disponibilita where id = 's2'));

call t_errore('Una disdetta deve portare la sua data',
  "update prenotazioni set stato = 'disdetta' where id = 'p3'");

call t_errore('Una prenotazione viva non puo avere una data di disdetta',
  "update prenotazioni set disdetta_il = now() where id = 'p3'");

-- ---------------------------------------------------------------------------
-- 4. Registro crediti
-- ---------------------------------------------------------------------------

insert into movimenti (cliente_id, tipo, delta, causale, importo_eur, nota, autore_id)
values ('c1', 'individuale', 5, 'acquisto', 200.00, 'Pacchetto 5 lezioni', 'a1'),
       ('c1', 'gruppo',     10, 'acquisto', 250.00, 'Pacchetto 10 gruppo', 'a1');

insert into movimenti (cliente_id, tipo, delta, causale, prenotazione_id, autore_id)
values ('c1', 'gruppo', -1, 'prenotazione', 'p3', 'c1');

call t_ok('Il saldo e la somma dei movimenti (gruppo: 10 - 1 = 9)',
  (select saldo = 9 from saldi where cliente_id = 'c1' and tipo = 'gruppo'));

call t_errore('Un acquisto non puo togliere crediti',
  "insert into movimenti (cliente_id, tipo, delta, causale)
   values ('c1', 'gruppo', -3, 'acquisto')");

call t_errore('Una prenotazione non puo aggiungere crediti',
  "insert into movimenti (cliente_id, tipo, delta, causale, prenotazione_id)
   values ('c1', 'gruppo', 2, 'prenotazione', 'p3')");

call t_errore('Un movimento di prenotazione deve citare la prenotazione',
  "insert into movimenti (cliente_id, tipo, delta, causale)
   values ('c1', 'gruppo', -1, 'prenotazione')");

call t_errore('Un acquisto non puo citare una prenotazione',
  "insert into movimenti (cliente_id, tipo, delta, causale, prenotazione_id)
   values ('c1', 'gruppo', 1, 'acquisto', 'p3')");

call t_errore('Un movimento a zero non ha senso',
  "insert into movimenti (cliente_id, tipo, delta, causale)
   values ('c1', 'gruppo', 0, 'rettifica')");

-- Una rettifica e' l'unica causale che puo' andare in entrambe le direzioni.
insert into movimenti (cliente_id, tipo, delta, causale, nota, autore_id)
values ('c1', 'gruppo', -2, 'rettifica', 'Storno errore di battitura', 'a1');

call t_ok('Una rettifica negativa e ammessa e il saldo la recepisce (7)',
  (select saldo = 7 from saldi where cliente_id = 'c1' and tipo = 'gruppo'));

-- ---------------------------------------------------------------------------
-- 5. Integrita referenziale
-- ---------------------------------------------------------------------------

call t_errore('Non si prenota uno slot inesistente',
  "insert into prenotazioni (id, slot_id, cliente_id) values ('p9', 'inesistente', 'c1')");

call t_errore('Non si accredita un cliente inesistente',
  "insert into movimenti (cliente_id, tipo, delta, causale)
   values ('fantasma', 'gruppo', 1, 'acquisto')");

call t_errore('Non si cancella uno slot con prenotazioni',
  "delete from slot where id = 's2'");

call t_errore('Non si cancella un cliente con movimenti',
  "delete from utenti where id = 'c1'");

call t_errore('Due utenti non possono avere la stessa email',
  "insert into utenti (id, email, nome) values ('c9', 'anna@test.it', 'Doppione')");

-- ---------------------------------------------------------------------------
-- Esito
-- ---------------------------------------------------------------------------

select descrizione as 'NON PASSATO' from t_esiti where passato = 0;

select sum(passato)              as passati,
       sum(passato = 0)          as falliti,
       count(*)                  as totali
  from t_esiti;
