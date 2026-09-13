-- ============================================================================
--  Verifica delle regole di prenotazione.
--  Si esegue su un database dove sono gia' state applicate le migrazioni
--  e lo stub di auth.
-- ============================================================================

\set ON_ERROR_STOP on
set client_min_messages = notice;

grant usage on schema public to app_user;
grant select on all tables in schema public to app_user;
grant execute on all functions in schema public to app_user;

-- ---------------------------------------------------------------------------
-- Impalcatura minima per le asserzioni
-- ---------------------------------------------------------------------------

create table if not exists t_esiti (descrizione text, passato boolean);
truncate t_esiti;
-- serve anche ad app_user: la sezione RLS registra i propri esiti da quel ruolo
grant insert on t_esiti to app_user;

create or replace function t_ok(descrizione text, condizione boolean)
returns void language plpgsql as $$
begin
  insert into t_esiti values (descrizione, condizione);
  raise notice '%  %', case when condizione then 'PASS' else 'FAIL' end, descrizione;
end $$;

-- Esegue uno statement che DEVE fallire, e controlla che il messaggio parli
-- della cosa giusta (non basta che fallisca: deve fallire per il motivo atteso).
create or replace function t_errore(descrizione text, sql text, frammento text)
returns void language plpgsql as $$
begin
  execute sql;
  perform t_ok(descrizione || ' — atteso errore, non e'' arrivato', false);
exception when others then
  perform t_ok(
    descrizione || format('  [%s]', left(SQLERRM, 60)),
    position(lower(frammento) in lower(SQLERRM)) > 0
  );
end $$;

-- ---------------------------------------------------------------------------
-- Dati di prova
-- ---------------------------------------------------------------------------

insert into auth.users (id, email) values
  ('00000000-0000-0000-0000-0000000000a1', 'admin@studio.test'),
  ('00000000-0000-0000-0000-0000000000c1', 'anna@test.it'),
  ('00000000-0000-0000-0000-0000000000c2', 'bruno@test.it');

update profili set ruolo = 'admin', nome = 'Admin'
 where id = '00000000-0000-0000-0000-0000000000a1';
update profili set nome = 'Anna'  where id = '00000000-0000-0000-0000-0000000000c1';
update profili set nome = 'Bruno' where id = '00000000-0000-0000-0000-0000000000c2';

-- Slot: sempre 60 minuti, come da specifica
insert into slot (id, inizio, fine, tipo, capienza) values
  ('00000000-0000-0000-0000-00000000e001', now() + interval '3 days',  now() + interval '3 days'  + interval '60 min', 'individuale', 1),
  ('00000000-0000-0000-0000-00000000e002', now() + interval '4 days',  now() + interval '4 days'  + interval '60 min', 'gruppo',      4),
  ('00000000-0000-0000-0000-00000000e003', now() + interval '30 min',  now() + interval '90 min',                      'individuale', 1),
  ('00000000-0000-0000-0000-00000000e004', now() + interval '10 hours',now() + interval '11 hours',                    'individuale', 1),
  ('00000000-0000-0000-0000-00000000e005', now() + interval '5 days',  now() + interval '5 days'  + interval '60 min', 'individuale', 1),
  ('00000000-0000-0000-0000-00000000e006', now() + interval '6 days',  now() + interval '6 days'  + interval '60 min', 'individuale', 1),
  ('00000000-0000-0000-0000-00000000e007', now() + interval '7 days',  now() + interval '7 days'  + interval '60 min', 'individuale', 1),
  ('00000000-0000-0000-0000-00000000e008', now() + interval '8 days',  now() + interval '8 days'  + interval '60 min', 'individuale', 1);

-- ===========================================================================
--  1. Vincoli strutturali
-- ===========================================================================

select t_errore(
  'Una sala sola: due slot non possono sovrapporsi',
  $$insert into slot (inizio, fine, tipo, capienza)
    values (now() + interval '3 days' + interval '30 min',
            now() + interval '3 days' + interval '90 min', 'individuale', 1)$$,
  'sovrapposizioni');

