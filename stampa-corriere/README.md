# Maschera pubblicitaria per LDV corriere — GM Vegasi

Foglio da 105×148 mm (il classico "10x15" adesivo) da pre-stampare **prima**
di stampare la LDV vera e propria: la parte alta resta bianca per fare
spazio all'etichetta del corriere, la parte bassa porta la pubblicità del
brand.

## Come è nata la misura

Il layout è calcolato su una LDV **GLS** reale (105,0 × 148,2 mm): il blocco
etichetta — intestazione mittente, città, barcode, riga GLS — arriva fino a
circa 86 mm dall'alto. `maschera-10x15.html` lascia libera una fascia di
90 mm (5 mm di margine di sicurezza) e usa i restanti ~58 mm per la grafica.

**Se usi un corriere diverso da GLS** (BRT, SDA/Poste, ecc.) l'etichetta può
avere un'impaginazione diversa: prima di stampare in serie, fai un test
allineando la LDV a una maschera stampata e verifica che non si sovrappongano.

## Come si usa

1. Apri `maschera-10x15.html` nel browser e stampalo su un foglio 10x15
   bianco (o esportalo in PDF da lì e stampa il PDF).
2. Ricarica lo stesso foglio nel vassoio/alimentatore della stampante.
3. Stampa sopra la LDV del corriere come fai di solito: cadrà nella fascia
   alta lasciata vuota.

Prima di stampare in serie, fai **una prova** con un foglio scarto e
controlla l'allineamento: la classe `.zona-ldv` in cima al foglio ha un
bordo tratteggiato leggero pensato apposta come guida per il test. Quando
sei sicuro dell'allineamento, aggiungi `no-guida` al tag `<body>` per
toglierlo dalla stampa definitiva.

## Cosa manca da confermare prima di stampare in serie

Il riquadro promozionale nella maschera contiene segnaposto da sostituire
a mano nell'HTML:

- **Handle social** — attualmente `@[handle da confermare]`. Se hai un
  account Instagram/TikTok del brand, sostituiscilo con quello reale.
- **Codice sconto** — attualmente `[CODICE]`, nessuno sconto reale è mai
  stato deciso qui: va scelto (percentuale/importo, validità) prima di
  promettere qualcosa in stampa.
- **Logo** — qui c'è solo il nome "GM Vegasi" in tipografia. Se hai un file
  logo puoi sostituire il paragrafo `.wordmark` con un tag `<img>`.

## Personalizzare

| Cosa cambiare | Dove in `maschera-10x15.html` |
|---|---|
| Altezza fascia LDV | `.zona-ldv { height: ... }` |
| Testo di ringraziamento | `<p class="tagline">` |
| Sito | `<p class="sito">` |
| Social e codice sconto | `<div class="riga-promo">` |
| Colori/font | blocco `<style>` in cima |

Per un PDF pronto da distribuire in stampa, apri il file in Chrome e usa
"Stampa → Salva come PDF" con margini a 0 e formato di carta personalizzato
105×148 mm.
