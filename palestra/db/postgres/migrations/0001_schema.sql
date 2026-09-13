-- ============================================================================
--  Studio PT — schema iniziale
--
--  Modello: una sala, uno slot alla volta, lezioni da 60 minuti individuali
--  o di gruppo (max 4). I crediti sono gestiti a mano dall'amministratore e
--  vivono in un registro di movimenti: il saldo non e' mai un contatore
--  modificabile, e' sempre la somma dei movimenti.
-- ============================================================================

create extension if not exists btree_gist;   -- per il vincolo anti-sovrapposizione
create extension if not exists pgcrypto;     -- gen_random_uuid()

-- ---------------------------------------------------------------------------
-- Tipi
-- ---------------------------------------------------------------------------

create type tipo_lezione       as enum ('individuale', 'gruppo');
create type ruolo_utente       as enum ('cliente', 'admin');
create type stato_slot         as enum ('aperto', 'chiuso');
create type stato_prenotazione as enum ('prenotata', 'presente', 'assente', 'disdetta');

-- Causali del registro crediti. Ogni riga di movimenti ne porta una: e' cio'
-- che permette di rispondere a "perche' ho un credito in meno?".
create type causale_movimento as enum (
  'acquisto',            -- ricarica manuale dell'amministratore  (+)
  'omaggio',             -- lezione regalata / prova              (+)
  'prenotazione',        -- scalo alla prenotazione               (-)
  'disdetta_in_tempo',   -- restituzione entro la finestra        (+)
  'rettifica'            -- correzione manuale, in entrambi i versi
);

-- ---------------------------------------------------------------------------
-- Impostazioni: le regole di prenotazione vivono qui, non nel codice, cosi'
-- si cambiano senza un rilascio.
-- ---------------------------------------------------------------------------

create table impostazioni (
  chiave  text primary key,
  valore  integer not null,
  nota    text
);

insert into impostazioni (chiave, valore, nota) values
  ('finestra_disdetta_ore',   24, 'Oltre questa soglia la disdetta restituisce il credito'),
  ('anticipo_minimo_ore',      2, 'Anticipo minimo per prenotare uno slot'),
  ('max_prenotazioni_aperte',  4, 'Prenotazioni future contemporanee per cliente'),
  ('giorni_visibili',         14, 'Finestra di slot mostrata al cliente');

create or replace function impostazione(p_chiave text)
returns integer
language sql
stable
as $$ select valore from impostazioni where chiave = p_chiave $$;

-- ---------------------------------------------------------------------------
-- Profili — estende auth.users di Supabase (stessa chiave primaria)
-- ---------------------------------------------------------------------------

create table profili (
  id                   uuid primary key references auth.users(id) on delete cascade,
  ruolo                ruolo_utente not null default 'cliente',
  nome                 text not null,
  email                text,
  telefono             text,
  note                 text,
  parq_compilato_il    timestamptz,
  consenso_privacy_il  timestamptz,
  attivo               boolean not null default true,
  creato_il            timestamptz not null default now()
);

create index profili_ruolo_idx on profili (ruolo) where attivo;

-- Helper usato da tutte le policy. SECURITY DEFINER perche' deve poter leggere
-- profili anche quando la RLS su profili non lo permetterebbe ancora.
create or replace function e_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from profili
    where id = auth.uid() and ruolo = 'admin' and attivo
  )
$$;

-- ---------------------------------------------------------------------------
-- Slot — la disponibilita' pubblicata dall'amministratore.
--
-- Con una sala sola lo slot *e'* la sala: due slot non possono sovrapporsi,
-- e il vincolo lo garantisce il database, non il codice applicativo.
-- ---------------------------------------------------------------------------

