# Padel — segnapunti per Apple Watch + storico su iPhone

Due versioni, entrambe gratuite:

| | App nativa (iPhone + Watch) | PWA (`web/`) |
|---|---|---|
| Segnapunti al polso | ✅ Apple Watch | ❌ watchOS non ha un browser |
| Segnapunti sul telefono | — (sul Watch) | ✅ schermo sempre acceso durante la partita |
| Battito, calorie, allenamento in Salute | ✅ HealthKit | ❌ il web non accede a HealthKit |
| Storico, modifica, rubrica, statistiche | ✅ | ✅ |
| Backup JSON | ✅ | ✅ **stesso formato**, i dati passano da una all'altra |
| Scadenza | ⚠️ ogni 7 giorni va reinstallata (Personal Team gratuito) | ✅ nessuna |
| Serve un Mac | ✅ | ❌ basta un hosting statico |

Il motore di punteggio è lo stesso: `PadelKit/Sources/PadelKit/MatchEngine.swift`
e il suo porting 1:1 in `web/engine.js`, con gli stessi scenari di test.

---

## Struttura

```
padel/
├── project.yml              XcodeGen: target Padel (iOS) + PadelWatch (watchOS, incorporata)
├── Config/                  firma, bundle ID, interruttore HealthKit
├── PadelKit/                Swift Package puro (solo Foundation), testato anche su Linux
│   ├── Sources/PadelKit/    Rules, MatchEngine, Records (Watch→iPhone, backup), Statistics
│   └── Tests/               31 test XCTest
├── Shared/                  codice SwiftUI comune ai due target (colori, formati)
├── iOS/                     SwiftData, ricezione WCSession, storico, editor, statistiche, impostazioni
├── Watch/                   setup, segnapunti, controlli, dati, HKWorkoutSession, invio all'iPhone
├── scripts/verifica.sh      test + build di entrambi i target sui simulatori
├── scripts/reinstalla.sh    build firmata + installazione su iPhone/Watch collegati
└── web/                     PWA: HTML/CSS/JS senza dipendenze
```

La CI (`.github/workflows/padel-app.yml`) esegue i test su Linux e compila i due
target con `xcodebuild` su macOS, con i warning trattati come errori, sia con
HealthKit attivo sia disattivo.

---

## App nativa: prima installazione

Serve un Mac con Xcode (versione compatibile con iOS del tuo iPhone) e il tuo
Apple ID gratuito.

1. **Xcode e account**
   - Installa Xcode dall'App Store e aprilo una volta (accetta la licenza, installa i componenti).
   - Xcode → Settings → Accounts → **+** → Apple ID → accedi. Comparirà
     “*Tuo Nome* (Personal Team)”.
2. **Configura la firma**
   ```sh
   cd padel
   cp Config/Signing.local.xcconfig.example Config/Signing.local.xcconfig
   scripts/reinstalla.sh --team        # stampa il tuo Team ID
   ```
   In `Config/Signing.local.xcconfig` metti il Team ID e un prefisso bundle univoco
   (es. `it.mariorossi.padel`). Con il Personal Team il bundle ID deve essere tuo:
   se Xcode dice “not available”, cambia prefisso.
3. **Modalità sviluppatore sull'iPhone**
   - Collega l'iPhone al Mac col cavo, sbloccalo, tocca **Autorizza** su “Vuoi autorizzare questo computer?”.
   - Impostazioni → Privacy e sicurezza → **Modalità sviluppatore** → attiva → riavvia → conferma.
     (La voce compare solo dopo aver collegato l'iPhone a Xcode almeno una volta:
     se manca, apri Xcode → Window → Devices and Simulators con l'iPhone collegato.)
4. **Modalità sviluppatore sull'Apple Watch**
   - Con l'iPhone collegato e il Watch vicino e sbloccato, apri Xcode → Window → Devices and Simulators:
     il Watch compare sotto l'iPhone (la prima volta può volerci qualche minuto per “preparare” il dispositivo).
   - Sul Watch: Impostazioni → Privacy e sicurezza → **Modalità sviluppatore** → attiva → riavvia → conferma.
5. **Compila e installa**
   ```sh
   scripts/reinstalla.sh
   ```
   In alternativa da Xcode: `xcodegen generate`, apri `Padel.xcodeproj`, schema **Padel**,
   scegli l'iPhone e premi ▶ (per il Watch: schema **PadelWatch**, destinazione il Watch).
6. **Autorizza il profilo** (solo la prima volta, su ciascun dispositivo)
   - iPhone: Impostazioni → Generali → **VPN e gestione dispositivi** → “Apple Development: *tuo Apple ID*” → **Autorizza**.
   - Watch: se all'avvio dice “sviluppatore non autorizzato”, stessa voce nelle Impostazioni del Watch
     (Generali → VPN e gestione dispositivi), oppure autorizza dall'iPhone.
7. **App sul Watch**: se non compare da sola, sull'iPhone apri l'app **Watch** →
   scorri fino a **Padel** → **Installa**.
8. Al primo avvio della partita il Watch chiede l'accesso a **Salute** (battito, calorie,
   allenamenti): accetta, altrimenti la partita funziona ma senza quei dati.

### HealthKit con il Personal Team

La capability HealthKit **non** è tra quelle riservate agli account a pagamento
(quelle escluse sono iCloud/CloudKit, notifiche push, Apple Pay, Sign in with Apple,
Associated Domains…). La verifica definitiva la fa la prima build firmata:
se `reinstalla.sh` fallisce con un errore di profilo che cita HealthKit, metti

