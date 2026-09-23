# -*- coding: utf-8 -*-
"""Contenuti del sito Sorgente Traslochi.

Tutti i testi sono qui: per correggere una frase si modifica questo file e si
rilancia `python3 build.py`. Nessun prezzo, nessuna certificazione e nessun
numero non fornito dall'azienda compare in queste pagine.
"""

# --------------------------------------------------------------------------
# Dati azienda (NAP: deve restare identico ovunque, anche nei dati strutturati)
# --------------------------------------------------------------------------

AZIENDA = {
    "nome": "Sorgente Traslochi",
    # I tre campi qui sotto possono restare vuoti: in quel caso il sito li
    # omette invece di mostrare un segnaposto, e build.py avvisa a ogni
    # generazione che mancano. Vanno riempiti prima di pubblicare.
    "ragione_sociale": "",   # se vuota, il sito usa il nome commerciale
    "piva": "",              # obbligatoria per legge una volta pubblicato
    "via": "Via Cupa Vicinale dell'Arco 72",
    "cap": "80144",
    "citta": "Napoli",
    "provincia": "NA",
    "regione": "Campania",
    "telefono_display": "347 263 6504",
    "telefono_tel": "+393472636504",
    "whatsapp": "393472636504",
    "email": "sorgentetraslochi@gmail.com",
    "maps": "https://maps.google.com/?cid=16215080151173160187",
    "facebook": "https://it-it.facebook.com/pages/category/Home-Mover/Sorgente-Group-Trasporti-Traslochi-1445547735715866/",
    "instagram": "https://www.instagram.com/sorgentetraslochi/",
    "orari": "lunedì - sabato, 8:00 - 18:00",
    "lat": "40.8797",
    "lon": "14.2350",
}

# Dominio di pubblicazione. Il giorno in cui si collega un dominio .it basta
# cambiare questa riga e rigenerare: canonical, sitemap e Open Graph seguono.
BASE_URL = "https://sorgentetraslochi.pages.dev"

# Gli stessi orari in forma leggibile da Google (schema.org). Se cambiano gli
# orari sopra, vanno aggiornati anche qui: sono la stessa informazione detta
# due volte, una per le persone e una per i motori di ricerca.
ORARI_SCHEMA = [
    {
        "giorni": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                   "Saturday"],
        "apre": "08:00",
        "chiude": "18:00",
    },
]

WHATSAPP_MSG = "Salve,%20vorrei%20un%20preventivo%20per%20un%20trasloco."

# Data dell'ultima modifica reale ai contenuti, in formato ISO. Va aggiornata
# a mano quando si cambiano i testi, NON a ogni generazione: compare come data
# dell'informativa privacy e come lastmod nella sitemap. Se si muovesse da
# sola a ogni build direbbe due bugie: che la privacy e' cambiata oggi e che
# tutte le pagine sono state riscritte oggi, e i motori imparano a ignorare
# un lastmod che cambia sempre.
DATA_AGGIORNAMENTO = "2026-09-23"

# Codice di verifica di Google Search Console. Google lo fornisce come
# <meta name="google-site-verification" content="XXXX">: qui va solo la parte
# dentro content. Vuoto = nessun tag, che e' la situazione prima della
# verifica o quando si verifica in altro modo (per esempio tramite la scheda
# Google Business, che spesso non richiede alcun tag).
VERIFICA_GOOGLE = "MiEvUbrsDnjOOwDmFwMv1DVJUHVep4ws0AC31sVjnn4"

# Formspree: ID del form gratuito collegato a sorgentetraslochi@gmail.com.
# Compare nell'endpoint del modulo (formspree.io/f/<ID>).
FORMSPREE_ID = "mvkgajzy"

# --------------------------------------------------------------------------
# Navigazione
# --------------------------------------------------------------------------

NAV = [
    ("/traslochi-abitazioni-napoli/", "Traslochi case"),
    ("/traslochi-uffici-napoli/", "Uffici e negozi"),
    ("/montaggio-mobili-napoli/", "Montaggio mobili"),
    ("/sgomberi-napoli/", "Sgomberi"),
    ("/deposito-mobili-napoli/", "Deposito"),
    ("/zone-servite/", "Zone servite"),
    ("/chi-siamo/", "Chi siamo"),
]

SERVIZI = [
    {
        "url": "/traslochi-abitazioni-napoli/",
        "titolo": "Traslochi di abitazioni",
        "sommario": "Dal monolocale alla villa: imballaggio, smontaggio, "
                    "trasporto e rimontaggio, con o senza autoscala.",
        "icona": "casa",
    },
    {
        "url": "/traslochi-uffici-napoli/",
        "titolo": "Traslochi di uffici e negozi",
        "sommario": "Spostamenti organizzati per fermare l'attività il meno "
                    "possibile, anche di sera o nel fine settimana.",
        "icona": "ufficio",
    },
    {
        "url": "/montaggio-mobili-napoli/",
        "titolo": "Montaggio e smontaggio mobili",
        "sommario": "Cucine, armadi e arredi su misura montati da chi lo fa "
                    "ogni giorno per i mobilifici campani.",
        "icona": "chiave",
    },
    {
        "url": "/sgomberi-napoli/",
        "titolo": "Sgomberi",
        "sommario": "Case, cantine, garage e locali svuotati e lasciati "
                    "puliti, con separazione di ciò che si recupera.",
        "icona": "scatola",
    },
    {
        "url": "/deposito-mobili-napoli/",
        "titolo": "Deposito mobili",
        "sommario": "Un posto dove lasciare i mobili quando fra un'uscita e "
                    "un'entrata passano settimane.",
        "icona": "magazzino",
    },
]

