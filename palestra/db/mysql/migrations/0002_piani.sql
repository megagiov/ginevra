-- ============================================================================
--  Piano alimentare e di allenamento a casa, per cliente.
--
--  Testo libero scritto dall'amministratore, visibile solo al cliente a cui
--  appartiene. Niente storico: e' un consiglio corrente, non un registro —
--  se cambia, il vecchio testo non serve piu' a nessuno.
-- ============================================================================

set names utf8mb4;

alter table utenti
  add column piano_alimentare    text     null after note,
  add column piano_allenamento   text     null after piano_alimentare,
  add column piano_aggiornato_il datetime null after piano_allenamento;
