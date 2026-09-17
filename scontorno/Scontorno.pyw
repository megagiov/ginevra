"""Scontorno — finestra da doppio clic: scegli le foto, escono scontornate.

Nessun terminale. E' il file che l'icona sul desktop lancia; `installa.bat`
crea quell'icona. Si possono anche trascinare le foto sopra l'icona: arrivano
qui come argomenti e partono da sole.

La roba seria sta in scontorno.py — qui c'e' solo la finestra.
"""
import os, subprocess, sys, threading, time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)

FONDO = '#f4f4f2'; INCHIOSTRO = '#16161a'; TENUE = '#6c6c74'
ACIDO = '#d7f000'; BORDO = '#d8d8d4'
try:
    from converti import FORMATI as _FORMATI, LEGGIBILI as IMMAGINI
except Exception:                       # senza converti.py si va avanti lo stesso
    _FORMATI = {'PNG': None, 'JPG': None, 'WEBP': None}
    IMMAGINI = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff')

SFONDI = {'trasparente': None, 'bianco': (255, 255, 255), 'nero': (0, 0, 0),
          'grigio chiaro': (240, 240, 240)}
FORMATI = {n: n for n in _FORMATI}
OMBRE = {'toglila col fondo': 'via', 'tienila morbida': 'morbida',
         'lasciala attaccata': 'tieni'}