MARCHI_ARREDO = [
    "Boffi", "Arclinea", "Valcucine", "Ernestomeda", "Porada",
    "Bernini", "Poltrona Frau", "Ceccotti", "Cappellini", "Schiffini",
]

MOBILIFICI = ["Ardisa", "Supermobili", "Cappelli", "Deville"]


# --------------------------------------------------------------------------
# Home
# --------------------------------------------------------------------------

HOME = {
    "slug": "",
    "title": "Traslochi a Napoli e provincia dal 1965 | Sorgente Traslochi",
    "description": "Traslochi di case e uffici, montaggio mobili, sgomberi e "
                   "deposito a Napoli e provincia. Preventivo e sopralluogo "
                   "gratuiti: 347 263 6504.",
    "h1": "Traslochi a Napoli e provincia, dal 1965",
    "sottotitolo": "Case, uffici e negozi, montaggio e smontaggio mobili, "
                   "sgomberi e deposito. Preventivo e sopralluogo gratuiti, "
                   "senza impegno.",
    "fiducia": [
        ("Dal 1965", "Tre generazioni della stessa famiglia sulle strade di "
                     "Napoli e provincia."),
        ("Preventivo gratuito", "Veniamo a vedere casa, misuriamo l'accesso e "
                                "vi diamo una cifra chiara prima di iniziare."),
        ("Montatori di arredo di design", "Gli stessi che montano cucine e "
                                          "arredi su misura per i mobilifici."),
        ("Napoli e provincia", "Dal centro storico ai comuni dell'hinterland, "
                               "conosciamo strade, cortili e permessi."),
    ],
    "chi_siamo_breve": [
        "Sorgente Traslochi è un'impresa familiare napoletana che trasporta "
        "e monta mobili dal 1965. Abbiamo cominciato con i trasporti per i "
        "mobilifici della città e negli anni abbiamo aggiunto tutto quello "
        "che sta intorno a un trasloco: l'imballaggio, lo smontaggio, "
        "l'autoscala quando la scala non basta, il rimontaggio a casa nuova.",
        "Chi vi risponde al telefono è la stessa persona che viene a fare il "
        "sopralluogo e che il giorno del trasloco è sul posto. Non passiamo "
        "il lavoro a terzi e non improvvisiamo squadre: i nostri montatori "
        "lavorano con noi da anni, ed è il motivo per cui ci chiamano anche "
        "quando c'è da smontare e rimontare una cucina su misura.",
    ],
    "come_funziona": [
        ("Ci chiamate", "Al telefono o su WhatsApp ci raccontate cosa dovete "
                        "spostare, da dove e verso dove. Bastano pochi minuti "
                        "per capire se serve un sopralluogo o se il quadro è "
                        "già chiaro."),
        ("Sopralluogo gratuito", "Passiamo a vedere l'abitazione o l'ufficio: "
                                 "guardiamo i volumi, il piano, l'ascensore, "
                                 "lo spazio per fermare il camion e i mobili "
                                 "che vanno smontati."),
        ("Preventivo scritto", "Vi diamo per iscritto cosa è compreso: "
                               "imballaggi, smontaggio, trasporto, "
                               "eventuale autoscala, rimontaggio. Decidete "
                               "con calma, senza impegno."),
        ("Il giorno del trasloco", "Arriviamo con il materiale e la squadra "
                                   "concordati. Imballiamo, carichiamo, "
                                   "trasportiamo e rimontiamo. A fine "
                                   "giornata i mobili sono al loro posto."),
    ],
    "faq": [
        ("Quanto costa un trasloco a Napoli?",
         "Non esiste un prezzo unico: dipende da quanti metri cubi si "
         "spostano, dal piano e dall'ascensore in partenza e in arrivo, dallo "
         "spazio per fermare il mezzo, dai mobili da smontare e rimontare e "
         "dalla distanza. Per questo veniamo a vedere di persona e mettiamo "
         "tutto per iscritto prima di cominciare: il sopralluogo e il "
         "preventivo sono gratuiti e non vi impegnano."),
        ("Quanto tempo prima conviene prenotare?",
         "Prima ci si sente, più facile è tenere il giorno che serve a voi. "
         "Fine mese, inizio mese e sabato sono i periodi più richiesti. "
         "Chiamate appena avete una data indicativa, anche se non è ancora "
         "definitiva: si aggiusta poi."),
        ("Lavorate solo a Napoli città?",
         "No, copriamo tutta la provincia: Casoria, Afragola, Arzano, "
         "Casalnuovo, Giugliano, Marano, l'area flegrea con Pozzuoli, e la "
         "fascia vesuviana con Portici, Ercolano e Torre del Greco, oltre a "
         "Pomigliano d'Arco. Se il vostro comune non è in elenco chiedeteci "
         "lo stesso: spesso ci andiamo."),
        ("Posso chiamarvi solo per montare o smontare dei mobili?",
         "Sì, il montaggio è un servizio a sé: lo facciamo anche per chi "
         "non trasloca, compreso un singolo mobile o una cucina comprata in "
         "negozio."),
    ],
    "recensioni_nota": "Stiamo raccogliendo qui le recensioni lasciate dai "
                       "clienti sulla scheda Google. Se vi siete trovati bene, "
                       "lasciarne una è il modo più utile per aiutarci.",
}

# --------------------------------------------------------------------------
# Pagine servizio
# --------------------------------------------------------------------------

