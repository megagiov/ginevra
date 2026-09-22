#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generatore del sito Sorgente Traslochi.

    python3 build.py

Legge i testi da content.py e scrive in dist/ un sito statico completo:
HTML, CSS, JS, favicon, robots.txt e sitemap.xml. Nessuna dipendenza esterna.
dist/ e' la cartella da pubblicare su Cloudflare Pages.
"""

import html
import json
import os
import re
import shutil
import struct
import zlib
from datetime import date

import content as C

A = C.AZIENDA
BASE = C.BASE_URL.rstrip("/")
QUI = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(QUI, "dist")
SRC = os.path.join(QUI, "src")

TEL_HREF = "tel:" + A["telefono_tel"]
WA_HREF = "https://wa.me/%s?text=%s" % (A["whatsapp"], C.WHATSAPP_MSG)
MAIL_HREF = "mailto:" + A["email"]
INDIRIZZO = "%s, %s %s (%s)" % (A["via"], A["cap"], A["citta"], A["provincia"])

# Pagine registrate per sitemap e navigazione interna.
SITEMAP = []


def e(t):
    """Escape per il testo inserito nell'HTML."""
    return html.escape(t, quote=False)


def url(path):
    return BASE + path


# --------------------------------------------------------------------------
# Frammenti comuni
# --------------------------------------------------------------------------

LOGO_SVG = (
    '<svg width="38" height="38" viewBox="0 0 38 38" aria-hidden="true" focusable="false">'
    '<rect width="38" height="38" rx="9" fill="#0d2440"/>'
    '<path d="M7 24V15l7-4 7 4v9z" fill="#fff"/>'
    '<path d="M22 24v-7h6l3 3v4z" fill="#ef7622"/>'
    '<circle cx="13" cy="25" r="2.6" fill="#0d2440" stroke="#fff" stroke-width="1.4"/>'
    '<circle cx="27" cy="25" r="2.6" fill="#0d2440" stroke="#fff" stroke-width="1.4"/>'
    "</svg>"
)


def header(percorso):
    voci = []
    for href, label in C.NAV:
        corrente = ' aria-current="page"' if href == percorso else ""
        voci.append('<li><a href="%s"%s>%s</a></li>' % (href, corrente, e(label)))
    voci.append('<li><a href="/preventivo/" class="btn btn-arancio">Preventivo gratuito</a></li>')
    return """<a class="skip" href="#contenuto">Vai al contenuto</a>
<div class="topbar"><div class="wrap">
  <span>Traslochi e montaggio mobili a Napoli e provincia, dal 1965</span>
  <span><a href="%s">Chiama il %s</a></span>
</div></div>
<header class="head"><div class="wrap">
  <a class="logo" href="/">%s<span class="lt"><b>Sorgente Traslochi</b><span class="sub">Napoli e provincia</span></span></a>
  <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="menu">Menu</button>
  <nav class="nav" id="menu" aria-label="Navigazione principale"><ul>%s</ul></nav>
</div></header>""" % (TEL_HREF, e(A["telefono_display"]), LOGO_SVG, "".join(voci))


def breadcrumb(voci):
    """voci: lista di (href, testo). L'ultima e' la pagina corrente."""
    if not voci:
        return "", None
    li = ['<li><a href="/">Home</a></li>']
    elementi = [{"@type": "ListItem", "position": 1, "name": "Home", "item": url("/")}]
    for i, (href, testo) in enumerate(voci, start=2):
        ultimo = i == len(voci) + 1
        if ultimo:
            li.append("<li>%s</li>" % e(testo))
        else:
            li.append('<li><a href="%s">%s</a></li>' % (href, e(testo)))
        elementi.append({"@type": "ListItem", "position": i, "name": testo,
                         "item": url(href)})
    markup = ('<nav class="breadcrumb" aria-label="Percorso"><div class="wrap">'
              "<ol>%s</ol></div></nav>" % "".join(li))
    return markup, {"@context": "https://schema.org", "@type": "BreadcrumbList",
                    "itemListElement": elementi}


def bottoni(chiaro=False):
    cls = "btn-chiaro" if chiaro else "btn-vuoto"
    return """<div class="btn-riga">
  <a class="btn btn-arancio" href="%s">Chiama %s</a>
  <a class="btn btn-wa" href="%s" rel="noopener" target="_blank">Scrivi su WhatsApp</a>
  <a class="btn %s" href="/preventivo/">Preventivo gratuito</a>
</div>""" % (TEL_HREF, e(A["telefono_display"]), WA_HREF, cls)


def cta_finale(titolo, testo):
    return """<section class="cta-finale"><div class="wrap stretto">
  <h2>%s</h2><p>%s</p>%s
</div></section>""" % (e(titolo), e(testo), bottoni(chiaro=True))