```
PADEL_HEALTHKIT = NO
```

in `Config/Signing.local.xcconfig` e rilancia. L'app si compila senza entitlement
né codice HealthKit: il segnapunti, l'invio all'iPhone e tutto il resto funzionano uguali;
mancano solo battito/calorie e il salvataggio in Salute, e senza sessione di
allenamento il Watch può tornare al quadrante tra un punto e l'altro
(la partita resta salvata e riprende da dove era).

---

## Reinstallazione ogni 7 giorni

Il profilo del Personal Team scade dopo 7 giorni: l'app non si apre più
(“non più disponibile”). **I dati non si perdono** se reinstalli sopra, senza cancellare l'app.

1. Collega l'iPhone al Mac (o stessa rete Wi-Fi, se l'hai già abbinato in Xcode), sbloccalo.
2. Tieni il Watch al polso, sbloccato, vicino all'iPhone.
3. ```sh
   cd padel && scripts/reinstalla.sh
   ```

Consiglio: mettiti un promemoria ricorrente ogni 6 giorni. Limiti del Personal Team da sapere:
massimo 3 app installate per dispositivo e 10 bundle ID nuovi ogni 7 giorni
(non cambiare prefisso ogni volta).

**Per tuo figlio o gli amici**: con il Personal Team bisogna installare dal *tuo* Mac
sui *loro* dispositivi (collegati via cavo) e ripetere ogni 7 giorni. Per distribuirla
davvero servirebbe l'Apple Developer Program (TestFlight): è l'unico caso in cui ci sono costi.
Per loro la PWA è probabilmente la soluzione migliore.

---

## Verifica locale

```sh
cd padel && scripts/verifica.sh
```

Genera il progetto, esegue i 31 test di PadelKit, compila iPhone e Watch
sui simulatori (iPhone 17, Apple Watch Ultra 3) con HealthKit attivo e disattivo.

---

## PWA (`web/`)

**Pubblicata su GitHub Pages: https://megagiov.github.io/ginevra/padel/**
(cartella `padel/` del branch `gh-pages`, accanto a Palestra). Per aggiornarla, copia di nuovo
i file di `padel/web/` in quella cartella e alza `VERSION` in `sw.js`.

Sono file statici: vanno pubblicati via **HTTPS** (necessario per service worker e installazione).

- **Sul tuo hosting**: carica il contenuto di `padel/web/` in una cartella, es.
  `https://tuosito.it/padel/`. Non serve PHP né database.
- **GitHub Pages / Netlify / Cloudflare Pages**: gratuiti, basta puntare alla cartella `padel/web`.

Sull'iPhone: apri l'indirizzo in **Safari** → pulsante Condividi → **Aggiungi alla schermata Home**.
Si apre a tutto schermo, funziona offline e non scade mai.

Da sapere:
- I dati stanno nel browser di quel telefono. Le app aggiunte alla Home sono escluse dalla
  cancellazione automatica di Safari, ma se elimini l'icona o i dati di Safari li perdi:
  usa **Impostazioni → Esporta backup** ogni tanto.
- Il backup è lo stesso JSON dell'app nativa: puoi importarlo dall'una all'altra.
- Durante la partita lo schermo resta acceso (Screen Wake Lock, iOS 16.4+).
- iPhone non supporta la vibrazione dal web: niente feedback aptico.
- Aggiornando i file sul server, cambia `VERSION` in `sw.js`.

Test del motore JS: `node --test padel/web/`.

---

## NAS Synology (DS120j o simili)

### Backup sul NAS (consigliato, nessuna esposizione in rete)
1. DSM → Pannello di controllo → Servizi file → **SMB** attivo (lo è di default).
2. Crea una cartella condivisa, es. `Padel`.
3. iPhone → app **File** → ⋯ → **Connetti al server** → `smb://IP-DEL-NAS` → utente e password DSM.
4. Nell'app: Impostazioni → **Esporta backup** → **Salva in File** → NAS → `Padel`.
   Per ripristinare: **Importa backup** e scegli il file dal NAS. Funziona sulla Wi-Fi di casa.

### Ospitare la PWA sul NAS
Serve HTTPS con certificato valido, quindi il NAS deve essere raggiungibile da Internet sulle porte 80/443.
1. Centro pacchetti → installa **Web Station** (crea la cartella condivisa `web`).
2. File Station → `web` → crea `padel` e carica il contenuto di `padel/web/`
   (`index.html`, `app.js`, `engine.js`, `style.css`, `sw.js`, `manifest.json`, cartella `icons`;
   i file di test non servono).
3. Pannello di controllo → Accesso esterno → **DDNS** → Aggiungi → provider *Synology* →
   scegli `tuonome.synology.me` e spunta **Ottieni un certificato da Let's Encrypt**.
4. Sul router inoltra le porte TCP **80** e **443** all'IP del NAS (non esporre le porte di DSM 5000/5001).
5. Safari sull'iPhone → `https://tuonome.synology.me/padel/` → Condividi → **Aggiungi alla schermata Home**.

Sicurezza se esponi il NAS: password forte e verifica in due passaggi sull'account DSM,
blocco automatico attivo (Pannello di controllo → Sicurezza → Account), DSM sempre aggiornato,
account `admin` disattivato. Se non vuoi esporre il NAS, ospita la PWA su GitHub Pages
e usa il NAS solo per i backup.
