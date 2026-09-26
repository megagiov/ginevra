# Palestra — note per chi ci lavora

App web offline per registrare gli allenamenti. L'utente e' italiano: testi,
commit e spiegazioni in italiano.

## Pubblicare: tre passi, nell'ordine

1. `node tools/versione.js` — **obbligatorio**. Il service worker serve l'app
   dalla memoria del telefono e scarica una versione nuova solo se cambia la
   versione in `sw.js`. Dimenticarlo ha gia' lasciato l'utente per giorni su
   una versione vecchia, convinto di avere correzioni che non gli erano
   arrivate.
2. `NODE_PATH=<node_modules con playwright> ./tests/run.sh` — deve passare
   tutto. Rifiuta di partire se la versione e' vecchia.
3. Copiare `palestra/` sul ramo `gh-pages` e fare push. **Solo quella
   cartella**: nella radice di `gh-pages` c'e' un altro sito dell'utente, con
   un trasferimento di dominio in corso. Non toccarlo.

## Cose da non promettere

- Vibrazione su iPhone: nessuna versione di Safari la concede alle web app.
- Battito in tempo reale dall'Apple Watch in Safari: HealthKit e Bluetooth
  non sono accessibili dal web. La strada e' l'automazione di fine
  allenamento + "Incolla dal Watch", oppure un'app nativa (serve un Mac).

## Catalogo

I nomi italiani stanno in `tools/nomi-it.json`, i riassunti di esecuzione in
`tools/riassunti-it.json` (chiave: nome inglese). Dopo averli cambiati:
`node tools/build-catalog.js`, poi `node tools/versione.js`.