def placeholder(titolo, nota):
    """Segnaposto immagine: da sostituire con <img> quando ci sono le foto."""
    return ('<div class="ph"><b>%s</b><span>%s</span>'
            "<span>Segnaposto: sostituire con foto reale in WebP</span></div>"
            % (e(titolo), e(nota)))


def footer():
    servizi = "".join('<li><a href="%s">%s</a></li>' % (s["url"], e(s["titolo"]))
                      for s in C.SERVIZI)
    return """<footer class="foot"><div class="wrap">
  <div class="cols">
    <div class="col">
      <h2>Sorgente Traslochi</h2>
      <p>
        %(ragione)s<br>
        %(via)s<br>%(cap)s %(citta)s (%(prov)s)<br>
        Tel. e WhatsApp: <a href="%(tel)s">%(telefono)s</a><br>
        <a href="%(mail)s">%(email)s</a><br>
        Orari: %(orari)s
      </p>
      <p><a href="%(maps)s" rel="noopener" target="_blank">Vedi su Google Maps</a></p>
    </div>
    <div class="col">
      <h3>Servizi</h3>
      <ul>%(servizi)s</ul>
    </div>
    <div class="col">
      <h3>Informazioni</h3>
      <ul>
        <li><a href="/zone-servite/">Zone servite</a></li>
        <li><a href="/chi-siamo/">Chi siamo</a></li>
        <li><a href="/preventivo/">Preventivo gratuito</a></li>
        <li><a href="/privacy/">Privacy e cookie</a></li>
      </ul>
      <h3>Seguiteci</h3>
      <p class="social">
        <a href="%(fb)s" rel="noopener" target="_blank">Facebook</a>
        <a href="%(ig)s" rel="noopener" target="_blank">Instagram</a>
      </p>
    </div>
  </div>
  <p class="legale">
    %(ragione)s &mdash; P.IVA %(piva)s &mdash; %(via)s, %(cap)s %(citta)s (%(prov)s).
    Tutti i diritti riservati. <a href="/privacy/">Privacy e cookie</a>.
  </p>
</div></footer>
<div class="barra">
  <a href="%(tel)s">Chiama</a>
  <a class="wa" href="%(wa)s" rel="noopener" target="_blank">WhatsApp</a>
</div>
<script src="/script.js" defer></script>""" % {
        "ragione": e(A["ragione_sociale"]), "via": e(A["via"]), "cap": A["cap"],
        "citta": e(A["citta"]), "prov": A["provincia"], "tel": TEL_HREF,
        "telefono": e(A["telefono_display"]), "mail": MAIL_HREF,
        "email": e(A["email"]), "orari": e(A["orari"]), "maps": A["maps"],
        "servizi": servizi, "fb": A["facebook"], "ig": A["instagram"],
        "piva": e(A["piva"]), "wa": WA_HREF,
    }


# --------------------------------------------------------------------------
# Dati strutturati
# --------------------------------------------------------------------------

def schema_azienda():
    return {
        "@context": "https://schema.org",
        "@type": "MovingCompany",
        "@id": url("/#azienda"),
        "name": A["nome"],
        "url": url("/"),
        "telephone": A["telefono_tel"],
        "email": A["email"],
        "image": url("/og-sorgente-traslochi.png"),
        "logo": url("/favicon.svg"),
        "description": ("Impresa familiare napoletana attiva dal 1965: "
                        "traslochi di case e uffici, montaggio e smontaggio "
                        "mobili, sgomberi e deposito a Napoli e provincia."),
        "foundingDate": "1965",
        "priceRange": "$$",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": A["via"],
            "postalCode": A["cap"],
            "addressLocality": A["citta"],
            "addressRegion": A["provincia"],
            "addressCountry": "IT",
        },
        "geo": {"@type": "GeoCoordinates", "latitude": A["lat"], "longitude": A["lon"]},
        "hasMap": A["maps"],
        "areaServed": [{"@type": "City", "name": z["nome"]} for z in C.ZONE],
        "sameAs": [A["maps"], A["facebook"], A["instagram"]],
        "makesOffer": [
            {"@type": "Offer", "itemOffered": {"@type": "Service",
             "name": s["titolo"], "url": url(s["url"])}}
            for s in C.SERVIZI
        ],
    }


def schema_faq(faq):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": r}}
            for q, r in faq
        ],
    }


def jsonld(*blocchi):
    out = []
    for b in blocchi:
        if b:
            out.append('<script type="application/ld+json">%s</script>'
                       % json.dumps(b, ensure_ascii=False, separators=(",", ":")))
    return "\n".join(out)