create table slot (
  id         uuid primary key default gen_random_uuid(),
  inizio     timestamptz not null,
  fine       timestamptz not null,
  tipo       tipo_lezione not null,
  capienza   smallint not null,
  stato      stato_slot not null default 'aperto',
  note       text,
  creato_il  timestamptz not null default now(),

  constraint slot_durata_valida
    check (fine > inizio),

  -- Un individuale ha un posto; un gruppo da due a quattro. Se un giorno la
  -- capienza massima cambia, si cambia qui e in nessun altro punto.
  constraint slot_capienza_coerente check (
    (tipo = 'individuale' and capienza = 1) or
    (tipo = 'gruppo'      and capienza between 2 and 4)
  ),

  -- Una sala: nessuna sovrapposizione temporale, mai, per nessun motivo.
  constraint slot_niente_sovrapposizioni
    exclude using gist (tstzrange(inizio, fine) with &&)
);

create index slot_inizio_idx on slot (inizio) where stato = 'aperto';

-- ---------------------------------------------------------------------------
-- Prenotazioni
-- ---------------------------------------------------------------------------

create table prenotazioni (
  id           uuid primary key default gen_random_uuid(),
  slot_id      uuid not null references slot(id) on delete restrict,
  cliente_id   uuid not null references profili(id) on delete restrict,
  stato        stato_prenotazione not null default 'prenotata',
  creata_il    timestamptz not null default now(),
  disdetta_il  timestamptz,

  constraint disdetta_coerente check (
    (stato = 'disdetta' and disdetta_il is not null) or
    (stato <> 'disdetta' and disdetta_il is null)
  )
);

-- Un cliente puo' occupare un posto solo per slot, ma dopo una disdetta deve
-- poter riprenotare: l'unicita' vale solo sulle prenotazioni non disdette.
create unique index prenotazione_attiva_unica
  on prenotazioni (slot_id, cliente_id)
  where stato <> 'disdetta';

create index prenotazioni_cliente_idx on prenotazioni (cliente_id, creata_il desc);
create index prenotazioni_slot_idx    on prenotazioni (slot_id) where stato <> 'disdetta';

-- ---------------------------------------------------------------------------
-- Movimenti — il registro dei crediti.
--
-- Append-only per costruzione: non esiste nessuna funzione che aggiorni o
-- cancelli una riga. Una correzione e' un movimento di segno opposto, cosi'
-- lo storico resta leggibile anche quando si sbaglia.
-- ---------------------------------------------------------------------------

create table movimenti (
  id               bigint generated always as identity primary key,
  cliente_id       uuid not null references profili(id) on delete restrict,
  tipo             tipo_lezione not null,
  delta            smallint not null,
  causale          causale_movimento not null,
  prenotazione_id  uuid references prenotazioni(id) on delete restrict,
  importo_eur      numeric(8,2),
  nota             text,
  autore_id        uuid references profili(id),
  creato_il        timestamptz not null default now(),

  constraint delta_non_nullo check (delta <> 0),

  -- Le causali legate a una prenotazione devono citarla; le altre no.
  constraint riferimento_coerente check (
    (causale in ('prenotazione', 'disdetta_in_tempo') and prenotazione_id is not null) or
    (causale in ('acquisto', 'omaggio', 'rettifica')  and prenotazione_id is null)
  ),

  -- Il segno non e' libero: un acquisto non puo' togliere crediti.
  constraint segno_coerente check (
    (causale in ('acquisto', 'omaggio', 'disdetta_in_tempo') and delta > 0) or
    (causale = 'prenotazione'                                and delta < 0) or
    (causale = 'rettifica')
  )
);

create index movimenti_cliente_idx on movimenti (cliente_id, creato_il desc);

-- Il saldo non e' un campo: e' una somma. Sempre ricostruibile, mai divergente.
create view saldi as
  select cliente_id,
         tipo,
         coalesce(sum(delta), 0)::integer as saldo
  from movimenti
  group by cliente_id, tipo;

-- Posti liberi per slot, usata dall'elenco lato cliente.
create view slot_disponibilita as
  select s.*,
         s.capienza - count(p.id) filter (where p.stato <> 'disdetta') as posti_liberi
  from slot s
  left join prenotazioni p on p.slot_id = s.id
  group by s.id;