-- Il vincolo usa tstzrange, che e' semiaperto: fine di uno = inizio del
-- successivo non e' una sovrapposizione. Senza questo, due lezioni di fila
-- sarebbero impossibili.
insert into slot (inizio, fine, tipo, capienza, note)
select s.fine, s.fine + interval '60 min', 'gruppo', 4, 'adiacente'
  from slot s where s.id = '00000000-0000-0000-0000-00000000e001';

select t_ok(
  'Slot adiacenti (fine = inizio) sono ammessi',
  (select count(*) = 1 from slot where note = 'adiacente'));

select t_errore(
  'Il gruppo non puo'' superare i 4 posti',
  $$insert into slot (inizio, fine, tipo, capienza)
    values (now() + interval '20 days', now() + interval '20 days' + interval '60 min', 'gruppo', 5)$$,
  'capienza_coerente');

select t_errore(
  'L''individuale ha esattamente un posto',
  $$insert into slot (inizio, fine, tipo, capienza)
    values (now() + interval '21 days', now() + interval '21 days' + interval '60 min', 'individuale', 2)$$,
  'capienza_coerente');

select t_errore(
  'Uno slot non puo'' finire prima di iniziare',
  $$insert into slot (inizio, fine, tipo, capienza)
    values (now() + interval '22 days', now() + interval '22 days' - interval '60 min', 'individuale', 1)$$,
  'durata_valida');

-- ===========================================================================
--  2. Registro crediti
-- ===========================================================================

set app.utente_id = '00000000-0000-0000-0000-0000000000a1';   -- admin

select accredita('00000000-0000-0000-0000-0000000000c1', 'individuale', 5, 200.00, 'Pacchetto 5 lezioni');
select accredita('00000000-0000-0000-0000-0000000000c1', 'gruppo',      10, 250.00, 'Pacchetto 10 gruppo');
select accredita('00000000-0000-0000-0000-0000000000c2', 'gruppo',       1,  30.00, 'Lezione singola');

select t_ok('Il saldo e'' la somma dei movimenti (Anna, individuale = 5)',
  (select saldo = 5 from saldi
    where cliente_id = '00000000-0000-0000-0000-0000000000c1' and tipo = 'individuale'));

select t_errore(
  'Un acquisto non puo'' avere quantita'' negativa',
  $$select accredita('00000000-0000-0000-0000-0000000000c1', 'gruppo', -3)$$,
  'rettifica');

select t_ok('Una rettifica negativa invece e'' ammessa',
  (select accredita('00000000-0000-0000-0000-0000000000c2', 'gruppo', -1, null,
                    'Storno errore di battitura', 'rettifica') is not null));

select t_ok('Dopo la rettifica il saldo di Bruno (gruppo) e'' 0',
  (select coalesce(saldo, 0) = 0 from saldi
    where cliente_id = '00000000-0000-0000-0000-0000000000c2' and tipo = 'gruppo'));

-- Il registro e' append-only per costruzione: nessun percorso applicativo
-- aggiorna o cancella. Qui si verifica che il vincolo di coerenza regga.
select t_errore(
  'Un movimento di prenotazione deve citare la prenotazione',
  $$insert into movimenti (cliente_id, tipo, delta, causale)
    values ('00000000-0000-0000-0000-0000000000c1', 'gruppo', -1, 'prenotazione')$$,
  'riferimento_coerente');

-- ===========================================================================
--  3. Prenotazione
-- ===========================================================================

set app.utente_id = '00000000-0000-0000-0000-0000000000c1';   -- Anna

select t_ok('Anna prenota un individuale',
  (select prenota('00000000-0000-0000-0000-00000000e001') is not null));

select t_ok('Il credito si scala subito (5 -> 4)',
  (select saldo = 4 from saldi
    where cliente_id = '00000000-0000-0000-0000-0000000000c1' and tipo = 'individuale'));