# --------------------------------------------------------------------------
# Scheletro della pagina
# --------------------------------------------------------------------------

DOC = """<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{descr}">
<link rel="canonical" href="{canon}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Sorgente Traslochi">
<meta property="og:locale" content="it_IT">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{descr}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{og}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0d2440">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/favicon.svg">
<link rel="stylesheet" href="/style.css">
{schema}
</head>
<body>
{header}
{breadcrumb}
<main id="contenuto">
{corpo}
</main>
{footer}
</body>
</html>
"""


def scrivi(slug, titolo, descrizione, corpo, schema_blocchi=(), briciole=None,
           priorita="0.7"):
    percorso = "/" if slug == "" else "/%s/" % slug
    bc_markup, bc_schema = breadcrumb(briciole or [])
    doc = DOC.format(
        title=e(titolo), descr=e(descrizione), canon=url(percorso),
        og=url("/og-sorgente-traslochi.png"),
        schema=jsonld(*(list(schema_blocchi) + [bc_schema])),
        header=header(percorso), breadcrumb=bc_markup, corpo=corpo,
        footer=footer(),
    )
    cartella = DIST if slug == "" else os.path.join(DIST, slug)
    os.makedirs(cartella, exist_ok=True)
    with open(os.path.join(cartella, "index.html"), "w", encoding="utf-8") as f:
        f.write(doc)
    SITEMAP.append((percorso, priorita))
    return percorso


# --------------------------------------------------------------------------
# Home
# --------------------------------------------------------------------------

def costruisci_home():
    h = C.HOME
    fiducia = "".join("<div><b>%s</b><span>%s</span></div>" % (e(t), e(d))
                      for t, d in h["fiducia"])
    servizi = "".join(
        '<article class="card"><h3><a href="%s">%s</a></h3><p>%s</p>'
        '<a class="vai" href="%s">Scopri di pi&ugrave;</a></article>'
        % (s["url"], e(s["titolo"]), e(s["sommario"]), s["url"])
        for s in C.SERVIZI)
    passi = "".join("<li><b>%s</b>%s</li>" % (e(t), e(d))
                    for t, d in h["come_funziona"])
    zone_link = ", ".join('<a href="/zone-servite/#%s">%s</a>' % (z["id"], e(z["nome"]))
                          for z in C.ZONE)
    chi = "".join("<p>%s</p>" % e(p) for p in h["chi_siamo_breve"])
    marchi = ", ".join(C.MARCHI_ARREDO)
    mobilifici = ", ".join(C.MOBILIFICI)

    corpo = """<section class="hero"><div class="wrap"><div class="due">
  <div>
    <h1>%(h1)s</h1>
    <p class="sub">%(sub)s</p>
    %(btn)s
  </div>
  <div class="foto">%(ph)s</div>
  </div>
  <div class="fiducia">%(fiducia)s</div>
</div></section>

<section><div class="wrap stretto">
  <p class="occhiello">Chi siamo</p>
  <h2>Un'impresa familiare napoletana</h2>
  %(chi)s
  <p><a href="/chi-siamo/">Leggi la nostra storia</a></p>
</div></section>

<section class="tenue"><div class="wrap">
  <p class="occhiello">Servizi</p>
  <h2>Cosa facciamo</h2>
  <div class="griglia griglia-3">%(servizi)s</div>
</div></section>

<section><div class="wrap stretto">
  <p class="occhiello">Arredamento di design</p>
  <h2>Montatori abituati agli arredi che non perdonano</h2>
  <p>Prima ancora dei traslochi abbiamo fatto trasporto e montaggio per i
     mobilifici campani: %(mobilifici)s. Consegnare per conto di un negozio
     vuol dire entrare ogni giorno in case diverse e non avere margine di
     errore.</p>
  <p>In quel lavoro abbiamo montato arredi di marchi come %(marchi)s: cucine e
     mobili su misura con tolleranze strette, dove il montaggio fa parte del
     prodotto. &Egrave; la stessa cura che mettiamo quando smontiamo e
     rimontiamo l&#8217;arredamento di casa vostra.</p>
  <p><a href="/montaggio-mobili-napoli/">Vedi il servizio di montaggio
     mobili</a></p>
</div></section>

<section class="tenue"><div class="wrap stretto">
  <p class="occhiello">Come funziona</p>
  <h2>Dal primo telefono ai mobili al loro posto</h2>
  <ol class="passi">%(passi)s</ol>
</div></section>

<section><div class="wrap stretto">
  <p class="occhiello">Zone servite</p>
  <h2>Napoli e provincia</h2>
  <p>Lavoriamo in tutti i quartieri di Napoli e nei comuni della provincia:
     %(zone)s.</p>
  <p><a href="/zone-servite/">Vedi tutte le zone servite</a></p>
</div></section>

<section class="tenue"><div class="wrap stretto">
  <p class="occhiello">Recensioni</p>
  <h2>Cosa dicono i clienti</h2>
  <div class="griglia">
    <div class="recensione"><p class="stelle" aria-hidden="true">&#9733;&#9733;&#9733;&#9733;&#9733;</p>
      <p>[SEGNAPOSTO &mdash; inserire qui una recensione reale presa dalla
         scheda Google, con nome e data.]</p></div>
    <div class="recensione"><p class="stelle" aria-hidden="true">&#9733;&#9733;&#9733;&#9733;&#9733;</p>
      <p>[SEGNAPOSTO &mdash; inserire qui una seconda recensione reale.]</p></div>
  </div>
  <p class="nota">%(recnota)s
     <a href="%(maps)s" rel="noopener" target="_blank">Lascia una recensione su
     Google</a>.</p>
</div></section>

%(cta)s""" % {
        "h1": e(h["h1"]), "sub": e(h["sottotitolo"]), "btn": bottoni(chiaro=True),
        "ph": placeholder("Foto squadra e furgone",
                          "Suggerita: il mezzo davanti a un palazzo napoletano"),
        "fiducia": fiducia, "chi": chi, "servizi": servizi,
        "mobilifici": e(mobilifici), "marchi": e(marchi), "passi": passi,
        "zone": zone_link, "recnota": e(h["recensioni_nota"]), "maps": A["maps"],
        "cta": cta_finale("Serve un preventivo?",
                          "Sopralluogo e preventivo sono gratuiti e non "
                          "impegnano a nulla. Chiamate, scrivete su WhatsApp "
                          "o compilate il modulo: rispondiamo noi."),
    }
    scrivi("", h["title"], h["description"], corpo,
           schema_blocchi=[schema_azienda()], briciole=None, priorita="1.0")


