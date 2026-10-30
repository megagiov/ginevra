"""Storia 1080x1920 dalla grafica orizzontale "Domani: chiusi!".

Ricompone la tavola di legno (testi) sopra e il poster illustrato sotto,
e copre la riga della data con un nastro che riporta il giorno corretto.
Uso: python3 on-the-road/storia_chiusura.py "LUNEDÌ 2 NOVEMBRE"
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont

QUI = Path(__file__).parent
W, H = 1080, 1920
DATA = sys.argv[1] if len(sys.argv) > 1 else "LUNEDÌ 2 NOVEMBRE"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
CREMA, BORDO, INCHIOSTRO = (245, 231, 194), (110, 75, 40), (70, 40, 15)

src = Image.open(QUI / "chiusura-2-novembre-orizzontale.jpg").convert("RGB")

# fondo: la grafica stessa, ingrandita, sfocata e scurita
s = max(W / src.width, H / src.height)
fondo = src.resize((round(src.width * s), round(src.height * s)), Image.LANCZOS)
fondo = fondo.crop(((fondo.width - W) // 2, 0, (fondo.width - W) // 2 + W, H))
fondo = ImageEnhance.Brightness(fondo.filter(ImageFilter.GaussianBlur(28))).enhance(0.45)

# tavola con i testi
tavola = src.crop((62, 0, 748, 768))
k = 960 / tavola.width
tavola = tavola.resize((960, round(tavola.height * k)), Image.LANCZOS)

# nastro sopra data sbagliata + segnaposto inglese (y 406-503 nell'originale)
d = ImageDraw.Draw(tavola)
x0, x1 = round((110 - 62) * k), round((715 - 62) * k)
y0, y1 = round(406 * k), round(503 * k)
tacca = 28
forma = [(x0 - tacca, y0), (x1 + tacca, y0), (x1, (y0 + y1) // 2), (x1 + tacca, y1),
         (x0 - tacca, y1), (x0, (y0 + y1) // 2)]
d.polygon(forma, fill=CREMA, outline=BORDO, width=4)
size = 80
f = ImageFont.truetype(FONT, size)
while d.textbbox((0, 0), DATA, font=f)[2] > (x1 - x0) - 40:
    size -= 2
    f = ImageFont.truetype(FONT, size)
d.text(((x0 + x1) // 2, (y0 + y1) // 2), DATA, font=f, fill=INCHIOSTRO, anchor="mm")

# poster illustrato
poster = src.crop((749, 15, 1326, 755))
ph = H - 60 - (150 + tavola.height + 30)
poster = poster.resize((round(poster.width * ph / poster.height), ph), Image.LANCZOS)

out = fondo
out.paste(tavola, ((W - tavola.width) // 2, 150))
out.paste(poster, ((W - poster.width) // 2, 150 + tavola.height + 30))
dest = QUI / "storia-chiusura-2-novembre.jpg"
out.save(dest, quality=95)
print(dest)
