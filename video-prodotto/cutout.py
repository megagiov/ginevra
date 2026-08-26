from PIL import Image, ImageDraw, ImageFilter
import numpy as np

src = Image.open('grigio-1024x1024.jpg').convert('RGB')
w, h = src.size
g = np.asarray(src.convert('L')).astype(np.uint8)

# 1) maschera del "quasi bianco"
nearwhite = (g > 238).astype(np.uint8) * 255
m = Image.fromarray(nearwhite, 'L')

# 2) flood fill dai 4 angoli: solo il bianco COLLEGATO al bordo e' sfondo
ff = m.copy()
for xy in [(0,0),(w-1,0),(0,h-1),(w-1,h-1)]:
    if ff.getpixel(xy) == 255:
        ImageDraw.floodfill(ff, xy, 128, thresh=0)
ffa = np.asarray(ff)
background = (ffa == 128)

alpha = np.where(background, 0, 255).astype(np.uint8)

# 3) bordo morbido per non avere l'effetto ritaglio con le forbici
a = Image.fromarray(alpha, 'L').filter(ImageFilter.GaussianBlur(0.8))
a = Image.fromarray((np.asarray(a).astype(np.int16).clip(0,255)).astype(np.uint8), 'L')

out = src.copy(); out.putalpha(a)

# 4) crop sul prodotto
bbox = out.getbbox()
out = out.crop(bbox)
out.save('shoe_cut.png')
cov = (np.asarray(a) > 128).mean()
print(f'ritaglio: bbox={bbox} -> {out.size}, prodotto copre il {cov*100:.1f}% del quadro originale')