# --------------------------------------------------------------------------
# Pagine servizio
# --------------------------------------------------------------------------

def costruisci_servizio(p):
    intro = "".join("<p>%s</p>" % e(t) for t in p["intro"])
    cosa = "".join("<li>%s</li>" % e(t) for t in p["cosa_facciamo"])
    perche = "".join("<div><b>%s</b><p>%s</p></div>" % (e(t), e(d))
                     for t, d in p["perche"])
    faq = "".join(
        "<details><summary>%s</summary><p>%s</p></details>" % (e(q), e(r))
        for q, r in p["faq"])
    titoli = {s["url"]: s["titolo"] for s in C.SERVIZI}
    correlate = " &middot; ".join('<a href="%s">%s</a>' % (u, e(titoli[u]))
                                  for u in p["correlate"])

    corpo = """<section><div class="wrap stretto">
  <h1>%(h1)s</h1>
  %(intro)s
  %(btn)s
</div></section>

<section class="tenue"><div class="wrap stretto">
  <h2>Cosa facciamo</h2>
  <ul class="elenco">%(cosa)s</ul>
  %(ph)s
</div></section>

<section><div class="wrap stretto">
  <h2>Perch&eacute; sceglierci</h2>
  <div class="motivi">%(perche)s</div>
</div></section>

<section class="tenue"><div class="wrap stretto faq">
  <h2>Domande frequenti</h2>
  %(faq)s
</div></section>

<section><div class="wrap stretto interne">
  <h2>Dove interveniamo</h2>
  <p>Operiamo a Napoli citt&agrave; e in tutta la provincia: vedi l&#8217;elenco
     completo delle <a href="/zone-servite/">zone servite</a>.</p>
  <p><strong>Altri servizi:</strong> %(correlate)s</p>
</div></section>

%(cta)s""" % {
        "h1": e(p["h1"]), "intro": intro, "btn": bottoni(), "cosa": cosa,
        "ph": placeholder("Foto del servizio",
                          "Suggerita: una fase reale di questo lavoro"),
        "perche": perche, "faq": faq, "correlate": correlate,
        "cta": cta_finale("Parliamone senza impegno",
                          "Raccontateci cosa dovete spostare: vi diciamo "
                          "subito come lo faremmo e quanto costa."),
    }
    scrivi(p["slug"], p["title"], p["description"], corpo,
           schema_blocchi=[schema_faq(p["faq"])],
           briciole=[("/%s/" % p["slug"], p["h1"])], priorita="0.9")


# --------------------------------------------------------------------------
# Zone servite
# --------------------------------------------------------------------------

