-- ============================================================================
--  Studio PT — schema MySQL / MariaDB  (hosting Aruba Linux, PHP 8.3)
--
--  Porting dallo schema PostgreSQL. Le decisioni di progetto sono le stesse:
--  una sala, lezioni da 60 minuti, gruppi fino a 4, crediti gestiti a mano e
--  saldo calcolato come somma di un registro di movimenti.
--
--  ORARI: tutte le colonne DATETIME contengono UTC, senza eccezioni.
--  MySQL non memorizza il fuso: la conversione a Europe/Rome avviene solo
--  quando si mostra un orario. Mescolare i due significa ritrovarsi lezioni
--  fantasma nelle due notti del cambio d'ora.
-- ============================================================================

set names utf8mb4;

-- ---------------------------------------------------------------------------
-- Impostazioni: le regole si cambiano qui, senza ricaricare il codice
-- ---------------------------------------------------------------------------

create table impostazioni (
  chiave  varchar(60)  not null primary key,
  valore  int          not null,
  nota    varchar(255) null
) engine=innodb default charset=utf8mb4;

insert into impostazioni (chiave, valore, nota) values
  ('finestra_disdetta_ore',   24, 'Oltre questa soglia la disdetta restituisce il credito'),
  ('anticipo_minimo_ore',      2, 'Anticipo minimo per prenotare uno slot'),
  ('max_prenotazioni_aperte',  4, 'Prenotazioni future contemporanee per cliente'),
  ('giorni_visibili',         14, 'Finestra di slot mostrata al cliente');

-- ---------------------------------------------------------------------------
-- Utenti
--
--  Su Postgres erano due tabelle (auth.users + profili) perche' Supabase
--  possiede la prima. Qui l'applicazione possiede tutto: una tabella sola.
-- ---------------------------------------------------------------------------

create table utenti (
  id                   char(36)     not null primary key,
  email                varchar(190) not null,
  nome                 varchar(120) not null,
  ruolo                enum('cliente','admin') not null default 'cliente',
  telefono             varchar(40)  null,
  note                 text         null,
  parq_compilato_il    datetime     null,
  consenso_privacy_il  datetime     null,
  attivo               tinyint(1)   not null default 1,
  creato_il            datetime     not null default current_timestamp,
  ultimo_accesso_il    datetime     null,

  unique key utenti_email_unica (email),
  key utenti_ruolo_idx (ruolo, attivo)
) engine=innodb default charset=utf8mb4;

-- ---------------------------------------------------------------------------
-- Accesso senza password
--
--  Del codice inviato per email si conserva solo l'impronta: chi leggesse il
--  database non potrebbe entrare nell'account di nessuno.
-- ---------------------------------------------------------------------------

create table codici_accesso (
  id            bigint unsigned not null auto_increment primary key,
  utente_id     char(36)    not null,
  hash_codice   char(64)    not null,
  scade_il      datetime    not null,
  usato_il      datetime    null,
  ip_richiesta  varchar(45) null,
  creato_il     datetime    not null default current_timestamp,

  key codici_utente_idx (utente_id, scade_il),
  unique key codici_hash_unico (hash_codice),
  constraint codici_utente_fk foreign key (utente_id)
    references utenti(id) on delete cascade
) engine=innodb default charset=utf8mb4;

-- Sessioni persistenti: il cliente non deve rifare l'accesso a ogni apertura.
-- Anche qui si salva l'impronta del token, mai il token.
create table sessioni (
  id             char(64) not null primary key,
  utente_id      char(36) not null,
  creata_il      datetime not null default current_timestamp,
  ultimo_uso_il  datetime null,
  scade_il       datetime not null,
  user_agent     varchar(255) null,

  key sessioni_utente_idx (utente_id),
  constraint sessioni_utente_fk foreign key (utente_id)
    references utenti(id) on delete cascade
) engine=innodb default charset=utf8mb4;

-- ---------------------------------------------------------------------------
-- Slot — la disponibilita' pubblicata dall'amministratore
-- ---------------------------------------------------------------------------

create table slot (
  id         char(36) not null primary key,
  inizio     datetime not null,
  fine       datetime not null,
  tipo       enum('individuale','gruppo') not null,
  capienza   tinyint unsigned not null,
  stato      enum('aperto','chiuso') not null default 'aperto',
  note       varchar(255) null,
  creato_il  datetime not null default current_timestamp,

  -- Due lezioni non possono iniziare allo stesso minuto. Da sola non basta a
  -- escludere le sovrapposizioni parziali: a quelle pensano i trigger.
  unique key slot_inizio_unico (inizio),
  key slot_calendario_idx (inizio, stato),

  constraint slot_durata_valida check (fine > inizio),

  constraint slot_capienza_coerente check (
    (tipo = 'individuale' and capienza = 1) or
    (tipo = 'gruppo'      and capienza between 2 and 4)
  )
) engine=innodb default charset=utf8mb4;