class Finestra:
    def __init__(self, root, iniziali=()):
        self.root = root
        self.coda = []
        self.modo = 'scontorna'
        self.al_lavoro = False
        self.ultima_cartella = None
        root.title('Scontorno')
        root.configure(bg=FONDO)
        root.minsize(780, 520)
        root.geometry('840x640')
        try:
            root.iconbitmap(os.path.join(QUI, 'scontorno.ico'))
        except Exception:
            pass                      # senza icona si vive lo stesso

        testa = tk.Frame(root, bg=FONDO); testa.pack(fill='x', padx=22, pady=(20, 4))
        tk.Label(testa, text='Scontorno', bg=FONDO, fg=INCHIOSTRO,
                 font=('Segoe UI', 19, 'bold')).pack(side='left')
        tk.Label(testa, text='  le foto non escono da questo computer', bg=FONDO,
                 fg=TENUE, font=('Segoe UI', 10)).pack(side='left', pady=(7, 0))

        bottoni = tk.Frame(root, bg=FONDO); bottoni.pack(fill='x', padx=22, pady=(14, 6))
        self.bottone = tk.Button(bottoni, text='Scontorna le foto…',
                                 command=lambda: self.scegli('scontorna'),
                                 bg=ACIDO, fg=INCHIOSTRO, activebackground=ACIDO,
                                 font=('Segoe UI', 13, 'bold'), relief='flat',
                                 cursor='hand2', pady=14)
        self.bottone.pack(side='left', fill='x', expand=True)
        self.bottone2 = tk.Button(bottoni, text='Cambia solo formato…',
                                  command=lambda: self.scegli('converti'),
                                  bg='#e8e8e4', fg=INCHIOSTRO, activebackground='#e8e8e4',
                                  font=('Segoe UI', 11), relief='flat',
                                  cursor='hand2', pady=14, padx=14)
        self.bottone2.pack(side='left', padx=(8, 0))
        tk.Label(root, text='o trascina le foto sopra l’icona sul desktop', bg=FONDO,
                 fg=TENUE, font=('Segoe UI', 9)).pack()

        scelte = tk.Frame(root, bg=FONDO); scelte.pack(fill='x', padx=22, pady=(14, 6))
        voci = list(FORMATI)
        # PNG di partenza: e' l'unico che tiene la trasparenza dello scontorno
        self.formato = self._menu(scelte, 'salva in', voci,
                                  voci.index('PNG') if 'PNG' in voci else 0)
        self.ombra = self._menu(scelte, 'ombra', list(OMBRE), 0)
        self.sfondo = self._menu(scelte, 'sfondo', list(SFONDI), 0)
        self.ritaglia = tk.BooleanVar(value=False)
        tk.Checkbutton(scelte, text='ritaglia al soggetto', variable=self.ritaglia,
                       bg=FONDO, fg=TENUE, font=('Segoe UI', 9), relief='flat',
                       activebackground=FONDO, selectcolor=FONDO).pack(side='left', padx=(14, 0))

        riquadro = tk.Frame(root, bg='white', highlightbackground=BORDO, highlightthickness=1)
        riquadro.pack(fill='both', expand=True, padx=22, pady=(8, 6))
        self.elenco = tk.Text(riquadro, bg='white', fg=INCHIOSTRO, relief='flat',
                              font=('Consolas', 10), padx=12, pady=10, wrap='none',
                              state='disabled', cursor='arrow')
        barra = tk.Scrollbar(riquadro, command=self.elenco.yview)
        self.elenco.configure(yscrollcommand=barra.set)
        barra.pack(side='right', fill='y'); self.elenco.pack(fill='both', expand=True)
        self.elenco.tag_configure('ok', foreground='#1c7a3e')
        self.elenco.tag_configure('male', foreground='#b3261e')
        self.elenco.tag_configure('tenue', foreground=TENUE)

        self.avanzamento = ttk.Progressbar(root, mode='determinate')
        piede = tk.Frame(root, bg=FONDO); piede.pack(fill='x', padx=22, pady=(0, 16))
        self.stato = tk.Label(piede, text='pronto', bg=FONDO, fg=TENUE,
                              font=('Segoe UI', 9), anchor='w')
        self.stato.pack(side='left')
        self.apri = tk.Button(piede, text='Apri la cartella', command=self.apri_cartella,
                              relief='flat', bg=FONDO, fg=TENUE, cursor='hand2',
                              font=('Segoe UI', 9), state='disabled')
        self.apri.pack(side='right')

        iniziali = [f for f in iniziali if f.lower().endswith(IMMAGINI)]
        if iniziali:
            self.root.after(200, lambda: self.accoda(iniziali))

    def _menu(self, padre, etichetta, voci, predefinita):
        tk.Label(padre, text=etichetta, bg=FONDO, fg=TENUE,
                 font=('Segoe UI', 9)).pack(side='left', padx=(0, 5))
        var = tk.StringVar(value=voci[predefinita])
        m = ttk.OptionMenu(padre, var, voci[predefinita], *voci)
        m.pack(side='left', padx=(0, 16))
        return var

    # ------------------------------------------------------------ lavoro

    def scegli(self, modo):
        import converti as C
        files = filedialog.askopenfilenames(
            title='Scegli le foto da scontornare' if modo == 'scontorna'
                  else 'Scegli le foto da convertire',
            filetypes=[('Immagini', ' '.join('*' + e for e in C.LEGGIBILI)),
                       ('Tutti i file', '*.*')])
        if files:
            self.accoda(list(files), modo)

    def accoda(self, files, modo='scontorna'):
        self.modo = modo
        self.coda.extend(files)
        if not self.al_lavoro:
            self.al_lavoro = True
            self.bottone.configure(state='disabled', text='sto lavorando…')
            self.bottone2.configure(state='disabled')
            self.avanzamento.pack(fill='x', padx=22, pady=(2, 8), before=self.stato.master)
            self.fatte = 0
            self.inizio = time.time()
            threading.Thread(target=self._lavora, daemon=True).start()

    def _lavora(self):
        import converti as C
        primo = True
        while self.coda:
            src = self.coda.pop(0)
            totale = self.fatte + len(self.coda) + 1
            self._segnala(f'{os.path.basename(src)} …',
                          avanzamento=(self.fatte, totale),
                          stato=('preparo il modello, solo la prima volta'
                                 if primo and self.modo == 'scontorna'
                                 else f'{self.fatte + 1} di {totale}'))
            primo = False
            t = time.time()
            try:
                formato = FORMATI[self.formato.get()]
                sfondo = SFONDI[self.sfondo.get()]
                if self.modo == 'scontorna':
                    import scontorno as S
                    out, strada = S.scontorna(C.apri(src),
                                              ombra=OMBRE[self.ombra.get()],
                                              sfondo=sfondo,
                                              ritaglia=self.ritaglia.get(),
                                              log=lambda *x: None)
                    dest = self._salva(C.prepara(out, formato, sfondo or (255, 255, 255)),
                                       src, formato, '-scontornata')
                    nota = f'   {strada}, {time.time() - t:.1f}s'
                    if formato == 'JPG' and sfondo is None:
                        # il JPG non ha trasparenza: si dice, invece di lasciare
                        # che se ne accorga dopo guardando il file
                        nota += ' — il JPG non tiene la trasparenza, fondo bianco'
                else:
                    dest = self._salva(C.prepara(C.apri(src), formato, sfondo or (255, 255, 255)),
                                       src, formato, '')
                    nota = f'   {os.path.getsize(dest) // 1024} KB, {time.time() - t:.1f}s'
                self.ultima_cartella = os.path.dirname(dest)
                self._segnala(f'✓ {os.path.basename(dest)}', tag='ok', coda=nota)
            except Exception as e:
                self._segnala(f'✗ {os.path.basename(src)}: {e}', tag='male')
            self.fatte += 1
        self._finito()

    def _salva(self, img, src, formato, suffisso):
        import converti as C
        try:
            return C.salva(img, src, formato, None, 92, suffisso)
        except OSError:
            # cartella di sola lettura (una chiavetta, una cartella di sistema):
            # si ripiega sul desktop invece di perdere il lavoro fatto
            casa = os.path.expanduser('~')
            scrivania = os.path.join(casa, 'Desktop')
            return C.salva(img, src, formato,
                           scrivania if os.path.isdir(scrivania) else casa, 92, suffisso)

    # ------------------------------------------------ ponte verso la finestra

    def _segnala(self, riga, tag='tenue', coda='', avanzamento=None, stato=None):
        def dentro():
            self.elenco.configure(state='normal')
            self.elenco.insert('end', riga + '\n', tag)
            if coda:
                self.elenco.insert('end', coda + '\n', 'tenue')
            self.elenco.see('end')
            self.elenco.configure(state='disabled')
            if avanzamento:
                fatte, totale = avanzamento
                self.avanzamento.configure(maximum=totale, value=fatte)
            if stato:
                self.stato.configure(text=stato)
        self.root.after(0, dentro)

    def _finito(self):
        def dentro():
            self.al_lavoro = False
            self.bottone.configure(state='normal', text='Scontorna le foto…')
            self.bottone2.configure(state='normal')
            self.avanzamento.pack_forget()
            quante = self.fatte
            durata = time.time() - self.inizio
            quanto = f'{durata:.1f}s' if durata >= 0.95 else 'meno di un secondo'
            self.stato.configure(text=f"{'una foto' if quante == 1 else str(quante) + ' foto'} in {quanto}")
            if self.ultima_cartella:
                self.apri.configure(state='normal')
        self.root.after(0, dentro)

    def apri_cartella(self):
        c = self.ultima_cartella
        if not c:
            return
        try:
            if sys.platform == 'win32':
                os.startfile(c)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', c])
            else:
                subprocess.Popen(['xdg-open', c])
        except Exception as e:
            messagebox.showerror('Scontorno', f'non riesco ad aprire {c}\n{e}')


def main():
    root = tk.Tk()
    Finestra(root, sys.argv[1:])
    root.mainloop()


if __name__ == '__main__':
    main()