def costruisci_zone():
    p = C.PAGINA_ZONE
    indice = " &middot; ".join('<a href="#%s">%s</a>' % (z["id"], e(z["nome"]))
                               for z in C.ZONE)
    sezioni = []
    for z in C.ZONE:
        testo = "".join("<p>%s</p>" % e(t) for t in z["testo"])
        sezioni.append(
            '<div class="zona" id="%s"><h2>%s</h2>%s</div>' % (z["id"], e(z["nome"]), testo))
    corpo = """<section><div class="wrap stretto">
  <h1>%(h1)s</h1>
  %(intro)s
  <p class="interne"><strong>Vai direttamente a:</strong> %(indice)s</p>
  %(btn)s
</div></section>

<section class="tenue"><div class="wrap stretto">
  %(sezioni)s
</div></section>

<section><div class="wrap stretto interne">
  <h2>Servizi disponibili in tutte le zone</h2>
  <ul class="elenco">%(servizi)s</ul>
</div></section>

%(cta)s""" % {
        "h1": e(p["h1"]),
        "intro": "".join("<p>%s</p>" % e(t) for t in p["intro"]),
        "indice": indice, "btn": bottoni(), "sezioni": "".join(sezioni),
        "servizi": "".join('<li><a href="%s">%s</a></li>' % (s["url"], e(s["titolo"]))
                           for s in C.SERVIZI),
        "cta": cta_finale("Il vostro comune non &egrave; in elenco?",
                          "Chiamateci lo stesso: ci muoviamo in tutta la "
                          "provincia di Napoli e spesso anche oltre."),
    }
    scrivi(p["slug"], p["title"], p["description"], corpo,
           briciole=[("/zone-servite/", "Zone servite")], priorita="0.8")


# --------------------------------------------------------------------------
# Chi siamo
# --------------------------------------------------------------------------

def costruisci_chi_siamo():
    p = C.CHI_SIAMO
    blocchi = []
    for titolo, paragrafi in p["sezioni"]:
        blocchi.append("<h2>%s</h2>%s" % (
            e(titolo), "".join("<p>%s</p>" % e(t) for t in paragrafi)))
    corpo = """<section><div class="wrap stretto">
  <h1>%(h1)s</h1>
  %(ph)s
  %(blocchi)s
  %(btn)s
</div></section>
%(cta)s""" % {
        "h1": e(p["h1"]),
        "ph": placeholder("Foto storica o di squadra",
                          "Suggerita: una foto d'epoca del primo mezzo"),
        "blocchi": "".join(blocchi), "btn": bottoni(),
        "cta": cta_finale("Vi serve una mano?",
                          "Un sopralluogo gratuito &egrave; il modo pi&ugrave; "
                          "rapido per capire tempi e costi del vostro "
                          "trasloco."),
    }
    scrivi(p["slug"], p["title"], p["description"], corpo,
           briciole=[("/chi-siamo/", "Chi siamo")], priorita="0.6")


# --------------------------------------------------------------------------
# Preventivo
# --------------------------------------------------------------------------

def campo_piano(prefisso, etichetta):
    return """<fieldset>
  <legend>%(et)s</legend>
  <div class="due">
    <div class="campo">
      <label for="%(p)s-piano">Piano</label>
      <input type="text" id="%(p)s-piano" name="%(et)s - piano" placeholder="es. 3&deg;, oppure piano terra">
    </div>
    <div class="campo">
      <label for="%(p)s-asc">Ascensore</label>
      <select id="%(p)s-asc" name="%(et)s - ascensore">
        <option value="">Seleziona</option>
        <option>S&igrave;, grande</option>
        <option>S&igrave;, piccolo</option>
        <option>No</option>
        <option>Non lo so</option>
      </select>
    </div>
  </div>
</fieldset>""" % {"p": prefisso, "et": etichetta}