SERVIZIO_ABITAZIONI = {
    "slug": "traslochi-abitazioni-napoli",
    "title": "Traslochi abitazioni Napoli | Case e appartamenti | Sorgente",
    "description": "Trasloco di case e appartamenti a Napoli e provincia: "
                   "imballaggio, smontaggio e rimontaggio mobili, autoscala. "
                   "Sopralluogo e preventivo gratuiti.",
    "h1": "Traslochi di abitazioni a Napoli",
    "intro": [
        "Traslocare una casa a Napoli raramente è solo questione di "
        "chilometri. È il vicolo dove il camion non entra, il quarto piano "
        "senza ascensore, l'armadio che è salito smontato vent'anni fa e "
        "adesso deve riscendere, il balcone che è l'unica via d'uscita per "
        "il divano. Sono le cose che guardiamo per prime quando veniamo a "
        "fare il sopralluogo.",
        "Ci occupiamo di traslochi completi di appartamenti, case "
        "indipendenti e singole stanze, in città e in tutta la provincia. "
        "Possiamo fare tutto noi, dall'imballaggio al rimontaggio, oppure "
        "solo la parte che vi serve se volete impacchettare da soli.",
    ],
    "cosa_facciamo": [
        "Sopralluogo gratuito per misurare volumi, accessi, piani e ascensori.",
        "Fornitura di scatole, pluriball, nastro, copertine e materiale di "
        "protezione.",
        "Imballaggio di piatti, bicchieri, libri, quadri, lampadari e oggetti "
        "fragili.",
        "Smontaggio di armadi, letti, cucine, librerie e arredi su misura.",
        "Protezione di pavimenti, vani scala e ascensori prima di cominciare.",
        "Servizio di autoscala quando la scala è stretta o il piano è alto.",
        "Trasporto con mezzi propri e personale della ditta.",
        "Rimontaggio dei mobili nella casa nuova e ritiro degli imballaggi "
        "vuoti.",
    ],
    "perche": [
        ("Conosciamo i palazzi di Napoli",
         "Sappiamo dove si può fermare un camion e dove serve il permesso, "
         "quali scale reggono un armadio intero e quali no. Il sopralluogo "
         "serve esattamente a questo: niente sorprese la mattina del "
         "trasloco."),
        ("Chi smonta è chi rimonta",
         "I mobili li smonta e li rimonta la stessa squadra. È il motivo per "
         "cui le ante tornano allineate e non avanzano viti sul pavimento."),
        ("Una sola persona di riferimento",
         "Dal primo telefono alla consegna delle chiavi parlate sempre con "
         "noi. Non c'è un call center in mezzo."),
        ("Preventivo chiaro prima di iniziare",
         "Mettiamo per iscritto cosa è compreso e cosa no. Se durante il "
         "sopralluogo emerge qualcosa che cambia la cifra, ve lo diciamo in "
         "quel momento."),
    ],
    "faq": [
        ("Il sopralluogo è davvero gratuito?",
         "Sì, e non vincola a nulla. Veniamo a vedere casa, prendiamo le "
         "misure e vi lasciamo un preventivo. Se decidete di rivolgervi a "
         "qualcun altro, non dovete niente."),
        ("Posso imballare da solo e farvi fare solo il trasporto?",
         "Certamente. Molti clienti impacchettano libri e vestiti per conto "
         "loro e lasciano a noi i mobili, i fragili e tutto quello che va "
         "smontato. Lo definiamo insieme nel preventivo."),
        ("Cosa succede se al mio piano non c'è l'ascensore?",
         "Valutiamo se conviene salire a mano o usare l'autoscala dal "
         "balcone o dalla finestra. Dipende dal piano, dallo spazio in strada "
         "e da quanti mobili voluminosi ci sono: lo stabiliamo durante il "
         "sopralluogo."),
        ("Quanto tempo prima devo prenotare?",
         "Più margine c'è, meglio riusciamo a darvi il giorno che volete. "
         "Fine mese, inizio mese e sabato sono i periodi più richiesti. "
         "Chiamate appena avete una data indicativa, anche se non è ancora "
         "definitiva."),
    ],
    "correlate": ["/montaggio-mobili-napoli/", "/deposito-mobili-napoli/",
                  "/sgomberi-napoli/"],
}

SERVIZIO_UFFICI = {
    "slug": "traslochi-uffici-napoli",
    "title": "Traslochi uffici e negozi Napoli | Sorgente Traslochi",
    "description": "Trasloco di uffici, studi e negozi a Napoli e provincia, "
                   "organizzato per ridurre i giorni di chiusura. Sopralluogo "
                   "e preventivo gratuiti.",
    "h1": "Traslochi di uffici e negozi a Napoli",
    "intro": [
        "Quando si sposta un ufficio il problema non è il peso delle "
        "scrivanie: è il tempo in cui l'attività resta ferma. Per questo un "
        "trasloco aziendale si progetta prima, stanza per stanza, e spesso si "
        "esegue di sera, di sabato o nei giorni di chiusura.",
        "Ci occupiamo di studi professionali, uffici, ambulatori, negozi e "
        "magazzini a Napoli e in provincia. Numeriamo le postazioni, "
        "etichettiamo scatole e cavi, smontiamo arredi e pareti attrezzate e "
        "rimontiamo tutto nella nuova sede seguendo la piantina che decidiamo "
        "insieme.",
    ],
    "cosa_facciamo": [
        "Sopralluogo nella sede attuale e in quella nuova, con piantina delle "
        "postazioni.",
        "Piano di trasloco con tempi, giorni e ordine delle stanze.",
        "Imballaggio di documenti, archivi e faldoni in scatole numerate.",
        "Smontaggio e rimontaggio di scrivanie, armadi, pareti attrezzate e "
        "scaffalature.",
        "Trasporto di computer, monitor e stampanti con imballi dedicati.",
        "Spostamento di arredi di negozio, espositori, banconi e vetrine.",
        "Lavorazioni fuori orario, di sera o nel fine settimana.",
        "Smaltimento di ciò che non viene portato nella nuova sede.",
    ],
    "perche": [
        ("Lavoriamo quando siete chiusi",
         "Concordiamo la finestra oraria in cui l'attività è ferma e la "
         "rispettiamo. L'obiettivo è che il lunedì mattina si riapra."),
        ("Ogni scatola sa dove va",
         "Numerazione e etichette per stanza e per postazione: chi rientra "
         "trova le proprie cose al proprio posto, non un muro di scatole "
         "anonime."),
        ("Squadre abituate agli arredi tecnici",
         "Pareti attrezzate, banconi e scaffalature metalliche richiedono lo "
         "stesso metodo di un arredo su misura. È il lavoro che facciamo "
         "tutti i giorni."),
        ("Un referente unico per tutta l'operazione",
         "Una sola persona coordina sopralluogo, squadra e consegna, e vi "
         "risponde al telefono anche durante il trasloco."),
    ],
    "faq": [
        ("Potete traslocare fuori dall'orario di lavoro?",
         "Sì. Sera, sabato e giorni di chiusura sono le finestre più "
         "richieste per gli uffici e le concordiamo in fase di preventivo."),
        ("Come gestite l'archivio cartaceo?",
         "Lo imballiamo in scatole numerate seguendo l'ordine degli "
         "scaffali, così al rimontaggio i faldoni tornano nella stessa "
         "sequenza. Le scatole restano chiuse dalla partenza all'arrivo."),
        ("Vi occupate anche di smontare le pareti attrezzate?",
         "Sì, smontiamo e rimontiamo pareti attrezzate, armadiature e "
         "scaffalature. Se la nuova sede ha misure diverse lo verifichiamo "
         "durante il sopralluogo."),
        ("Potete portare via i mobili che non servono più?",
         "Sì, possiamo svuotare la vecchia sede di quello che non viene "
         "trasferito. Lo trattiamo come uno sgombero e lo mettiamo a "
         "preventivo insieme al trasloco."),
    ],
    "correlate": ["/montaggio-mobili-napoli/", "/sgomberi-napoli/",
                  "/deposito-mobili-napoli/"],
}

