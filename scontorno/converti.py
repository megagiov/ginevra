"""Cambio formato: legge quel che trova e salva nel formato che chiedi.

    python3 converti.py foto.avif --in jpg
    python3 converti.py *.webp --in jpg -o convertite/
    python3 converti.py foto.png --in jpg --sfondo bianco --qualita 90

Legge tutto quello che apre Pillow (JPG, PNG, WEBP, AVIF, TIFF, BMP, GIF...) e
anche HEIC/HEIF dell'iPhone se e' installato `pillow-heif`. Gira in locale come
il resto: nessun servizio, nessun caricamento da nessuna parte.
"""
import argparse, os, sys
from PIL import Image, ImageOps

try:                                    # HEIC dell'iPhone: se c'e', si usa
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIF = True
except ImportError:
    HEIF = False

try:
    Image.init()
    AVIF = 'AVIF' in Image.SAVE         # Pillow >= 11.3 ce l'ha dentro
except Exception:
    AVIF = False

FORMATI = {
    'JPG':  dict(pil='JPEG', est='.jpg',  alpha=False),
    'PNG':  dict(pil='PNG',  est='.png',  alpha=True),
    'WEBP': dict(pil='WEBP', est='.webp', alpha=True),
}
if AVIF:
    FORMATI['AVIF'] = dict(pil='AVIF', est='.avif', alpha=True)

LEGGIBILI = ('.jpg', '.jpeg', '.png', '.webp', '.avif', '.bmp', '.gif', '.tif',
             '.tiff', '.ico', '.ppm', '.jp2') + (('.heic', '.heif') if HEIF else ())


def apri(percorso):
    """Immagine raddrizzata secondo l'EXIF: le foto da telefono arrivano storte."""
    img = Image.open(percorso)
    img.load()
    return ImageOps.exif_transpose(img)


def prepara(img, formato, sfondo=(255, 255, 255)):
    """Immagine nel modo giusto per quel formato."""
    f = FORMATI[formato]
    if img.mode in ('P', 'PA'):
        img = img.convert('RGBA' if 'transparency' in img.info else 'RGB')
    if img.mode in ('I', 'I;16', 'F'):          # profondita' esotiche
        img = img.convert('RGB')
    if img.mode == 'CMYK' and f['pil'] != 'JPEG':
        img = img.convert('RGB')
    trasparente = img.mode in ('RGBA', 'LA')
    if trasparente and not f['alpha']:
        # il JPG non ha trasparenza: si appoggia su un colore invece di
        # ritrovarsi il nero, che e' quel che verrebbe fuori da solo
        piano = Image.new('RGB', img.size, tuple(sfondo))
        piano.paste(img, mask=img.getchannel('A'))
        img = piano
    elif not trasparente and img.mode not in ('RGB', 'L', 'CMYK'):
        img = img.convert('RGB')
    return img


def _libero(percorso, sorgente):
    """Non sovrascrive la foto di partenza ne' un file gia' li'."""
    if percorso != sorgente and not os.path.exists(percorso):
        return percorso
    base, est = os.path.splitext(percorso)
    if not os.path.exists(base + '-convertita' + est):
        return base + '-convertita' + est
    n = 2
    while os.path.exists(f'{base}-convertita-{n}{est}'):
        n += 1
    return f'{base}-convertita-{n}{est}'


def salva(img, sorgente, formato, cartella=None, qualita=92, suffisso=''):
    f = FORMATI[formato]
    nome = os.path.splitext(os.path.basename(sorgente))[0] + suffisso + f['est']
    dest = os.path.join(cartella or os.path.dirname(sorgente) or '.', nome)
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    dest = _libero(dest, os.path.abspath(sorgente))
    extra = {}
    if f['pil'] in ('JPEG', 'WEBP', 'AVIF'):
        extra['quality'] = int(qualita)
    if f['pil'] == 'JPEG':
        extra.update(optimize=True, progressive=True, subsampling='keep' if img.mode == 'RGB' else 0)
    if f['pil'] == 'PNG':
        extra['optimize'] = True
    for chiave in ('icc_profile', 'exif'):      # colore e dati di scatto
        if img.info.get(chiave):
            extra[chiave] = img.info[chiave]
    if f['pil'] == 'JPEG' and extra.get('subsampling') == 'keep' and img.format != 'JPEG':
        extra.pop('subsampling')                # 'keep' vale solo da JPEG a JPEG
    img.save(dest, f['pil'], **extra)
    return dest


def converti(sorgente, formato, cartella=None, sfondo=(255, 255, 255), qualita=92):
    return salva(prepara(apri(sorgente), formato, sfondo), sorgente, formato, cartella, qualita)


def main(argv=None):
    import scontorno as S
    p = argparse.ArgumentParser(description='Cambia formato alle foto, in locale.')
    p.add_argument('foto', nargs='+')
    p.add_argument('--in', dest='formato', required=True,
                   choices=tuple(FORMATI) + tuple(f.lower() for f in FORMATI))
    p.add_argument('-o', '--out', default=None, help='cartella di destinazione')
    p.add_argument('--sfondo', type=S._colore, default=(255, 255, 255),
                   help='colore sotto la trasparenza quando si va in JPG')
    p.add_argument('--qualita', type=int, default=92)
    a = p.parse_args(argv)
    for src in S._espandi(a.foto):
        if not os.path.isfile(src):
            print(f'non trovo {src}', file=sys.stderr)
            continue
        try:
            dest = converti(src, a.formato.upper(), a.out, a.sfondo or (255, 255, 255), a.qualita)
            print(f'{dest}  ({os.path.getsize(dest)//1024} KB)')
        except Exception as e:
            print(f'{src}: {type(e).__name__}: {e}', file=sys.stderr)


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
