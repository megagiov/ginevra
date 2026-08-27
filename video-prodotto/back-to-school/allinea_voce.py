"""Appoggia la voce italiana corretta sugli attacchi del parlato generato.

Il modello video pronuncia male e qui e' anche passato all'inglese in mezzo
("backpacks, pencil cases, water bottles"), quindi l'allineamento parola per
parola di `place.py` non si puo' usare: le parole non si corrispondono. Si
allinea per **frase**, che e' la struttura che i due parlati condividono.

La regola resta quella del quaderno di bordo: **dentro una frase l'audio non si
tocca mai**. Le frasi si spostano intere, le pause vere si allungano o si
accorciano.

    python3 back-to-school/allinea_voce.py
"""
import numpy as np
import wave, os

SR = 44100
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
OUT = os.path.join(ROOT, 'out')

# attacchi delle quattro frasi nel parlato generato, letti dalla trascrizione
ATTACCHI = [0.00, 1.94, 4.92, 6.92]

# Confini delle stesse quattro frasi dentro la voce italiana, misurati sull'onda.
# Vanno scritti, non dedotti: le pause della voce non hanno una gerarchia che
# corrisponda al copione — quella dopo "trovi tutto" (596 ms) e' piu' lunga di
# quella dopo "scuola" (572 ms), quindi qualunque regola basata sulla durata
# delle pause taglia nei punti sbagliati.
FRASI = [(0.064, 1.758),    # È tempo di pensare alla scuola
         (2.330, 4.825),    # Zaini, astucci, borracce
         (5.337, 7.126),    # anche con i personaggi dei cartoni
         (7.717, 10.353)]   # Da noi trovi tutto. Cosa aspetti?


def leggi(path):
    w = wave.open(path)
    sr, n = w.getframerate(), w.getnframes()
    a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    return a, sr


def main():
    voce, sr = leggi(os.path.join(OUT, 'voce.wav'))
    if sr != SR:                                    # la voce esce a 48k, il montaggio va a 44,1k
        n = int(len(voce) * SR / sr)
        voce = np.interp(np.linspace(0, len(voce) - 1, n), np.arange(len(voce)), voce).astype(np.float32)

    frasi = FRASI
    print('frasi della voce italiana:')
    for i, (s, e) in enumerate(frasi):
        print('  %d  %5.2f - %5.2f  (%.2f s)' % (i + 1, s, e, e - s))

    durata = 11.10
    total = np.zeros(int(SR * durata), np.float32)
    fine_prec = 0.0
    for (s, e), att in zip(frasi, ATTACCHI):
        s = max(0.0, s - 0.035); e = e + 0.045      # un filo di respiro ai bordi
        pezzo = voce[int(s * SR):int(e * SR)].copy()
        inizio = max(att - 0.035, fine_prec + 0.06)
        i0 = int(inizio * SR); i1 = min(len(total), i0 + len(pezzo))
        pezzo = pezzo[:i1 - i0]
        f = int(0.010 * SR)
        if len(pezzo) > 2 * f:
            pezzo[:f] *= np.linspace(0, 1, f)
            pezzo[-f:] *= np.linspace(1, 0, f)
        total[i0:i1] += pezzo
        print('  posata a %5.2f, finisce a %5.2f  (attacco generato %5.2f)'
              % (inizio, inizio + len(pezzo) / SR, att))
        fine_prec = inizio + len(pezzo) / SR

    total /= max(1e-9, np.abs(total).max()) / 0.90
    w = wave.open(os.path.join(OUT, 'voce_allineata.wav'), 'wb')
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(total, -1, 1) * 32767).astype(np.int16).tobytes())
    w.close()
    print('parlato finisce a %.2f s su %.2f s di video' % (fine_prec, durata))


if __name__ == '__main__':
    main()