SERVIZIO_MONTAGGIO = {
    "slug": "montaggio-mobili-napoli",
    "title": "Montaggio e smontaggio mobili Napoli | Sorgente Traslochi",
    "description": "Montaggio e smontaggio di cucine, armadi e arredi su "
                   "misura a Napoli e provincia. Montatori con esperienza su "
                   "arredamento di design.",
    "h1": "Montaggio e smontaggio mobili a Napoli",
    "intro": [
        "Il montaggio è il mestiere da cui veniamo. Prima ancora che "
        "traslochi, per anni abbiamo fatto trasporto e montaggio per i "
        "mobilifici campani: " + ", ".join(MOBILIFICI) + ". Da lì è nata "
        "l'abitudine a lavorare su arredi che non ammettono approssimazione.",
        "Montiamo e smontiamo cucine, armadi a muro, cabine armadio, "
        "librerie, letti e arredi su misura, sia dentro un trasloco sia come "
        "servizio a sé stante. Se avete comprato un mobile e vi serve solo "
        "chi lo monta, è un lavoro che facciamo volentieri.",
    ],
    "cosa_facciamo": [
        "Montaggio di cucine componibili, comprese le regolazioni di ante e "
        "cassetti.",
        "Smontaggio di cucine da trasferire in un'altra casa.",
        "Montaggio e smontaggio di armadi a muro, cabine armadio e "
        "scorrevoli.",
        "Librerie, pareti attrezzate e boiserie.",
        "Letti, reti, testiere e contenitori.",
        "Fissaggio a parete di pensili, mensole e televisori.",
        "Rimontaggio di arredi già smontati da altri.",
        "Piccole sostituzioni di ferramenta e cerniere durante il rimontaggio.",
    ],
    "perche": [
        ("Esperienza su arredo di design",
         "Abbiamo montato arredi di marchi come " +
         ", ".join(MARCHI_ARREDO[:5]) + " e " +
         ", ".join(MARCHI_ARREDO[5:]) + ". Sono mobili con tolleranze "
         "strette, dove un fissaggio fuori squadra si vede subito."),
        ("Smontare pensando a chi rimonta",
         "Ferramenta in sacchetti etichettati, ante numerate, foto dei "
         "passaggi critici. È quello che fa la differenza fra un rimontaggio "
         "di mezza giornata e uno che non finisce mai."),
        ("Attrezzatura nostra",
         "Arriviamo con gli utensili giusti, comprese le attrezzature per "
         "allineare e mettere in bolla, non con un cacciavite e "
         "un'improvvisazione."),
        ("Anche senza trasloco",
         "Il montaggio è un servizio autonomo: potete chiamarci solo per "
         "quello, anche per un singolo mobile."),
    ],
    "faq": [
        ("Montate mobili comprati in un altro negozio?",
         "Sì. Montiamo qualunque arredo, indipendentemente da dove è stato "
         "acquistato. Se avete le istruzioni tenetele da parte, ma nella "
         "maggior parte dei casi non servono."),
        ("Si può smontare e rimontare una cucina in una casa nuova?",
         "Nella maggior parte dei casi sì, ma dipende da com'è fatta e da "
         "come sono disposti gli attacchi nella nuova casa. Veniamo a "
         "vederla e vi diciamo francamente cosa si recupera e cosa no."),
        ("Quanto tempo serve per montare una cucina?",
         "Dipende dalla lunghezza, dal numero di elettrodomestici da "
         "incassare e dallo stato delle pareti. Ve lo diciamo dopo aver "
         "visto il progetto o il mobile: non diamo tempi a scatola chiusa."),
        ("Potete rimontare un mobile smontato da qualcun altro?",
         "Sì, e capita spesso. Se la ferramenta è stata conservata il "
         "lavoro è lineare; se manca qualcosa lo segnaliamo prima di "
         "cominciare."),
    ],
    "correlate": ["/traslochi-abitazioni-napoli/", "/traslochi-uffici-napoli/",
                  "/deposito-mobili-napoli/"],
}