def costruisci_preventivo():
    p = C.PREVENTIVO
    corpo = """<section><div class="wrap stretto">
  <h1>%(h1)s</h1>
  %(intro)s
  %(btn)s
</div></section>

<section class="tenue"><div class="wrap stretto">
  <h2>Modulo di richiesta</h2>
  <form action="https://formspree.io/f/%(formid)s" method="POST">
    <input type="hidden" name="_subject" value="Richiesta preventivo dal sito">
    <input type="text" name="_gotcha" class="hp" tabindex="-1" autocomplete="off" aria-hidden="true">

    <div class="due">
      <div class="campo">
        <label for="nome">Nome e cognome *</label>
        <input type="text" id="nome" name="Nome" required autocomplete="name">
      </div>
      <div class="campo">
        <label for="telefono">Telefono *</label>
        <input type="tel" id="telefono" name="Telefono" required autocomplete="tel"
               inputmode="tel">
      </div>
    </div>

    <div class="campo">
      <label for="email">Email</label>
      <input type="email" id="email" name="Email" autocomplete="email">
      <span class="aiuto">Facoltativa: se la lasciate vi mandiamo il
        preventivo anche per iscritto.</span>
    </div>

    <div class="campo">
      <label for="tipo">Di cosa avete bisogno *</label>
      <select id="tipo" name="Servizio" required>
        <option value="">Seleziona</option>
        <option>Trasloco di abitazione</option>
        <option>Trasloco di ufficio o negozio</option>
        <option>Montaggio o smontaggio mobili</option>
        <option>Sgombero</option>
        <option>Deposito mobili</option>
        <option>Altro</option>
      </select>
    </div>

    <div class="due">
      <div class="campo">
        <label for="partenza">Indirizzo di partenza *</label>
        <input type="text" id="partenza" name="Indirizzo di partenza" required
               placeholder="Via, civico, comune">
      </div>
      <div class="campo">
        <label for="arrivo">Indirizzo di arrivo</label>
        <input type="text" id="arrivo" name="Indirizzo di arrivo"
               placeholder="Via, civico, comune">
      </div>
    </div>

    <div class="due">
      %(piano_part)s
      %(piano_arr)s
    </div>

    <div class="campo">
      <label for="data">Data indicativa</label>
      <input type="date" id="data" name="Data indicativa">
      <span class="aiuto">Anche approssimativa: serve solo a capire il
        periodo.</span>
    </div>

    <div class="campo">
      <label for="descrizione">Descrizione</label>
      <textarea id="descrizione" name="Descrizione"
        placeholder="Numero di stanze, mobili da smontare, elettrodomestici, oggetti ingombranti, cose da sapere sull'accesso..."></textarea>
    </div>

    <p class="nota"><strong>Foto (facoltative):</strong> il modo pi&ugrave;
      veloce per farci capire i volumi &egrave; mandarci qualche foto delle
      stanze su <a href="%(wa)s" rel="noopener" target="_blank">WhatsApp</a>
      o via email a <a href="%(mail)s">%(email)s</a>, indicando il nome che
      avete scritto nel modulo.</p>

    <label class="consenso">
      <input type="checkbox" name="Consenso privacy" value="prestato" required>
      <span>Ho letto l&#8217;<a href="/privacy/">informativa privacy</a> e
        acconsento al trattamento dei dati per ricevere una risposta alla mia
        richiesta. *</span>
    </label>

    <button class="btn btn-arancio" type="submit">Invia la richiesta</button>
    <p class="aiuto">* Campi obbligatori. Non usiamo i vostri dati per
      newsletter o pubblicit&agrave;.</p>
  </form>
</div></section>

<section><div class="wrap stretto">
  <h2>Oppure contattateci direttamente</h2>
  <ul class="elenco">
    <li>Telefono e WhatsApp: <a href="%(tel)s">%(telefono)s</a></li>
    <li>Email: <a href="%(mail)s">%(email)s</a></li>
    <li>Sede: %(indirizzo)s &mdash;
        <a href="%(maps)s" rel="noopener" target="_blank">apri in Google Maps</a></li>
    <li>Orari: %(orari)s</li>
  </ul>
</div></section>""" % {
        "h1": e(p["h1"]),
        "intro": "".join("<p>%s</p>" % e(t) for t in p["intro"]),
        "btn": bottoni(), "formid": C.FORMSPREE_ID,
        "piano_part": campo_piano("part", "Partenza"),
        "piano_arr": campo_piano("arr", "Arrivo"),
        "wa": WA_HREF, "mail": MAIL_HREF, "email": e(A["email"]),
        "tel": TEL_HREF, "telefono": e(A["telefono_display"]),
        "indirizzo": e(INDIRIZZO), "maps": A["maps"], "orari": e(A["orari"]),
    }
    scrivi(p["slug"], p["title"], p["description"], corpo,
           briciole=[("/preventivo/", "Preventivo")], priorita="0.9")


# --------------------------------------------------------------------------
# Privacy e cookie
# --------------------------------------------------------------------------

