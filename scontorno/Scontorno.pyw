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
IMMAGINI = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff')

SFONDI = {'trasparente': None, 'bianco': (255, 255, 255), 'nero': (0, 0, 0),
          'grigio chiaro': (240, 240, 240)}
OMBRE = {'toglila col fondo': 'via', 'tienila morbida': 'morbida',
         'lasciala attaccata': 'tieni'}


class Finestra:
    def __init__(self, root, iniziali=()):
        self.root = root
        self.coda = []
        self.al_lavoro = False
        self.ultima_cartella = None
        root.title('Scontorno')
        root.configure(bg=FONDO)
        root.minsize(620, 480)
        try:
            root.iconbitmap(os.path.join(QUI, 'scontorno.ico'))
        except Exception:
            pass                      # senza icona si vive lo stesso

        testa = tk.Frame(root, bg=FONDO); testa.pack(fill='x', padx=22, pady=(20, 4))
        tk.Label(testa, text='Scontorno', bg=FONDO, fg=INCHIOSTRO,
                 font=('Segoe UI', 19, 'bold')).pack(side='left')
        tk.Label(testa, text='  le foto non escono da questo computer', bg=FONDO,
                 fg=TENUE, font=('Segoe UI', 10)).pack(side='left', pady=(7, 0))

        self.bottone = tk.Button(root, text='Scegli le foto…', command=self.scegli,
                                 bg=ACIDO, fg=INCHIOSTRO, activebackground=ACIDO,
                                 font=('Segoe UI', 13, 'bold'), relief='flat',
                                 cursor='hand2', pady=14)
        self.bottone.pack(fill='x', padx=22, pady=(14, 6))
        tk.Label(root, text='o trascina le foto sopra l’icona sul desktop', bg=FONDO,
                 fg=TENUE, font=('Segoe UI', 9)).pack()

        scelte = tk.Frame(root, bg=FONDO); scelte.pack(fill='x', padx=22, pady=(14, 6))
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

    def scegli(self):
        files = filedialog.askopenfilenames(
            title='Scegli le foto da scontornare',
            filetypes=[('Immagini', '*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff'),
                       ('Tutti i file', '*.*')])
        if files:
            self.accoda(list(files))

    def accoda(self, files):
        self.coda.extend(files)
        if not self.al_lavoro:
            self.al_lavoro = True
            self.bottone.configure(state='disabled', text='sto lavorando…')
            self.avanzamento.pack(fill='x', padx=22, pady=(2, 8), before=self.stato.master)
            self.fatte = 0
            self.inizio = time.time()
            threading.Thread(target=self._lavora, daemon=True).start()

    def _lavora(self):
        from PIL import Image
        import scontorno as S
        primo = True
        while self.coda:
            src = self.coda.pop(0)
            totale = self.fatte + len(self.coda) + 1
            self._segnala(f'{os.path.basename(src)} …',
                          avanzamento=(self.fatte, totale),
                          stato=('preparo il modello, solo la prima volta'
                                 if primo else f'{self.fatte + 1} di {totale}'))
            primo = False
            t = time.time()
            try:
                out, strada = S.scontorna(
                    Image.open(src),
                    ombra=OMBRE[self.ombra.get()],
                    sfondo=SFONDI[self.sfondo.get()],
                    ritaglia=self.ritaglia.get(),
                    log=lambda *x: None)
                dest = self._salva(out, src)
                self.ultima_cartella = os.path.dirname(dest)
                self._segnala(f'✓ {os.path.basename(dest)}',
                              tag='ok', coda=f'   {strada}, {time.time()-t:.1f}s')
            except Exception as e:
                self._segnala(f'✗ {os.path.basename(src)}: {e}', tag='male')
            self.fatte += 1
        self._finito()

    def _salva(self, out, src):
        nome = os.path.splitext(os.path.basename(src))[0] + '-scontornata.png'
        dest = os.path.join(os.path.dirname(src), nome)
        try:
            out.save(dest)
        except OSError:
            # cartella di sola lettura (una chiavetta, una cartella di sistema):
            # si ripiega sul desktop invece di perdere il lavoro fatto
            scrivania = os.path.join(os.path.expanduser('~'), 'Desktop')
            dest = os.path.join(scrivania if os.path.isdir(scrivania)
                                else os.path.expanduser('~'), nome)
            out.save(dest)
        return dest

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
            self.bottone.configure(state='normal', text='Scegli le foto…')
            self.avanzamento.pack_forget()
            quante = self.fatte
            self.stato.configure(
                text=f"{quante} foto in {time.time() - self.inizio:.1f}s"
                     if quante != 1 else f"una foto in {time.time() - self.inizio:.1f}s")
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