SERVIZIO_SGOMBERI = {
    "slug": "sgomberi-napoli",
    "title": "Sgomberi Napoli | Case, cantine, garage e locali | Sorgente",
    "description": "Sgombero di case, cantine, garage, soffitte e locali "
                   "commerciali a Napoli e provincia. Sopralluogo e preventivo "
                   "gratuiti, locali lasciati puliti.",
    "h1": "Sgomberi a Napoli: case, cantine e locali",
    "intro": [
        "Uno sgombero arriva quasi sempre in un momento complicato: "
        "un'eredità, una casa da riconsegnare al proprietario, una cantina "
        "che non si apriva da anni, un negozio che chiude. Il nostro compito "
        "è toglierlo di mezzo in fretta e senza farvi rimanere in mezzo alla "
        "polvere.",
        "Svuotiamo appartamenti interi, singole stanze, cantine, soffitte, "
        "garage, box e locali commerciali a Napoli e in provincia. Separiamo "
        "ciò che si può ancora usare da ciò che va smaltito e lasciamo i "
        "locali puliti e pronti per la riconsegna.",
    ],
    "cosa_facciamo": [
        "Sopralluogo per valutare volume, accessi e tipo di materiale.",
        "Svuotamento completo di appartamenti, anche disabitati da tempo.",
        "Cantine, soffitte, sottotetti, garage e box.",
        "Locali commerciali, magazzini e depositi.",
        "Smontaggio dei mobili ingombranti prima di portarli via.",
        "Separazione di mobili, elettrodomestici, ingombranti e materiali "
        "diversi.",
        "Messa da parte di documenti, foto e oggetti personali da farvi "
        "ricontrollare.",
        "Pulizia di base dei locali a fine lavoro.",
    ],
    "perche": [
        ("Ci muoviamo in fretta",
         "Per una riconsegna con scadenza il tempo è tutto. Organizziamo la "
         "squadra in modo da chiudere lo sgombero nei giorni concordati."),
        ("Niente va perso senza che lo guardiate",
         "Documenti, fotografie, lettere e piccoli oggetti personali li "
         "mettiamo da parte e ve li facciamo controllare prima di portare "
         "via qualsiasi cosa."),
        ("Sappiamo scendere anche dai palazzi difficili",
         "Cantine strette, scale a chiocciola, vicoli senza sosta: sono la "
         "normalità del nostro lavoro a Napoli."),
        ("Riconsegna pulita",
         "I locali restano vuoti e spazzati, in condizioni da mostrare al "
         "proprietario o all'agenzia."),
    ],
    "faq": [
        ("Come si stabilisce il prezzo di uno sgombero?",
         "Dipende dal volume da portare via, dal piano, dalla presenza "
         "dell'ascensore e dal tipo di materiale. Per questo veniamo sempre a "
         "vedere prima: solo dopo il sopralluogo diamo una cifra."),
        ("Sgomberate anche una cantina o un solo garage?",
         "Sì, gli sgomberi parziali sono richiesti almeno quanto quelli di "
         "una casa intera. Può trattarsi di una sola cantina, di un box o di "
         "una stanza."),
        ("Cosa succede ai mobili ancora in buono stato?",
         "Li teniamo separati dal resto. Se volete destinarli a qualcuno o "
         "recuperarli, ce lo dite prima e li gestiamo di conseguenza."),
        ("Potete sgomberare una casa che devo riconsegnare entro pochi "
         "giorni?",
         "Chiamateci subito e diteci la scadenza. Se la data è stretta "
         "organizziamo il sopralluogo in tempi rapidi e vi diciamo "
         "onestamente se riusciamo a rientrare nei termini."),
    ],
    "correlate": ["/traslochi-abitazioni-napoli/", "/traslochi-uffici-napoli/",
                  "/montaggio-mobili-napoli/"],
}

SERVIZIO_DEPOSITO = {
    "slug": "deposito-mobili-napoli",
    "title": "Deposito mobili Napoli | Custodia temporanea | Sorgente",
    "description": "Deposito temporaneo di mobili e masserizie a Napoli e "
                   "provincia, per i periodi fra un'uscita e un'entrata. "
                   "Ritiro, custodia e riconsegna.",
    "h1": "Deposito mobili a Napoli",
    "intro": [
        "Fra la consegna delle chiavi della casa vecchia e l'ingresso in "
        "quella nuova passa spesso qualche settimana: i lavori non sono "
        "finiti, il rogito slitta, l'affitto scade prima. In quei casi i "
        "mobili devono stare da qualche parte.",
        "Ritiriamo l'arredamento, lo imballiamo e lo custodiamo per il tempo "
        "che serve, poi lo riportiamo e lo rimontiamo nella nuova casa. È lo "
        "stesso servizio che usiamo quando un trasloco si svolge in due "
        "tempi.",
    ],
    "cosa_facciamo": [
        "Smontaggio e imballaggio dei mobili prima del ritiro.",
        "Ritiro presso l'abitazione o l'ufficio con mezzi nostri.",
        "Inventario di quanto viene preso in custodia.",
        "Custodia dei mobili per il periodo concordato.",
        "Riconsegna nella data che stabilite, anche in una città diversa "
        "della provincia.",
        "Rimontaggio degli arredi all'arrivo.",
        "Deposito parziale: solo alcuni mobili, mentre il resto va subito "
        "nella casa nuova.",
    ],
    "perche": [
        ("Un interlocutore solo",
         "Ritiro, custodia e riconsegna li gestisce la stessa ditta che fa il "
         "trasloco: non dovete coordinare due fornitori diversi."),
        ("Imballaggio pensato per la sosta",
         "Un mobile che resta fermo per settimane va protetto diversamente da "
         "uno che viaggia per un'ora. Lo imballiamo di conseguenza."),
        ("Inventario di quello che lasciate",
         "Sapete esattamente cosa è stato preso in carico e cosa vi torna "
         "indietro."),
        ("Date flessibili",
         "Se i lavori nella casa nuova si allungano, si concorda una "
         "riconsegna più avanti."),
    ],
    "faq": [
        ("Per quanto tempo posso lasciare i mobili?",
         "Dai pochi giorni ai mesi. Il periodo si concorda in anticipo e si "
         "può prolungare se i tempi della casa nuova cambiano: basta "
         "avvisarci."),
        ("Posso depositare solo una parte dei mobili?",
         "Sì. Capita spesso che vada in deposito solo l'arredo di una stanza "
         "o quello che non entra subito nella casa nuova."),
        ("Chi porta i mobili in deposito e chi li riporta?",
         "Ce ne occupiamo noi in entrambe le direzioni, con i nostri mezzi e "
         "il nostro personale."),
        ("I mobili vengono smontati prima del deposito?",
         "Gli arredi voluminosi sì, perché occupano meno spazio e si "
         "proteggono meglio. Al ritorno li rimonta la stessa squadra che li "
         "ha smontati."),
    ],
    "correlate": ["/traslochi-abitazioni-napoli/", "/montaggio-mobili-napoli/",
                  "/traslochi-uffici-napoli/"],
}