def costruisci_privacy():
    p = C.PRIVACY
    corpo = """<section><div class="wrap stretto">
  <h1>%(h1)s</h1>
  <p>Questa pagina spiega come %(ragione)s (di seguito &laquo;noi&raquo;)
     tratta i dati personali di chi visita questo sito, ai sensi del
     Regolamento UE 2016/679 (GDPR).</p>

  <h2>Titolare del trattamento</h2>
  <p>%(ragione)s &mdash; %(indirizzo)s &mdash; P.IVA %(piva)s.<br>
     Telefono: <a href="%(tel)s">%(telefono)s</a> &mdash;
     Email: <a href="%(mail)s">%(email)s</a>.</p>

  <h2>Quali dati raccogliamo</h2>
  <p>Raccogliamo soltanto i dati che ci fornite volontariamente:</p>
  <ul class="elenco">
    <li><strong>Modulo di preventivo:</strong> nome, telefono, eventuale
        email, indirizzi di partenza e arrivo, piano e ascensore, data
        indicativa e la descrizione che scrivete.</li>
    <li><strong>Telefono, WhatsApp o email:</strong> i dati che ci comunicate
        durante il contatto.</li>
  </ul>
  <p>Non chiediamo dati particolari e vi preghiamo di non inserirne nel campo
     descrizione.</p>

  <h2>Perch&eacute; li trattiamo e su quale base</h2>
  <ul class="elenco">
    <li>Per rispondere alla vostra richiesta e prepararvi un preventivo:
        esecuzione di misure precontrattuali richieste dall&#8217;interessato
        (art. 6.1.b GDPR).</li>
    <li>Per eventuali obblighi fiscali e contabili, se il lavoro viene
        affidato: obbligo legale (art. 6.1.c GDPR).</li>
  </ul>
  <p>Non usiamo i vostri dati per newsletter, profilazione o pubblicit&agrave;
     e non li vendiamo a nessuno.</p>

  <h2>Per quanto tempo li conserviamo</h2>
  <p>Le richieste che non danno seguito a un lavoro vengono conservate per il
     tempo necessario a gestire il contatto e comunque non oltre 24 mesi. I
     documenti legati a un incarico effettivamente svolto sono conservati per
     i termini previsti dalla legge (di norma 10 anni).</p>

  <h2>A chi possono essere comunicati</h2>
  <p>I dati sono trattati da noi e possono essere trattati, per nostro conto e
     come responsabili del trattamento, dai fornitori tecnici del sito:</p>
  <ul class="elenco">
    <li><strong>Cloudflare, Inc.</strong> &mdash; hosting del sito e sicurezza
        della rete di distribuzione.</li>
    <li><strong>Formspree, Inc.</strong> &mdash; gestione dell&#8217;invio del
        modulo di preventivo.</li>
    <li>Il provider della nostra casella di posta elettronica.</li>
  </ul>
  <p>Alcuni di questi fornitori hanno sede negli Stati Uniti: i trasferimenti
     avvengono sulla base delle garanzie previste dal Capo V del GDPR
     (clausole contrattuali standard o adesione al EU-U.S. Data Privacy
     Framework).</p>

  <h2>Cookie</h2>
  <p>Questo sito <strong>non usa cookie di profilazione, di statistica o di
     terze parti</strong> e non installa strumenti di tracciamento
     pubblicitario. Per questo non compare alcun banner di consenso: non ci
     sono cookie per cui chiederlo.</p>
  <p>Il fornitore di hosting pu&ograve; utilizzare cookie strettamente tecnici
     necessari alla sicurezza e al funzionamento della connessione: per questi
     cookie, ai sensi dell&#8217;art. 122 del Codice privacy, non &egrave;
     richiesto il consenso.</p>
  <p>Se in futuro introdurremo strumenti di statistica o marketing,
     aggiorneremo questa pagina e inseriremo il relativo banner di consenso
     prima di attivarli.</p>

  <h2>Link a siti e servizi esterni</h2>
  <p>Le pagine contengono collegamenti a Google Maps, Facebook, Instagram e
     WhatsApp. Quando aprite quei collegamenti valgono le informative privacy
     dei rispettivi gestori, sulle quali non abbiamo controllo.</p>

  <h2>I vostri diritti</h2>
  <p>Potete chiederci in qualsiasi momento l&#8217;accesso ai vostri dati,
     la rettifica, la cancellazione, la limitazione o l&#8217;opposizione al
     trattamento e la portabilit&agrave;, oltre a revocare il consenso
     prestato. Basta scrivere a <a href="%(mail)s">%(email)s</a> o telefonare
     al <a href="%(tel)s">%(telefono)s</a>: rispondiamo entro un mese.</p>
  <p>Se ritenete che il trattamento violi la normativa potete presentare
     reclamo al Garante per la protezione dei dati personali
     (<a href="https://www.garanteprivacy.it" rel="noopener" target="_blank">garanteprivacy.it</a>).</p>

  <h2>Aggiornamenti</h2>
  <p>Ultimo aggiornamento: %(data)s. Eventuali modifiche saranno pubblicate su
     questa pagina.</p>
</div></section>""" % {
        "h1": e(p["h1"]), "ragione": e(A["ragione_sociale"]),
        "indirizzo": e(INDIRIZZO), "piva": e(A["piva"]), "tel": TEL_HREF,
        "telefono": e(A["telefono_display"]), "mail": MAIL_HREF,
        "email": e(A["email"]), "data": date.today().strftime("%d/%m/%Y"),
    }
    scrivi(p["slug"], p["title"], p["description"], corpo,
           briciole=[("/privacy/", "Privacy e cookie")], priorita="0.3")


