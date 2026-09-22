# SEO: cosa e' fatto, cosa manca, cosa conta davvero

Documento di lavoro per Sorgente Traslochi. Aggiornato al 22 settembre 2026.

Premessa onesta, perche' il resto si capisca meglio: per un'impresa di
traslochi a Napoli, **la scheda Google Business pesa piu' del sito**. Chi cerca
"traslochi Napoli" dal telefono vede prima la mappa con tre attivita', e solo
sotto i risultati normali. Il sito serve a due cose: convincere chi ci arriva,
e sostenere la scheda con dati coerenti. Le due cose insieme funzionano; il
sito da solo molto meno.

---

## 1. Fatto: SEO tecnica

Tutto verificato con Lighthouse sui file reali, desktop e mobile.

| Voce | Stato |
| --- | --- |
| Prestazioni | 100 |
| Accessibilita' | 100 |
| Buone pratiche | 100 |
| SEO | 100 |
| LCP su mobile | 1,0 - 1,5 s |
| CLS | 0 |

Nel dettaglio:

- title e meta description unici per pagina, con la parola chiave e Napoli
- un solo H1 per pagina, gerarchia H2/H3 coerente
- URL parlanti (`/traslochi-uffici-napoli/`, non `/servizi/2`)
- canonical su ogni pagina, sitemap.xml, robots.txt
- dati strutturati: `MovingCompany` con NAP, coordinate, orari, dodici aree
  servite e collegamenti ai profili social; `Service` su ogni pagina servizio,
  agganciato alla stessa azienda; `FAQPage` dove ci sono domande;
  `BreadcrumbList` ovunque
- pagina 404 vera (prima un indirizzo inesistente restituiva la home con
  stato 200: Google avrebbe indicizzato indirizzi inventati)
- immagini WebP con nomi descrittivi, alt, misure dichiarate
- collegamenti interni fra zone e servizi, agganciati a frasi reali dei testi
- testi originali e diversi per ognuna delle dodici zone, senza la solita
  pagina fotocopia con il nome del comune cambiato

Non c'e' molto altro da spremere sul piano tecnico: da qui in avanti il
guadagno sta nei contenuti e nella scheda Google.

---

## 2. Da fare subito, e puo' farlo solo chi ha gli account

### Google Search Console (dieci minuti, il primo passo)

Senza questo, Google scopre il sito da solo, con i suoi tempi. Con questo, si
parte in giorni invece che in settimane e si vede cosa cercano le persone.

1. <https://search.google.com/search-console> con l'account Google
   dell'azienda, lo stesso della scheda Business
2. Aggiungi proprieta' > **Prefisso URL** > `https://sorgentetraslochi.pages.dev`
3. Verifica: se siete gia' proprietari verificati della scheda Google
   Business, spesso passa da sola. Altrimenti Google da' un `<meta>`:
   mandatemelo, lo inserisco e ripubblico in un minuto
4. Menu **Sitemap** > inserire `sitemap.xml` > Invia
5. **Controllo URL** in alto: incollare l'indirizzo della home e premere
   *Richiedi indicizzazione*. Ripetere per le cinque pagine servizio e per
   zone servite

Dopo tre o quattro settimane, in **Rendimento**, si legge con quali ricerche
il sito compare. E' li' che si capisce su cosa insistere: se arriva traffico
per "sgombero cantina Napoli" e non per "trasloco ufficio", si rafforza la
prima.

### Scheda Google Business (l'investimento che rende di piu')

1. Sito web: sostituire l'indirizzo Wix con quello nuovo
2. Verificare che nome, indirizzo e telefono siano **identici al carattere** a
   quelli del sito: `Sorgente Traslochi`, `Via Cupa Vicinale dell'Arco 72,
   80144 Napoli (NA)`, `347 263 6504`. Google incrocia i due: se coincidono,
   la scheda sale
3. Orari: lunedi'-sabato 8:00-18:00, gli stessi che stanno sul sito
4. Servizi: traslochi abitazioni, traslochi uffici e negozi, montaggio mobili,
   sgomberi, deposito mobili. Stessi nomi delle pagine
5. Aree servite: i dodici comuni della pagina zone servite
6. Foto: caricare le stesse che stanno sul sito, e aggiungerne di nuove ogni
   tanto. Le schede con foto recenti ricevono piu' contatti