PAGINE_SERVIZIO = [
    SERVIZIO_ABITAZIONI, SERVIZIO_UFFICI, SERVIZIO_MONTAGGIO,
    SERVIZIO_SGOMBERI, SERVIZIO_DEPOSITO,
]

# --------------------------------------------------------------------------
# Zone servite - un testo originale per ogni area, mai copiato fra le sezioni
# --------------------------------------------------------------------------

ZONE = [
    {
        "nome": "Napoli città",
        "id": "napoli",
        "testo": [
            "A Napoli il trasloco si decide in strada prima che in casa. "
            "Fra il centro storico, il Vomero, Chiaia, il Vasto, la Sanità e "
            "i quartieri collinari cambia tutto: la larghezza dei vicoli, la "
            "pendenza, la possibilità di fermare un camion, l'altezza degli "
            "androni. Lavoriamo qui da tre generazioni e la prima cosa che "
            "guardiamo durante il sopralluogo è proprio come si arriva al "
            "portone.",
            "Copriamo tutti i quartieri: centro storico e Chiaia, Vomero e "
            "Arenella, Fuorigrotta e Bagnoli, Posillipo, Soccavo e Pianura, "
            "Vicaria, Poggioreale e Zona Industriale, Secondigliano, "
            "Scampia, Miano, Chiaiano, Ponticelli, Barra e San Giovanni a "
            "Teduccio. Per le zone a traffico limitato e per le occupazioni "
            "di suolo pubblico vi diciamo in anticipo cosa serve e quanto "
            "tempo prima va richiesto.",
        ],
    },
    {
        "nome": "Casoria",
        "id": "casoria",
        "testo": [
            "A Casoria lavoriamo soprattutto su condomini degli anni Settanta "
            "e Ottanta: ascensori piccoli, vani scala stretti e cortili "
            "interni in cui il camion entra solo se manovra bene. Sono "
            "edifici che conosciamo, e sappiamo in partenza quando conviene "
            "portare l'autoscala invece di insistere con le scale.",
            "La vicinanza con Napoli nord rende frequenti i traslochi in "
            "giornata verso la città e verso gli altri comuni intorno. "
            "Seguiamo anche uffici e attività commerciali della zona, con "
            "lavorazioni concentrate nei giorni di chiusura.",
        ],
    },
    {
        "nome": "Afragola",
        "id": "afragola",
        "testo": [
            "Ad Afragola capita spesso di spostare arredamento completo di "
            "case familiari: cucine su misura, camere da letto importanti, "
            "armadi a ponte. Sono i lavori in cui conta chi smonta, perché "
            "un mobile di quel tipo o torna su preciso o non torna su.",
            "Serviamo sia il centro sia le zone più recenti verso la "
            "stazione dell'alta velocità. Per chi si trasferisce a Napoli o "
            "nei comuni vicini organizziamo il trasloco in un'unica giornata, "
            "con rimontaggio lo stesso pomeriggio quando i volumi lo "
            "permettono.",
        ],
    },
    {
        "nome": "Arzano",
        "id": "arzano",
        "testo": [
            "Arzano è un comune compatto, con strade strette nel centro e "
            "palazzi senza cortile. Il punto critico è quasi sempre la sosta "
            "del mezzo: si risolve scegliendo l'orario giusto e, dove serve, "
            "chiedendo per tempo l'occupazione di suolo pubblico.",
            "Oltre ai traslochi di abitazioni ci chiamano per sgomberi di "
            "cantine e garage e per montaggi di cucine e armadi acquistati "
            "nei mobilifici della zona, che è il lavoro da cui la nostra "
            "attività è nata.",
        ],
    },
    {
        "nome": "Casalnuovo di Napoli",
        "id": "casalnuovo",
        "testo": [
            "A Casalnuovo e nelle frazioni di Licignano e Tavernanova ci "
            "muoviamo fra palazzine recenti e case indipendenti. Le prime "
            "hanno ascensori moderni ma spesso vincoli di orario per i "
            "carichi; le seconde hanno scale interne che complicano la "
            "discesa dei mobili grandi.",
            "È una zona da cui partono molti trasferimenti verso Napoli est "
            "e verso i comuni vesuviani: sono tragitti brevi, che permettono "
            "di concentrare carico, viaggio e rimontaggio nello stesso "
            "giorno.",
        ],
    },
    {
        "nome": "Giugliano in Campania",
        "id": "giugliano",
        "testo": [
            "Giugliano è uno dei comuni più estesi della provincia e le "
            "distanze interne contano: fra il centro, Varcaturo, Lago Patria "
            "e la fascia costiera i tempi di percorrenza cambiano parecchio. "
            "Ne teniamo conto quando organizziamo la giornata, perché un "
            "viaggio in più del previsto sposta l'orario di tutto il resto.",
            "Sulla costa seguiamo anche seconde case e appartamenti in "
            "affitto stagionale, con traslochi parziali e periodi di deposito "
            "fra un'occupazione e l'altra.",
        ],
    },
    {
        "nome": "Marano di Napoli",
        "id": "marano",
        "testo": [
            "Marano è in collina e il dislivello si sente: strade in "
            "pendenza, rampe d'accesso ripide, cortili in quota. Per i mobili "
            "voluminosi la scelta fra scala e autoscala qui va fatta con "
            "attenzione, e il sopralluogo serve anche a verificare che il "
            "mezzo giusto possa effettivamente arrivare sotto casa.",
            "Lavoriamo sia nel centro sia nelle zone residenziali verso "
            "Quarto e Calvizzano, con traslochi verso Napoli e verso gli "
            "altri comuni dell'area flegrea.",
        ],
    },
    {
        "nome": "Pozzuoli e Campi Flegrei",
        "id": "pozzuoli",
        "testo": [
            "A Pozzuoli, Bacoli, Monte di Procida e Quarto il tratto comune "
            "è la conformazione del terreno: rione Terra e la zona alta, le "
            "discese verso il porto, le case sulla costa raggiungibili solo "
            "da strade strette. Ogni trasloco qui si progetta sul posto, "
            "guardando dove si può fermare il mezzo e quanti metri di "
            "trasporto a mano restano da fare.",
            "Seguiamo abitazioni, attività del porto e locali commerciali. "
            "Per le case vicine al mare usiamo protezioni aggiuntive sugli "
            "imballaggi quando i mobili devono restare fermi in deposito.",
        ],
    },
    {
        "nome": "Portici",
        "id": "portici",
        "testo": [
            "Portici è uno dei comuni con la densità abitativa più alta "
            "d'Italia, e si vede: palazzi affacciati direttamente sul corso, "
            "poco spazio per fermarsi, ascensori piccoli. Per lavorare bene "
            "qui serve programmare l'orario, di solito la prima mattina, "
            "quando il traffico sul corso Garibaldi è ancora gestibile.",
            "Nella parte alta, verso la Reggia e il parco, ci sono invece "
            "appartamenti in edifici storici con soffitti alti e scaloni: "
            "sono contesti in cui la protezione di pavimenti e ringhiere è "
            "parte del lavoro, non un accessorio.",
        ],
    },
    {
        "nome": "Ercolano",
        "id": "ercolano",
        "testo": [
            "A Ercolano convivono il centro fitto vicino agli scavi e le "
            "zone residenziali verso il Vesuvio. Nel primo caso il problema "
            "è l'accesso, nel secondo la pendenza delle strade che salgono "
            "verso il parco nazionale.",
            "Facciamo traslochi di case e sgomberi di cantine e depositi, e "
            "ci capita spesso di lavorare in ville con giardino dove il "
            "camion resta al cancello: in quei casi mettiamo in conto il "
            "tratto a spalla e lo diciamo chiaramente nel preventivo.",
        ],
    },
    {
        "nome": "Torre del Greco",
        "id": "torre-del-greco",
        "testo": [
            "Torre del Greco si sviluppa in lunghezza fra il mare e la "
            "montagna, e la differenza fra un trasloco in zona porto e uno "
            "nella parte alta è notevole. Lo verifichiamo sempre durante il "
            "sopralluogo, perché cambia il mezzo da mandare e il tempo da "
            "preventivare.",
            "Oltre alle abitazioni seguiamo laboratori e attività "
            "artigianali della zona, con spostamenti di banchi da lavoro, "
            "scaffalature e materiali che richiedono imballaggi su misura.",
        ],
    },
    {
        "nome": "Pomigliano d'Arco",
        "id": "pomigliano",
        "testo": [
            "A Pomigliano d'Arco lavoriamo molto su appartamenti in "
            "palazzine con parcheggio interno, che è la condizione migliore "
            "per un trasloco: il mezzo entra, la distanza fino all'ascensore "
            "è breve e la giornata fila.",
            "La zona industriale genera invece richieste di tipo diverso: "
            "uffici da trasferire, archivi da spostare, magazzini da "
            "svuotare. Sono lavori che concordiamo fuori orario per non "
            "fermare l'attività.",
        ],
    },
]

