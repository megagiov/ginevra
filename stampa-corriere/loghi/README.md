# Loghi — provenienza e conversione

I due file qui dentro sono stati derivati dagli originali a colori forniti
dall'utente in chat, convertiti in bianco/nero puro perché la stampa delle
LDV è in bianco e nero (niente sfumature: su una stampante monocromatica un
grigio intermedio esce come retino/dithering, non come grigio pulito).

- **`gm-vegasi-logo.png`** — logo GM Vegasi (wordmark + fiocco), originale
  blu su sfondo trasparente. Conversione: pixel colorati riportati a nero
  puro, canale alpha invariato (i bordi restano morbidi, non è stata
  applicata soglia).

- **`gm-vegasi-tiktokshop.png`** — badge GM Vegasi + TikTok Shop (borsa con
  cartellino), originale a colori (nero, ciano, rosa) su sfondo nero pieno.
  Conversione: scala di grigi poi soglia dura a 50/255 — sotto diventa nero,
  sopra diventa bianco. Soglie più alte (provate 80/110/140) rompevano i
  bordi arrotondati e l'area "lucida" della borsa in un retino sporco; 50
  è il punto in cui i contorni restano puliti.

Se in futuro serve una versione a colori (social, sito), bisogna richiedere
di nuovo i file originali: qui sono state tenute solo le versioni convertite,
quelle a colori non sono state salvate nel repository.
