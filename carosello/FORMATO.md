# Formato carosello TikTok — GM Vegasi

Misurato sui caroselli pubblicati (`riferimento/1-5.jpg`, giacca Marrone/Nero).

## Impostazioni fisse
- **Dimensione**: 1080x1080 (1:1), JPG.
- **Cornice**: blu `#0272BC`, 22 px su tutti i lati.
- **Divisorio centrale**: stesso blu, ~10 px (x 536-546). Due pannelli affiancati, uno per variante colore.
- **Logo**: riquadro nero "GM VEGASI TikTok Shop" in basso a sinistra, 186x198 px a (70, 818). File: `assets/logo_gmvegasi_tiktokshop.png`.
- **Testo**: bianco, sans-serif bold (Open Sans Bold), centrato.
  - claim principale ~54 px al centro della slide, sopra il divisorio, max 2 righe;
  - titoli per pannello ~34 px in alto, centrati sul proprio pannello (slide "look").
- **Foto**: packshot su bianco o modelle su fondo grigio chiaro; stessa inquadratura nei due pannelli.

## Struttura (5 slide)
1. **Hook**: packshot dei colori a confronto + domanda "Colore A o Colore B?".
2. **Caratteristiche**: modelle frontali + claim sul fit/dettagli.
3. **Engagement**: retro + "Team A o Team B? Scrivilo nei commenti!".
4. **Dettagli**: primi piani + claim sui dettagli.
5. **Look completo**: figura intera, titolo per pannello con l'abbinamento.

## Regole
- Claim solo forniti dall'utente o visibili in foto; nessun materiale dichiarato senza fonte ("effetto camoscio", non "camoscio").
- Con 3 colori: layout `tre` (fasce orizzontali), utile per prodotti larghi come le scarpe.

## Generazione
`python3 carosello/build.py spec.json` (vedi docstring per lo schema). Font: mettere `fonts/OpenSans-Bold.ttf`; senza, ripiega su DejaVu Sans Bold.