select t_errore(
  'Non si prenota due volte lo stesso slot',
  $$select prenota('00000000-0000-0000-0000-00000000e001')$$,
  'gia');

select t_errore(
  'Serve l''anticipo minimo di 2 ore',
  $$select prenota('00000000-0000-0000-0000-00000000e003')$$,
  'anticipo');

select t_errore(
  'Un cliente non puo'' prenotare per conto di un altro',
  $$select prenota('00000000-0000-0000-0000-00000000e002', '00000000-0000-0000-0000-0000000000c2')$$,
  'un altro cliente');

set app.utente_id = '00000000-0000-0000-0000-0000000000c2';   -- Bruno, saldo gruppo 0
select t_errore(
  'Bruno ha saldo gruppo azzerato e non puo'' prenotare',
  $$select prenota('00000000-0000-0000-0000-00000000e002')$$,
  'credito esaurito');

-- Tetto alle prenotazioni future aperte
set app.utente_id = '00000000-0000-0000-0000-0000000000c1';
select prenota('00000000-0000-0000-0000-00000000e005');
select prenota('00000000-0000-0000-0000-00000000e006');
select prenota('00000000-0000-0000-0000-00000000e007');   -- quarta aperta

select t_errore(
  'Massimo 4 prenotazioni future aperte per cliente',
  $$select prenota('00000000-0000-0000-0000-00000000e008')$$,
  'prenotazioni future');

-- ===========================================================================
--  4. Disdetta — la regola delle 24 ore
-- ===========================================================================

-- e005 e' fra 5 giorni: ampiamente dentro la finestra
select t_ok('Disdetta oltre 24h: il credito torna',
  (select disdici((select id from prenotazioni
                    where slot_id = '00000000-0000-0000-0000-00000000e005'
                      and cliente_id = '00000000-0000-0000-0000-0000000000c1'
                      and stato = 'prenotata')) = true));

select t_ok('Dopo la disdetta in tempo si puo'' riprenotare lo stesso slot',
  (select prenota('00000000-0000-0000-0000-00000000e005') is not null));

-- Anna e' al tetto delle 4 aperte: ne libera una per poter prenotare e004
select disdici((select id from prenotazioni
                 where slot_id = '00000000-0000-0000-0000-00000000e006'
                   and cliente_id = '00000000-0000-0000-0000-0000000000c1'
                   and stato = 'prenotata'));

-- e004 e' fra 10 ore: sotto la finestra di 24
select prenota('00000000-0000-0000-0000-00000000e004');

select t_ok('Disdetta sotto le 24h: il credito NON torna',
  (select disdici((select id from prenotazioni
                    where slot_id = '00000000-0000-0000-0000-00000000e004'
                      and cliente_id = '00000000-0000-0000-0000-0000000000c1'
                      and stato = 'prenotata')) = false));

select t_ok('I movimenti di restituzione sono solo quelli delle disdette in tempo (2)',
  (select count(*) = 2 from movimenti
    where cliente_id = '00000000-0000-0000-0000-0000000000c1'
      and causale = 'disdetta_in_tempo'));

select t_errore(
  'Una prenotazione gia'' disdetta non si disdice di nuovo',
  $$select disdici((select id from prenotazioni
                     where slot_id = '00000000-0000-0000-0000-00000000e004'
                       and stato = 'disdetta' limit 1))$$,
  'disdicibile');

-- ===========================================================================
--  5. Capienza del gruppo
-- ===========================================================================

set app.utente_id = '00000000-0000-0000-0000-0000000000a1';   -- admin accredita quattro persone
insert into auth.users (id, email) values
  ('00000000-0000-0000-0000-0000000000c3', 'carla@test.it'),
  ('00000000-0000-0000-0000-0000000000c4', 'dario@test.it'),
  ('00000000-0000-0000-0000-0000000000c5', 'elena@test.it');
