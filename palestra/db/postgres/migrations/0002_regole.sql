-- ============================================================================
--  Studio PT — regole di prenotazione e sicurezza
--
--  Nessuna scrittura su prenotazioni e movimenti passa direttamente dal
--  client: non esiste una policy di INSERT su quelle tabelle. Si entra solo
--  da queste funzioni, che applicano le regole in transazione. Cosi' la
--  regola delle 24 ore non e' una cortesia dell'interfaccia, e' un fatto.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Profilo automatico al primo accesso (magic link)
-- ---------------------------------------------------------------------------

create or replace function crea_profilo_al_signup()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into profili (id, nome, email)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'nome', split_part(new.email, '@', 1)),
    new.email
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

create trigger profilo_al_signup
  after insert on auth.users
  for each row execute function crea_profilo_al_signup();

-- ---------------------------------------------------------------------------
-- prenota() — l'unica via per occupare un posto
-- ---------------------------------------------------------------------------

create or replace function prenota(p_slot_id uuid, p_cliente_id uuid default null)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_cliente  uuid := coalesce(p_cliente_id, auth.uid());
  v_slot     slot;
  v_occupati integer;
  v_saldo    integer;
  v_aperte   integer;
  v_id       uuid;
begin
  if auth.uid() is null then
    raise exception 'Accesso non autenticato' using errcode = '28000';
  end if;

  if v_cliente <> auth.uid() and not e_admin() then
    raise exception 'Non puoi prenotare per un altro cliente' using errcode = '42501';
  end if;

  -- Lock sul cliente PRIMA che sullo slot (ordine costante = niente deadlock).
  -- Serializza le prenotazioni di questa persona: senza, due richieste
  -- simultanee su slot diversi spenderebbero lo stesso ultimo credito.
  perform 1 from profili where id = v_cliente and attivo for update;
  if not found then
    raise exception 'Cliente inesistente o non attivo' using errcode = '23503';
  end if;

  -- Lock sullo slot: serializza la corsa all'ultimo posto del gruppo.
  select * into v_slot from slot where id = p_slot_id for update;
  if not found then
    raise exception 'Slot inesistente' using errcode = '23503';
  end if;

  if v_slot.stato <> 'aperto' then
    raise exception 'Questo slot non e'' prenotabile' using errcode = 'P0001';
  end if;

  if v_slot.inizio < now() + make_interval(hours => impostazione('anticipo_minimo_ore')) then
    raise exception 'Troppo tardi per prenotare: servono almeno % ore di anticipo',
      impostazione('anticipo_minimo_ore') using errcode = 'P0001';
  end if;

  if exists (select 1 from prenotazioni
             where slot_id = p_slot_id and cliente_id = v_cliente and stato <> 'disdetta') then
    raise exception 'Hai gia'' un posto in questo slot' using errcode = 'P0001';
  end if;

  select count(*) into v_occupati from prenotazioni
   where slot_id = p_slot_id and stato <> 'disdetta';

  if v_occupati >= v_slot.capienza then
    raise exception 'Nessun posto libero in questo slot' using errcode = 'P0001';
  end if;

  select coalesce(sum(delta), 0) into v_saldo from movimenti
   where cliente_id = v_cliente and tipo = v_slot.tipo;

  if v_saldo < 1 then
    raise exception 'Credito esaurito per le lezioni di tipo %', v_slot.tipo
      using errcode = 'P0001';
  end if;

  select count(*) into v_aperte
    from prenotazioni p join slot s on s.id = p.slot_id
   where p.cliente_id = v_cliente and p.stato = 'prenotata' and s.inizio > now();

  if v_aperte >= impostazione('max_prenotazioni_aperte') then
    raise exception 'Hai gia'' % prenotazioni future aperte',
      impostazione('max_prenotazioni_aperte') using errcode = 'P0001';
  end if;

  insert into prenotazioni (slot_id, cliente_id)
  values (p_slot_id, v_cliente)
  returning id into v_id;

  -- Il credito si scala adesso, non alla presenza: altrimenti con un credito
  -- solo si bloccherebbero quattro slot.
  insert into movimenti (cliente_id, tipo, delta, causale, prenotazione_id, autore_id)
  values (v_cliente, v_slot.tipo, -1, 'prenotazione', v_id, auth.uid());

  return v_id;
end;
$$;

-- ---------------------------------------------------------------------------
-- disdici() — restituisce il credito solo dentro la finestra
-- ---------------------------------------------------------------------------

create or replace function disdici(p_prenotazione_id uuid)
returns boolean            -- true se il credito e' stato restituito
language plpgsql
security definer
set search_path = public
as $$
declare
  v_pren      prenotazioni;
  v_slot      slot;
  v_in_tempo  boolean;
