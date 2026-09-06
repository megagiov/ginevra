#!/usr/bin/env python3
"""Trascrive il cantato di un brano in un JSON con i tempi, parola per parola.

    python3 versi.py brano.mp3 --out versi.json

Il file prodotto si apre e si corregge a mano: su una base musicale densa la
trascrizione sbaglia, e le parole sbagliate a schermo si notano piu' di tutto.
Formato: lista di {"start", "end", "text", "words": [{"w", "s", "e"}]}, tempi in
secondi dall'inizio del brano. Poi:

    python3 eq.py brano.mp3 --testo versi.json ...
"""
import argparse, json, sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("audio")
    p.add_argument("--out", default="versi.json")
    p.add_argument("--modello", default="small",
                   help="tiny, base, small (default), medium, large-v3")
    p.add_argument("--lingua", default=None, help="es. en, it; default: automatica")
    p.add_argument("--blocco", type=float, default=60.0,
                   help="secondi per blocco: limita la deriva dei tempi")
    a = p.parse_args()

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("manca faster-whisper: pip install faster-whisper")

    m = WhisperModel(a.modello, device="cpu", compute_type="int8", cpu_threads=8)

    # durata del brano, per sapere quanti blocchi servono
    import subprocess, imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    raw = subprocess.run([ff, "-v", "error", "-i", a.audio, "-f", "f32le",
                          "-ac", "1", "-ar", "8000", "-"],
                         capture_output=True, check=True).stdout
    durata = len(raw) / 4 / 8000

    versi = []
    t = 0.0
    while t < durata:
        fine = min(t + a.blocco, durata)
        # niente VAD: su un mix con batteria e basso taglierebbe via il cantato
        segs, _ = m.transcribe(a.audio, vad_filter=False, beam_size=5,
                               language=a.lingua, condition_on_previous_text=False,
                               word_timestamps=True, clip_timestamps=[t, fine])
        for s in segs:
            if not s.text.strip():
                continue
            versi.append({"start": s.start, "end": s.end, "text": s.text.strip(),
                          "words": [{"w": w.word.strip(), "s": w.start, "e": w.end}
                                    for w in (s.words or [])]})
        print(f"  {t:.0f}-{fine:.0f} s: {len(versi)} segmenti", flush=True)
        t = fine

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(versi, f, ensure_ascii=False, indent=1)
    print("scritto", a.out, f"({len(versi)} segmenti) — rileggilo e correggilo")


if __name__ == "__main__":
    main()
