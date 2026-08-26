# GM Vegasi — istruzioni di progetto

## OBBLIGATORIO prima di qualsiasi lavoro su Artlist

Prima di generare **qualunque cosa** su Artlist — video, immagini, voci —
leggi per intero `video-prodotto/ARTLIST.md`.

Contiene i costi misurati, i difetti noti dei modelli, le regole editoriali e i
kit gia' pronti. Non e' documentazione di cortesia: ogni riga li' dentro
corrisponde a un errore gia' pagato in crediti in una sessione precedente.

Regole che non si violano mai, nemmeno se sembrano superflue:

1. **Il prezzo del gate va sempre riportato all'utente prima di spendere.**
   Sotto una certa soglia il gate NON scatta e la generazione parte da sola:
   per quelle, avvisare subito dopo quanto e' stato speso.
2. **Ogni video generato va ispezionato fotogramma per fotogramma prima di
   consegnarlo.** Il modello inventa marchi sui prodotti anche quando glielo
   vieti esplicitamente: e' successo tre volte su tre.
3. **Mai far pronunciare al modello video un'affermazione commerciale in
   italiano.** La pronuncia e' inaffidabile e sbaglia in modo diverso a ogni
   tentativo. I claim vanno a schermo come testo.
4. **Nessuna affermazione inventata.** I claim sono solo quelli forniti
   dall'utente. La presentatrice e' una dimostratrice, mai una cliente o una
   dipendente reale: non puo' raccontare esperienze d'acquisto.

## Altro nel repository

`catalogo/` contiene l'archivio del marchio e il generatore dei due cataloghi
in PDF (licenze e prodotti). Vedi il suo README.

`brand/logo/` contiene il marchio in vettoriale e in PNG trasparente.

`video-prodotto/` contiene la pipeline locale per gli spot: montaggio,
scontorno, voce e sottotitoli girano senza servizi a pagamento. Vedi il suo
README.