7. Post: anche uno al mese ("trasloco completato a Pozzuoli", "montaggio
   cucina su misura al Vomero") tiene la scheda viva

### Recensioni: il fattore numero uno

Nel locale, la differenza fra comparire terzi o non comparire la fanno numero,
freschezza e risposte delle recensioni. Molto piu' di qualunque parola messa
nel sito.

- chiedete una recensione a fine lavoro, quando il cliente e' contento e
  ancora davanti a voi: e' il momento in cui accettano
- usate il link diretto dalla scheda (*Chiedi recensioni*), mandatelo su
  WhatsApp mentre siete ancora sul posto
- rispondete a tutte, anche alle negative, con calma e nel merito
- obiettivo ragionevole: due o tre al mese, costanti. Venti recensioni vere
  spalmate su un anno valgono piu' di cinquanta arrivate in una settimana

Sul sito ci sono due segnaposto per le recensioni: quando ne avete di reali,
le riporto con nome e data. **Non le inventiamo**: oltre a essere pubblicita'
ingannevole, Google le riconosce e penalizza.

---

## 3. Proposta: pagine dedicate ai comuni principali

Oggi i dodici comuni stanno in sezioni della stessa pagina. Funziona, ma chi
cerca "traslochi Casoria" trova pagine di concorrenti interamente dedicate a
Casoria, e quelle partono avvantaggiate.

L'intervento con il miglior rapporto fra lavoro e risultato e' dare una
**pagina propria ai comuni che contano di piu'**: Casoria, Afragola,
Giugliano, Pozzuoli, Portici, Torre del Greco. Sei pagine, non dodici: meglio
poche pagine con dentro qualcosa di vero che dodici riempite di aria.

Perche' abbia senso, ogni pagina deve dire cose che valgono solo li':

- com'e' fatto l'accesso in quel comune (strade strette, cortili, pendenze)
- che tipo di lavori ci capitano piu' spesso
- quanto ci mettiamo ad arrivare e come organizziamo la giornata
- un lavoro realmente svolto li', se ne ricordate uno raccontabile
- una foto fatta in quel comune, se c'e'

Se invece sono sei varianti dello stesso testo con il nome cambiato, Google le
tratta come contenuto povero e non le premia: in quel caso e' meglio lasciare
tutto com'e'.

**Serve il vostro contributo**, non posso scriverle da solo: mi bastano due
minuti di racconto per comune (che zone, che difficolta', un lavoro tipico) e
le costruisco io. Ne parliamo quando volete.

---

## 4. Contenuti che mancano al sito

In ordine di utilita':

1. **Recensioni reali** al posto dei due segnaposto in home
2. **Foto** per le tre pagine ancora senza: uffici e negozi, sgomberi,
   deposito
3. **P.IVA e ragione sociale**: oltre a essere obbligatorie, sono dati che
   Google usa per capire che l'impresa e' reale
4. **Originali delle foto dei mezzi**, per rifare l'anteprima social che oggi
   e' ingrandita da un file piccolo

---

## 5. Cosa aspettarsi, con i tempi veri

- **giorni**: il sito compare cercando "sorgente traslochi" (nome proprio)
- **due-quattro settimane**: le pagine entrano nell'indice e iniziano a
  comparire per ricerche lunghe e specifiche ("smontaggio cucina su misura
  Napoli")
- **tre-sei mesi**: si puo' competere su ricerche generiche e molto contese
  come "traslochi Napoli", e solo se nel frattempo la scheda Google cresce di
  recensioni

Chi promette la prima posizione in due settimane sta vendendo fumo. Quello che
si puo' fare e' quello che abbiamo fatto: un sito veloce, chiaro, coerente nei
dati, che non dice bugie, piu' una scheda Google curata. Il resto e' costanza.

---

## 6. Da non fare mai

- comprare link o pacchetti "1000 backlink": Google se ne accorge e penalizza
- inventare recensioni, certificazioni, assicurazioni o anni di attivita'
- riempire le pagine di "traslochi Napoli" ripetuto: e' controproducente da
  piu' di dieci anni
- aprire un secondo sito con lo stesso contenuto per "occupare piu' spazio":
  si fanno concorrenza fra loro
- cambiare gli indirizzi delle pagine dopo l'indicizzazione senza redirect
