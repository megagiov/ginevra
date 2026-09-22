# Sito Sorgente Traslochi

Sito statico in italiano per Sorgente Traslochi (Napoli). Nessun backend,
nessun servizio a pagamento, nessuna dipendenza esterna: si genera con Python
gia' presente nel sistema e si pubblica su Cloudflare Pages nel piano gratuito.

## Come si genera

```bash
cd sito
python3 build.py
```

Il comando ricrea da zero la cartella `dist/`, che e' quella da pubblicare.
`dist/` e' versionata apposta: cosi' Cloudflare Pages puo' servirla senza
eseguire alcuna build.

Anteprima in locale:

```bash
cd sito/dist && python3 -m http.server 8765
# poi apri http://localhost:8765
```

## Dove si modificano le cose

| Cosa | File |
| --- | --- |
| Testi, FAQ, zone, dati azienda, P.IVA, orari | `content.py` |
| Struttura delle pagine, dati strutturati, modulo | `build.py` |
| Grafica, colori, layout | `src/style.css` |
| Menu mobile (unico JS del sito) | `SCRIPT` dentro `build.py` |

Dopo ogni modifica: `python3 build.py`.

Il dominio di pubblicazione sta in una sola riga (`BASE_URL` in `content.py`).
Il giorno in cui si collega un dominio `.it` si cambia quella riga e si
rigenera: canonical, Open Graph e sitemap si aggiornano da soli.

## Cosa contiene

Dieci pagine: home, cinque pagine servizio, zone servite, chi siamo,
preventivo e privacy. Piu' `sitemap.xml`, `robots.txt`, favicon, immagine di
anteprima social e `_headers` per Cloudflare.

Caratteristiche tecniche:

- HTML statico, un solo CSS (~12 KB) e 400 byte di JavaScript per il menu
- font di sistema: nessuna richiesta a Google Fonts, nessun blocco del render
- nessun cookie, nessun tracciamento, nessun banner di consenso da mostrare
- dati strutturati JSON-LD: `MovingCompany`, `FAQPage`, `BreadcrumbList`
- title, meta description e canonical unici per pagina, un solo H1 per pagina
- barra fissa Chiama/WhatsApp su mobile, nessun overflow orizzontale da 320 px
  in su

## Immagini

Le foto attuali dell'azienda sono stock, quindi il sito non ne usa nessuna: al
loro posto ci sono segnaposto (`<div class="ph">`) che indicano che foto
servirebbe. Quando arrivano le foto reali:

1. converti in WebP e ridimensiona (max 1600 px di lato lungo)
2. salva in `src/img/` con nomi descrittivi, per esempio
   `trasloco-appartamento-vomero-napoli.webp`
3. sostituisci il segnaposto con
   `<img src="/img/nome-file.webp" width="..." height="..." loading="lazy" alt="descrizione">`
   (niente `loading="lazy"` sulla prima immagine della home: penalizza l'LCP)
4. fai copiare la cartella da `build.py` insieme agli altri statici

## Da completare prima di pubblicare

Vedi `DA-COMPLETARE.md`: contiene i dati mancanti e i due punti da confermare
con l'azienda.

## Pubblicazione

Vedi `DEPLOY.md`: Cloudflare Pages, Google Search Console, scheda Google
Business e dismissione del vecchio sito Wix.