select accredita('00000000-0000-0000-0000-0000000000c3', 'gruppo', 2);
select accredita('00000000-0000-0000-0000-0000000000c4', 'gruppo', 2);
select accredita('00000000-0000-0000-0000-0000000000c5', 'gruppo', 2);

-- L'admin prenota per conto dei clienti (la schermata "prenota per conto di")
select prenota('00000000-0000-0000-0000-00000000e002', '00000000-0000-0000-0000-0000000000c1');
select prenota('00000000-0000-0000-0000-00000000e002', '00000000-0000-0000-0000-0000000000c3');
select prenota('00000000-0000-0000-0000-00000000e002', '00000000-0000-0000-0000-0000000000c4');
select prenota('00000000-0000-0000-0000-00000000e002', '00000000-0000-0000-0000-0000000000c5');

select t_ok('Lo slot di gruppo risulta pieno (0 posti liberi)',
  (select posti_liberi = 0 from slot_disponibilita
    where id = '00000000-0000-0000-0000-00000000e002'));

select t_errore(
  'Il quinto posto in un gruppo da 4 viene rifiutato',
  $$select prenota('00000000-0000-0000-0000-00000000e002', '00000000-0000-0000-0000-0000000000c2')$$,
  'nessun posto');

-- ===========================================================================
--  6. Row Level Security — con un ruolo non privilegiato
-- ===========================================================================

set role app_user;

set app.utente_id = '00000000-0000-0000-0000-0000000000c1';   -- Anna
select t_ok('Anna vede solo le proprie prenotazioni',
  (select count(*) = 0 from prenotazioni
    where cliente_id <> '00000000-0000-0000-0000-0000000000c1'));

select t_ok('Anna vede solo i propri movimenti',
  (select count(*) = 0 from movimenti
    where cliente_id <> '00000000-0000-0000-0000-0000000000c1'));

select t_ok('Anna vede solo il proprio profilo',
  (select count(*) = 1 from profili));

select t_ok('Anna vede il calendario degli slot',
  (select count(*) > 0 from slot));

select t_errore(
  'Un cliente non puo'' scriversi crediti a mano',
  $$insert into movimenti (cliente_id, tipo, delta, causale)
    values ('00000000-0000-0000-0000-0000000000c1', 'individuale', 99, 'acquisto')$$,
  'denied');

select t_errore(
  'Un cliente non puo'' inserire prenotazioni scavalcando le regole',
  $$insert into prenotazioni (slot_id, cliente_id)
    values ('00000000-0000-0000-0000-00000000e008', '00000000-0000-0000-0000-0000000000c1')$$,
  'denied');

select t_errore(
  'Un cliente non puo'' pubblicare slot',
  $$insert into slot (inizio, fine, tipo, capienza)
    values (now() + interval '30 days', now() + interval '30 days' + interval '60 min', 'gruppo', 4)$$,
  'denied');

select t_errore(
  'Un cliente non puo'' accreditarsi con la funzione di ricarica',
  $$select accredita('00000000-0000-0000-0000-0000000000c1', 'individuale', 50)$$,
  'amministratore');

select t_errore(
  'Un cliente non puo'' segnare le presenze',
  $$select segna_presenza(
      (select id from prenotazioni limit 1), true)$$,
  'amministratore');

set app.utente_id = '00000000-0000-0000-0000-0000000000a1';   -- admin, sempre come app_user
select t_ok('L''amministratore vede le prenotazioni di tutti',
  (select count(distinct cliente_id) > 1 from prenotazioni));

reset role;

-- ===========================================================================
--  Esito
-- ===========================================================================

select count(*) filter (where passato)       as passati,
       count(*) filter (where not passato)   as falliti,
       count(*)                              as totali
  from t_esiti;

select descrizione from t_esiti where not passato;

do $$
declare n integer;
begin
  select count(*) into n from t_esiti where not passato;
  if n > 0 then
    raise exception '% test falliti', n;
  end if;
end $$;
