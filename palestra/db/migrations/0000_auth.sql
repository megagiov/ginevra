-- ============================================================================
--  Autenticazione — installazione autonoma (NAS), nessun servizio esterno.
--
--  Accesso senza password: il cliente inserisce la sua email, riceve un link
--  con un codice monouso, entra. Su cinquanta persone di eta' ed esperienza
--  diverse e' l'unico metodo che non genera chiamate di assistenza.
--
--  Lo schema si chiama "auth" e la funzione auth.uid() ha la stessa firma di
--  Supabase: se un domani il NAS non bastasse, il resto del database si
--  sposta su Supabase senza toccare una riga.
-- ============================================================================

create extension if not exists pgcrypto;

create schema if not exists auth;

create table if not exists auth.users (
  id                  uuid primary key default gen_random_uuid(),
  email               text unique,
  raw_user_meta_data  jsonb not null default '{}'::jsonb,
  creato_il           timestamptz not null default now(),
  ultimo_accesso_il   timestamptz
);

-- Codici di accesso monouso. Si conserva solo l'hash: chi legge il database
-- non puo' entrare nell'account di nessuno.
create table if not exists auth.codici_accesso (
  id          bigint generated always as identity primary key,
  user_id     uuid not null references auth.users(id) on delete cascade,
  hash_codice text not null,
  scade_il    timestamptz not null,
  usato_il    timestamptz,
  richiesto_da inet,
  creato_il   timestamptz not null default now()
);

create index if not exists codici_validi_idx
  on auth.codici_accesso (user_id, scade_il)
  where usato_il is null;

-- L'identita' della richiesta in corso. L'applicazione la imposta una volta
-- per richiesta, con SET LOCAL, dopo aver validato la sessione.
--
--   begin;
--   set local app.utente_id = '<uuid>';
--   select prenota('<slot>');
--   commit;
--
-- SET LOCAL e' essenziale: muore con la transazione, quindi una connessione
-- riusata dal pool non puo' ereditare l'identita' di chi l'ha usata prima.
create or replace function auth.uid()
returns uuid
language sql
stable
as $$ select nullif(current_setting('app.utente_id', true), '')::uuid $$;

-- Ruolo con cui l'applicazione si collega: nessun privilegio implicito, la
-- RLS si applica davvero. Il superuser la aggirerebbe, quindi l'app non deve
-- MAI collegarsi come superuser.
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'app_user') then
    create role app_user nologin;
  end if;
end
$$;