# Collegamenti interni: frasi gia' presenti nei testi delle zone che
# diventano link alle pagine servizio. Si aggancia il link a un'espressione
# che c'e' davvero, invece di aggiungere in fondo a ogni sezione la stessa
# riga di collegamenti: quella sarebbe la classica coda uguale per tutti.
LINK_ZONE = {
    "casoria": [
        ("uffici e attività commerciali", "/traslochi-uffici-napoli/"),
    ],
    "afragola": [
        ("cucine su misura", "/montaggio-mobili-napoli/"),
    ],
    "arzano": [
        ("sgomberi di cantine e garage", "/sgomberi-napoli/"),
        ("montaggi di cucine e armadi", "/montaggio-mobili-napoli/"),
    ],
    "giugliano": [
        ("periodi di deposito", "/deposito-mobili-napoli/"),
    ],
    "pozzuoli": [
        ("deposito", "/deposito-mobili-napoli/"),
    ],
    "portici": [
        ("appartamenti in edifici storici", "/traslochi-abitazioni-napoli/"),
    ],
    "ercolano": [
        ("traslochi di case", "/traslochi-abitazioni-napoli/"),
        ("sgomberi di cantine e depositi", "/sgomberi-napoli/"),
    ],
    "torre-del-greco": [
        ("laboratori e attività artigianali", "/traslochi-uffici-napoli/"),
    ],
    "pomigliano": [
        ("uffici da trasferire", "/traslochi-uffici-napoli/"),
        ("magazzini da svuotare", "/sgomberi-napoli/"),
    ],
    "casalnuovo": [
        ("case indipendenti", "/traslochi-abitazioni-napoli/"),
    ],
    "marano": [
        ("mobili voluminosi", "/traslochi-abitazioni-napoli/"),
    ],
}

