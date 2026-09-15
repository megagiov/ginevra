-- ============================================================================
--  Due maestri, due lezioni in parallelo.
--
--  Finora la sala ammetteva una lezione alla volta, di qualsiasi tipo:
--  un secondo maestro rende falsa quell'ipotesi. Ora la regola e' "mai due
--  lezioni dello STESSO tipo sovrapposte" — un'individuale e un gruppo
--  possono girare nello stesso orario (un maestro segue l'una, l'altro
--  l'altra), ma due individuali o due gruppi insieme restano vietati:
--  quello servirebbe un secondo maestro per lo stesso tipo, caso che questa
--  app non prevede.
-- ============================================================================

set names utf8mb4;

alter table slot drop index slot_inizio_unico;
alter table slot add unique key slot_inizio_tipo_unico (inizio, tipo);

drop trigger slot_no_sovrapposizione_ins;
drop trigger slot_no_sovrapposizione_upd;

delimiter //

create trigger slot_no_sovrapposizione_ins
before insert on slot
for each row
begin
  if exists (select 1 from slot s
              where s.tipo = new.tipo
                and s.inizio < new.fine and s.fine > new.inizio) then
    signal sqlstate '45000'
      set message_text = 'Sovrapposizione con un altro slot dello stesso tipo';
  end if;
end//

create trigger slot_no_sovrapposizione_upd
before update on slot
for each row
begin
  if exists (select 1 from slot s
              where s.id <> new.id
                and s.tipo = new.tipo
                and s.inizio < new.fine and s.fine > new.inizio) then
    signal sqlstate '45000'
      set message_text = 'Sovrapposizione con un altro slot dello stesso tipo';
  end if;
end//

delimiter ;