# --------------------------------------------------------------------------
# File statici
# --------------------------------------------------------------------------

FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 38 38">
<rect width="38" height="38" rx="9" fill="#0d2440"/>
<path d="M7 24V15l7-4 7 4v9z" fill="#fff"/>
<path d="M22 24v-7h6l3 3v4z" fill="#ef7622"/>
<circle cx="13" cy="25" r="2.6" fill="#0d2440" stroke="#fff" stroke-width="1.4"/>
<circle cx="27" cy="25" r="2.6" fill="#0d2440" stroke="#fff" stroke-width="1.4"/>
</svg>"""

SCRIPT = """/* Solo l'apertura del menu su mobile: nessuna libreria, nessun tracciamento. */
(function () {
  var b = document.querySelector('.nav-toggle');
  var n = document.getElementById('menu');
  if (!b || !n) return;
  b.addEventListener('click', function () {
    var aperto = n.classList.toggle('aperto');
    b.setAttribute('aria-expanded', aperto ? 'true' : 'false');
  });
})();
"""


def png_piatto(percorso, larghezza, altezza, bande):
    """Scrive un PNG senza dipendenze esterne.

    bande: lista di (altezza_in_pixel, (r, g, b)) dall'alto verso il basso.
    Serve solo a produrre l'immagine di anteprima social provvisoria.
    """
    righe = bytearray()
    riga_corrente = 0
    for h_banda, colore in bande:
        linea = bytes(colore) * larghezza
        for _ in range(h_banda):
            if riga_corrente >= altezza:
                break
            righe += b"\x00" + linea
            riga_corrente += 1
    while riga_corrente < altezza:
        righe += b"\x00" + bytes(bande[-1][1]) * larghezza
        riga_corrente += 1

    def chunk(tipo, dati):
        return (struct.pack(">I", len(dati)) + tipo + dati
                + struct.pack(">I", zlib.crc32(tipo + dati) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", larghezza, altezza, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(righe), 9))
           + chunk(b"IEND", b""))
    with open(percorso, "wb") as f:
        f.write(png)


def scrivi_statici():
    shutil.copyfile(os.path.join(SRC, "style.css"), os.path.join(DIST, "style.css"))
    with open(os.path.join(DIST, "script.js"), "w", encoding="utf-8") as f:
        f.write(SCRIPT)
    with open(os.path.join(DIST, "favicon.svg"), "w", encoding="utf-8") as f:
        f.write(FAVICON)

    # Anteprima social provvisoria: va sostituita con una foto reale 1200x630.
    png_piatto(os.path.join(DIST, "og-sorgente-traslochi.png"), 1200, 630,
               [(540, (13, 36, 64)), (90, (239, 118, 34))])

    with open(os.path.join(DIST, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\n\nSitemap: %s\n" % url("/sitemap.xml"))

    oggi = date.today().isoformat()
    voci = "".join(
        "  <url><loc>%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>\n"
        % (url(p), oggi, pr) for p, pr in SITEMAP)
    with open(os.path.join(DIST, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                "%s</urlset>\n" % voci)

    # Cloudflare Pages: cache lunga sugli statici, pagine sempre riconvalidate.
    with open(os.path.join(DIST, "_headers"), "w", encoding="utf-8") as f:
        f.write("/*\n"
                "  X-Content-Type-Options: nosniff\n"
                "  Referrer-Policy: strict-origin-when-cross-origin\n"
                "  X-Frame-Options: SAMEORIGIN\n"
                "\n/style.css\n  Cache-Control: public, max-age=86400\n"
                "\n/script.js\n  Cache-Control: public, max-age=86400\n"
                "\n/favicon.svg\n  Cache-Control: public, max-age=604800\n"
                "\n/*.png\n  Cache-Control: public, max-age=604800\n"
                "\n/*.webp\n  Cache-Control: public, max-age=604800\n")


def main():
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)

    costruisci_home()
    for p in C.PAGINE_SERVIZIO:
        costruisci_servizio(p)
    costruisci_zone()
    costruisci_chi_siamo()
    costruisci_preventivo()
    costruisci_privacy()
    scrivi_statici()

    print("Generate %d pagine in %s" % (len(SITEMAP), DIST))
    for p, _ in SITEMAP:
        print("  " + p)


if __name__ == "__main__":
    main()