begin
  if auth.uid() is null then
    raise exception 'Accesso non autenticato' using errcode = '28000';
  end if;

  select * into v_pren from prenotazioni where id = p_prenotazione_id for update;
  if not found then
    raise exception 'Prenotazione inesistente' using errcode = '23503';
  end if;

  if v_pren.cliente_id <> auth.uid() and not e_admin() then
    raise exception 'Non puoi disdire la prenotazione di un altro cliente'
      using errcode = '42501';
  end if;

  if v_pren.stato <> 'prenotata' then
    raise exception 'Questa prenotazione non e'' piu'' disdicibile' using errcode = 'P0001';
  end if;

  select * into v_slot from slot where id = v_pren.slot_id;

  if v_slot.inizio <= now() then
    raise exception 'La lezione e'' gia'' iniziata' using errcode = 'P0001';
  end if;

  v_in_tempo := now() <= v_slot.inizio
                - make_interval(hours => impostazione('finestra_disdetta_ore'));

  update prenotazioni
     set stato = 'disdetta', disdetta_il = now()
   where id = p_prenotazione_id;

  if v_in_tempo then
    insert into movimenti (cliente_id, tipo, delta, causale, prenotazione_id, autore_id)
    values (v_pren.cliente_id, v_slot.tipo, 1, 'disdetta_in_tempo', p_prenotazione_id, auth.uid());
  end if;

  -- Fuori finestra non si scrive nulla: il credito era gia' stato scalato
  -- alla prenotazione e semplicemente non torna indietro.
  return v_in_tempo;
end;
$$;

-- ---------------------------------------------------------------------------
-- segna_presenza() — solo amministratore, non muove crediti
-- ---------------------------------------------------------------------------

create or replace function segna_presenza(p_prenotazione_id uuid, p_presente boolean)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  if not e_admin() then
    raise exception 'Riservato all''amministratore' using errcode = '42501';
  end if;

  update prenotazioni
     set stato = case when p_presente then 'presente' else 'assente' end::stato_prenotazione
   where id = p_prenotazione_id and stato in ('prenotata', 'presente', 'assente');

  if not found then
    raise exception 'Prenotazione inesistente o disdetta' using errcode = 'P0001';
  end if;
end;
$$;

-- ---------------------------------------------------------------------------
-- accredita() — la ricarica manuale concordata con il cliente
-- ---------------------------------------------------------------------------

create or replace function accredita(
  p_cliente_id  uuid,
  p_tipo        tipo_lezione,
  p_quantita    integer,
  p_importo_eur numeric default null,
  p_nota        text default null,
  p_causale     causale_movimento default 'acquisto'
)
returns bigint
language plpgsql
security definer
set search_path = public
as $$
declare
  v_id bigint;
begin
  if not e_admin() then
    raise exception 'Riservato all''amministratore' using errcode = '42501';
  end if;

  if p_quantita = 0 then
    raise exception 'La quantita'' non puo'' essere zero' using errcode = 'P0001';
  end if;

  if p_causale not in ('acquisto', 'omaggio', 'rettifica') then
    raise exception 'Causale non ammessa per una ricarica manuale' using errcode = 'P0001';
  end if;

  if p_quantita < 0 and p_causale <> 'rettifica' then
    raise exception 'Solo una rettifica puo'' togliere crediti' using errcode = 'P0001';
  end if;

  insert into movimenti (cliente_id, tipo, delta, causale, importo_eur, nota, autore_id)
  values (p_cliente_id, p_tipo, p_quantita, p_causale, p_importo_eur, p_nota, auth.uid())
  returning id into v_id;

  return v_id;
end;
$$;

-- ---------------------------------------------------------------------------
-- Row Level Security
--
--  prenotazioni e movimenti non hanno policy di INSERT/UPDATE/DELETE: si
--  scrive soltanto attraverso le funzioni qui sopra.
-- ---------------------------------------------------------------------------

alter table profili      enable row level security;
alter table slot         enable row level security;
alter table prenotazioni enable row level security;
alter table movimenti    enable row level security;
alter table impostazioni enable row level security;

create policy profili_lettura on profili for select
  using (id = auth.uid() or e_admin());

create policy profili_scrittura_admin on profili for all
  using (e_admin()) with check (e_admin());

-- Gli slot non contengono dati personali: chiunque sia autenticato li vede.
create policy slot_lettura on slot for select
  using (auth.uid() is not null);

create policy slot_scrittura_admin on slot for all
  using (e_admin()) with check (e_admin());

create policy prenotazioni_lettura on prenotazioni for select
  using (cliente_id = auth.uid() or e_admin());

create policy movimenti_lettura on movimenti for select
  using (cliente_id = auth.uid() or e_admin());

create policy impostazioni_lettura on impostazioni for select
  using (auth.uid() is not null);

create policy impostazioni_scrittura_admin on impostazioni for all
  using (e_admin()) with check (e_admin());

-- Le viste ereditano la RLS delle tabelle sottostanti (security_invoker).
alter view saldi              set (security_invoker = on);
alter view slot_disponibilita set (security_invoker = on);
