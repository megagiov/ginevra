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
| Data dell'ultima modifica ai testi (`DATA_AGGIORNAMENTO`) | `content.py` |
| Struttura delle pagine, dati strutturati, modulo | `build.py` |
| Grafica, colori, layout | `src/style.css` |
| Menu mobile (unico JS del sito) | `SCRIPT` dentro `build.py` |

Dopo ogni modifica ai testi, aggiorna `DATA_AGGIORNAMENTO` in `content.py` e
rigenera con `python3 build.py`. Quella data compare come data
dell'informativa privacy e come `lastmod` nella sitemap: va spostata quando i
contenuti cambiano davvero, non a ogni generazione. Il comando elenca in fondo i dati
ancora mancanti (P.IVA, ragione sociale, orari, ID Formspree): finche' sono
vuoti il sito li omette invece di mostrare segnaposto, ma vanno riempiti prima
di pubblicare.

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

Le foto reali stanno in `src/img/`: i WebP che il sito usa e gli originali in
`src/img/originali/`. Per aggiungerne di nuove:

1. metti l'originale (JPG o PNG) in `src/img/originali/` con un nome
   descrittivo, per esempio `trasloco-appartamento-vomero-napoli.jpg`
2. aggiungilo all'elenco `FOTO` in `tools/prepara-foto.py`
3. `pip install Pillow && python3 tools/prepara-foto.py` converte in WebP
4. usa la foto in `build.py` con `foto("nome.webp", "descrizione", larghezza,
   altezza)`; la prima immagine della home vuole `primaria=True`, che la
   carica subito invece che in differita
5. `python3 build.py`

`build.py` non ha bisogno di Pillow: si limita a copiare i file gia' pronti.
La conversione e' un passaggio a parte, da fare solo quando arrivano foto
nuove.

Dove mancano ancora le foto (le pagine servizio) resta un segnaposto
`<div class="ph">` che dice quale scatto servirebbe.

## Da completare prima di pubblicare

Vedi `DA-COMPLETARE.md`: contiene i dati mancanti e i due punti da confermare
con l'azienda.

## Pubblicazione

Vedi `DEPLOY.md`: Cloudflare Pages, Google Search Console, scheda Google
Business e dismissione del vecchio sito Wix.