PAGINA_ZONE = {
    "slug": "zone-servite",
    "title": "Zone servite: Napoli e provincia | Sorgente Traslochi",
    "description": "Traslochi, sgomberi e montaggio mobili a Napoli e in "
                   "provincia: Casoria, Afragola, Arzano, Casalnuovo, "
                   "Giugliano, Marano, Pozzuoli, Portici, Ercolano e altri.",
    "h1": "Dove lavoriamo: Napoli e provincia",
    "intro": [
        "Lavoriamo a Napoli città e in tutta la provincia. Sotto trovate le "
        "aree in cui interveniamo più spesso, con quello che cambia "
        "concretamente da una zona all'altra: accessi, pendenze, spazi per "
        "fermare il mezzo.",
        "Se il vostro comune non è in elenco, chiamateci comunque: la "
        "provincia è ampia e ci spostiamo anche fuori dalle aree qui "
        "descritte.",
    ],
}

# --------------------------------------------------------------------------
# Chi siamo
# --------------------------------------------------------------------------

CHI_SIAMO = {
    "slug": "chi-siamo",
    "title": "Chi siamo | Sorgente Traslochi, Napoli dal 1965",
    "description": "Sorgente Traslochi: impresa familiare napoletana attiva "
                   "dal 1965 nei trasporti, nei traslochi e nel montaggio di "
                   "arredi, anche di design.",
    "h1": "Chi siamo",
    "sezioni": [
        ("Una famiglia, un mestiere",
         ["Sorgente Traslochi nasce nel 1965 a Napoli come impresa di "
          "trasporti. Da allora il mestiere è passato di mano dentro la "
          "stessa famiglia, e con esso un modo di lavorare che non è "
          "cambiato: si va a vedere prima, si dice quello che si può fare, "
          "si fa quello che si è detto.",
          "Oggi siamo una ditta di traslochi a tutto tondo, ma il punto di "
          "partenza resta il trasporto e il montaggio dei mobili. È la parte "
          "del lavoro che conosciamo meglio ed è il motivo per cui molti "
          "clienti ci chiamano anche solo per smontare e rimontare un "
          "arredo."]),
        ("Dai mobilifici alle case",
         ["Per anni abbiamo fatto trasporto e montaggio per mobilifici "
          "campani come " + ", ".join(MOBILIFICI[:-1]) + " e " +
          MOBILIFICI[-1] + ". Consegnare e montare arredi per conto di un "
          "negozio significa entrare ogni giorno in case diverse, con "
          "problemi diversi, e avere pochissimo margine di errore: il mobile "
          "è nuovo e il cliente sta guardando.",
          "In quel lavoro abbiamo montato arredi di marchi come " +
          ", ".join(MARCHI_ARREDO[:-1]) + " e " + MARCHI_ARREDO[-1] + ". "
          "Sono cucine e arredi su misura con tolleranze strette, dove il "
          "montaggio è parte del prodotto. Quell'abitudine alla precisione "
          "ce la siamo portata dentro i traslochi."]),
        ("Come lavoriamo",
         ["Facciamo sempre il sopralluogo prima di dare un prezzo, e il "
          "sopralluogo è gratuito. Non diamo cifre al telefono su lavori che "
          "non abbiamo visto: sarebbe comodo per noi e rischioso per voi.",
          "Il preventivo è scritto e dice cosa comprende. Se durante il "
          "lavoro emerge qualcosa che non era previsto, ve lo diciamo in quel "
          "momento e decidete voi, non lo scoprite alla fine.",
          "Le squadre sono nostre. Non subappaltiamo i traslochi ad altri e "
          "non montiamo squadre improvvisate per una giornata: le persone che "
          "trovate a casa vostra lavorano con noi."]),
    ],
}

# --------------------------------------------------------------------------
# Preventivo
# --------------------------------------------------------------------------

PREVENTIVO = {
    "slug": "preventivo",
    "title": "Preventivo gratuito traslochi Napoli | Sorgente Traslochi",
    "description": "Chiedete un preventivo gratuito per trasloco, sgombero o "
                   "montaggio mobili a Napoli e provincia. Modulo online, "
                   "telefono e WhatsApp: 347 263 6504.",
    "h1": "Preventivo gratuito",
    "intro": [
        "Il preventivo e il sopralluogo non costano nulla e non vi impegnano. "
        "Più informazioni ci date qui sotto, più la prima risposta sarà "
        "precisa: per i traslochi completi passiamo comunque a vedere di "
        "persona prima di confermare una cifra.",
        "Se preferite parlarne subito, chiamate o scrivete su WhatsApp: "
        "rispondiamo noi, non un centralino.",
    ],
}

# --------------------------------------------------------------------------
# Privacy
# --------------------------------------------------------------------------

PRIVACY = {
    "slug": "privacy",
    "title": "Privacy e cookie | Sorgente Traslochi",
    "description": "Informativa privacy e cookie di Sorgente Traslochi: quali "
                   "dati raccogliamo tramite il modulo di preventivo, come li "
                   "usiamo e come esercitare i vostri diritti.",
    "h1": "Privacy e cookie",
}