-- MySQL non ha i vincoli di esclusione di PostgreSQL, ma un trigger puo'
-- leggere la propria tabella: la garanzia resta nel database invece di
-- scendere nel codice applicativo, dove sarebbe aggirabile da qualunque bug.
--
-- Il confronto e' stretto su entrambi i lati (inizio < fine_nuovo AND
-- fine > inizio_nuovo): due slot consecutivi, dove la fine di uno coincide
-- con l'inizio dell'altro, restano ammessi.

delimiter //

create trigger slot_no_sovrapposizione_ins
before insert on slot
for each row
begin
  if exists (select 1 from slot s
              where s.inizio < new.fine and s.fine > new.inizio) then
    signal sqlstate '45000'
      set message_text = 'Sovrapposizione con un altro slot della sala';
  end if;
end//

create trigger slot_no_sovrapposizione_upd
before update on slot
for each row
begin
  if exists (select 1 from slot s
              where s.id <> new.id
                and s.inizio < new.fine and s.fine > new.inizio) then
    signal sqlstate '45000'
      set message_text = 'Sovrapposizione con un altro slot della sala';
  end if;
end//

delimiter ;

-- ---------------------------------------------------------------------------
-- Prenotazioni
-- ---------------------------------------------------------------------------

create table prenotazioni (
  id           char(36) not null primary key,
  slot_id      char(36) not null,
  cliente_id   char(36) not null,
  stato        enum('prenotata','presente','assente','disdetta') not null default 'prenotata',
  creata_il    datetime not null default current_timestamp,
  disdetta_il  datetime null,

  -- PostgreSQL aveva un indice unico parziale. MySQL non li ha, ma una
  -- colonna generata ottiene lo stesso effetto: vale 1 quando la
  -- prenotazione e' viva e NULL quando e' disdetta, e nell'indice unico i
  -- NULL non fanno duplicato. Cosi' un cliente occupa un posto solo per
  -- slot, ma dopo una disdetta puo' riprenotare.
  attiva tinyint unsigned generated always as
    (case when stato <> 'disdetta' then 1 else null end) stored,

  unique key prenotazione_attiva_unica (slot_id, cliente_id, attiva),
  key prenotazioni_cliente_idx (cliente_id, creata_il),
  key prenotazioni_slot_idx (slot_id, attiva),

  constraint disdetta_coerente check (
    (stato =  'disdetta' and disdetta_il is not null) or
    (stato <> 'disdetta' and disdetta_il is null)
  ),

  constraint prenotazioni_slot_fk foreign key (slot_id)
    references slot(id) on delete restrict,
  constraint prenotazioni_cliente_fk foreign key (cliente_id)
    references utenti(id) on delete restrict
) engine=innodb default charset=utf8mb4;

-- ---------------------------------------------------------------------------
-- Movimenti — il registro dei crediti
--
--  Nessuna colonna "lezioni_residue" da nessuna parte: il saldo e' la somma
--  dei delta. Una correzione e' un movimento di segno opposto, mai una
--  modifica: lo storico resta leggibile anche quando si sbaglia.
-- ---------------------------------------------------------------------------

create table movimenti (
  id               bigint unsigned not null auto_increment primary key,
  cliente_id       char(36) not null,
  tipo             enum('individuale','gruppo') not null,
  delta            smallint not null,
  causale          enum('acquisto','omaggio','prenotazione','disdetta_in_tempo','rettifica') not null,
  prenotazione_id  char(36) null,
  importo_eur      decimal(8,2) null,
  nota             varchar(255) null,
  autore_id        char(36) null,
  creato_il        datetime not null default current_timestamp,

  key movimenti_cliente_idx (cliente_id, tipo),
  key movimenti_cronologia_idx (cliente_id, creato_il),

  constraint delta_non_nullo check (delta <> 0),

  -- Le causali legate a una prenotazione devono citarla; le altre no.
  constraint riferimento_coerente check (
    (causale in ('prenotazione','disdetta_in_tempo') and prenotazione_id is not null) or
    (causale in ('acquisto','omaggio','rettifica')   and prenotazione_id is null)
  ),

  -- Il segno non e' libero: un acquisto non puo' togliere crediti, e solo
  -- una rettifica puo' andare in entrambe le direzioni.
  constraint segno_coerente check (
    (causale in ('acquisto','omaggio','disdetta_in_tempo') and delta > 0) or
    (causale = 'prenotazione'                              and delta < 0) or
    (causale = 'rettifica')
  ),

  constraint movimenti_cliente_fk foreign key (cliente_id)
    references utenti(id) on delete restrict,
  constraint movimenti_prenotazione_fk foreign key (prenotazione_id)
    references prenotazioni(id) on delete restrict
) engine=innodb default charset=utf8mb4;

-- ---------------------------------------------------------------------------
-- Viste
-- ---------------------------------------------------------------------------

create view saldi as
  select cliente_id,
         tipo,
         coalesce(sum(delta), 0) as saldo
    from movimenti
   group by cliente_id, tipo;

create view slot_disponibilita as
  select s.id, s.inizio, s.fine, s.tipo, s.capienza, s.stato, s.note,
         s.capienza - coalesce(
           (select count(*) from prenotazioni p
             where p.slot_id = s.id and p.stato <> 'disdetta'), 0) as posti_liberi
    from slot s;
