-- ============================================================================
--  Maestri: quando sono in due (o piu'), il cliente sceglie con chi vuole
--  fare lezione.
--
--  Uno slot puo' avere piu' maestri "candidati" (chi e' libero a
--  quell'ora); la prenotazione fissa quale dei due l'ha presa in carico.
--  Con un solo maestro candidato non c'e' scelta da fare: si assegna da
--  solo, senza mostrare nulla al cliente. Con zero, il campo resta vuoto
--  come e' sempre stato: chi non traccia i maestri non vede differenza.
-- ============================================================================

set names utf8mb4;

create table maestri (
  id        char(36)     not null primary key,
  nome      varchar(120) not null,
  attivo    tinyint(1)   not null default 1,
  creato_il datetime     not null default current_timestamp
) engine=innodb default charset=utf8mb4;

create table slot_maestri (
  slot_id    char(36) not null,
  maestro_id char(36) not null,

  primary key (slot_id, maestro_id),

  constraint slot_maestri_slot_fk foreign key (slot_id)
    references slot(id) on delete cascade,
  constraint slot_maestri_maestro_fk foreign key (maestro_id)
    references maestri(id) on delete restrict
) engine=innodb default charset=utf8mb4;

alter table prenotazioni
  add column maestro_id char(36) null after cliente_id,
  add constraint prenotazioni_maestro_fk foreign key (maestro_id)
    references maestri(id) on delete restrict;
