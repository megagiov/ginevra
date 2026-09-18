"""Scontorno — finestra da doppio clic: scegli le foto, escono scontornate.

Nessun terminale. E' il file che l'icona sul desktop lancia; `installa.bat`
crea quell'icona. Si possono anche trascinare le foto sopra l'icona: arrivano
qui come argomenti e partono da sole.

La roba seria sta in scontorno.py — qui c'e' solo la finestra.
"""
import json, os, subprocess, sys, threading, time
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
# 'lato massimo' rimpicciolisce e basta (1024x768 con 800 -> 800x600);
# 'tela esatta' da' proprio quella misura, soggetto centrato — il caso catalogo.
MISURE = {'lato massimo': False, 'tela esatta': True}


def _cartella_scelte():
    """Dove tenere le scelte: la cartella del programma puo' essere di sola
    lettura (Programmi, una chiavetta), quella dell'utente no."""
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA') or os.path.expanduser('~')
    else:
        base = os.environ.get('XDG_CONFIG_HOME') or os.path.join(os.path.expanduser('~'), '.config')
    return os.path.join(base, 'Scontorno')


SCELTE = os.path.join(_cartella_scelte(), 'scelte.json')


def leggi_scelte():
    try:
        with open(SCELTE, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}                     # prima volta, o file rovinato: si riparte dai default


def scrivi_scelte(d):
    try:
        os.makedirs(os.path.dirname(SCELTE), exist_ok=True)
        with open(SCELTE, 'w', encoding='utf-8') as f:
            json.dump(d, f, indent=1)
    except Exception:
        pass                          # non poter ricordare le scelte non e' un errore


def _accorcia(percorso, quanto=52):
    if len(percorso) <= quanto:
        return percorso
    return percorso[:quanto // 2 - 2] + ' … ' + percorso[-(quanto // 2 - 1):]


class Finestra:
    def __init__(self, root, iniziali=()):
        self.root = root
        self.coda = []
        self.modo = 'scontorna'
        self.al_lavoro = False
        self.ultima_cartella = None
        self.scelte = leggi_scelte()
        salvata = self.scelte.get('cartella')
        self.cartella = salvata if salvata and os.path.isdir(salvata) else None
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
                                  self.scelte.get('formato', 'PNG' if 'PNG' in voci else voci[0]))
        self.ombra = self._menu(scelte, 'ombra', list(OMBRE), self.scelte.get('ombra'))
        self.sfondo = self._menu(scelte, 'sfondo', list(SFONDI), self.scelte.get('sfondo'))
        self.ritaglia = tk.BooleanVar(value=bool(self.scelte.get('ritaglia')))
        tk.Checkbutton(scelte, text='ritaglia al soggetto', variable=self.ritaglia,
                       bg=FONDO, fg=TENUE, font=('Segoe UI', 9), relief='flat',
                       activebackground=FONDO, selectcolor=FONDO,
                       command=self.ricorda).pack(side='left', padx=(14, 0))

        mis = tk.Frame(root, bg=FONDO); mis.pack(fill='x', padx=22, pady=(0, 4))
        tk.Label(mis, text='misura', bg=FONDO, fg=TENUE,
                 font=('Segoe UI', 9)).pack(side='left', padx=(0, 5))
        self.misura = tk.StringVar(value=self.scelte.get('misura', ''))
        campo = tk.Entry(mis, textvariable=self.misura, width=10, relief='flat',
                         bg='white', fg=INCHIOSTRO, font=('Segoe UI', 10),
                         highlightthickness=1, highlightbackground=BORDO,
                         highlightcolor=TENUE)
        campo.pack(side='left', ipady=3)
        campo.bind('<FocusOut>', lambda _: self.ricorda())
        campo.bind('<Return>', lambda _: self.ricorda())
        self.come = self._menu(mis, '  come', list(MISURE), self.scelte.get('come'))
        tk.Label(mis, text='vuoto = le lascia come sono; non ingrandisce mai',
                 bg=FONDO, fg=TENUE, font=('Segoe UI', 9)).pack(side='left')

        dove = tk.Frame(root, bg=FONDO); dove.pack(fill='x', padx=22, pady=(0, 4))
        tk.Label(dove, text='le salvo in', bg=FONDO, fg=TENUE,
                 font=('Segoe UI', 9)).pack(side='left', padx=(0, 5))
        self.etichetta_cartella = tk.Label(dove, bg=FONDO, fg=INCHIOSTRO,
                                           font=('Segoe UI', 9, 'bold'), anchor='w')
        self.etichetta_cartella.pack(side='left')
        tk.Button(dove, text='Cambia…', command=self.scegli_cartella, relief='flat',
                  bg=FONDO, fg=TENUE, font=('Segoe UI', 9), cursor='hand2',
                  activebackground=FONDO).pack(side='left', padx=(8, 0))
        self.bottone_accanto = tk.Button(dove, text='accanto alle originali',
                                         command=lambda: self.imposta_cartella(None),
                                         relief='flat', bg=FONDO, fg=TENUE,
                                         font=('Segoe UI', 9), cursor='hand2',
                                         activebackground=FONDO)
        self.bottone_accanto.pack(side='left')
        self._mostra_cartella()

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

    def _menu(self, padre, etichetta, voci, scelta=None):
        tk.Label(padre, text=etichetta, bg=FONDO, fg=TENUE,
                 font=('Segoe UI', 9)).pack(side='left', padx=(0, 5))
        partenza = scelta if scelta in voci else voci[0]
        var = tk.StringVar(value=partenza)
        m = ttk.OptionMenu(padre, var, partenza, *voci, command=lambda _=None: self.ricorda())
        m.pack(side='left', padx=(0, 16))
        return var

    # ------------------------------------------------------- dove si salva

    def _mostra_cartella(self):
        self.etichetta_cartella.configure(
            text=_accorcia(self.cartella) if self.cartella else 'accanto alle originali')
        self.bottone_accanto.configure(state='normal' if self.cartella else 'disabled')

    def imposta_cartella(self, percorso):
        self.cartella = percorso or None
        self._mostra_cartella()
        self.ricorda()

    def scegli_cartella(self):
        scelta = filedialog.askdirectory(title='Dove salvo le foto finite',
                                         initialdir=self.cartella or os.path.expanduser('~'),
                                         mustexist=False)
        if scelta:
            self.imposta_cartella(os.path.normpath(scelta))

    def ricorda(self):
        scrivi_scelte({'cartella': self.cartella, 'formato': self.formato.get(),
                       'ombra': self.ombra.get(), 'sfondo': self.sfondo.get(),
                       'ritaglia': bool(self.ritaglia.get()),
                       'misura': self.misura.get().strip(), 'come': self.come.get()})

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
        import converti as C
        try:
            misura = C.leggi_misura(self.misura.get())
        except ValueError as e:
            messagebox.showerror('Scontorno', str(e))
            return
        self.modo = modo
        # le scelte si leggono qui, sul thread della finestra: tkinter non e'
        # fatto per essere interrogato da un altro thread e prima o poi si pianta
        self.opzioni = dict(formato=FORMATI[self.formato.get()],
                            ombra=OMBRE[self.ombra.get()],
                            sfondo=SFONDI[self.sfondo.get()],
                            ritaglia=bool(self.ritaglia.get()),
                            misura=misura, tela=MISURE[self.come.get()],
                            cartella=self.cartella)
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
            self.ripiegato = False
            try:
                opz = self.opzioni
                formato, sfondo = opz['formato'], opz['sfondo']
                if self.modo == 'scontorna':
                    import scontorno as S
                    out, strada = S.scontorna(C.apri(src),
                                              ombra=opz['ombra'],
                                              sfondo=sfondo,
                                              ritaglia=opz['ritaglia'],
                                              log=lambda *x: None)
                    out = C.ridimensiona(out, opz['misura'], opz['tela'], sfondo)
                    dest = self._salva(C.prepara(out, formato, sfondo or (255, 255, 255)),
                                       src, formato, '-scontornata')
                    nota = f'   {strada}, {out.width}×{out.height}, {time.time() - t:.1f}s'
                    if formato == 'JPG' and sfondo is None:
                        # il JPG non ha trasparenza: si dice, invece di lasciare
                        # che se ne accorga dopo guardando il file
                        nota += ' — il JPG non tiene la trasparenza, fondo bianco'
                else:
                    img = C.ridimensiona(C.apri(src), opz['misura'], opz['tela'], sfondo)
                    dest = self._salva(C.prepara(img, formato, sfondo or (255, 255, 255)),
                                       src, formato, '')
                    nota = (f'   {img.width}×{img.height}, '
                            f'{os.path.getsize(dest) // 1024} KB, {time.time() - t:.1f}s')
                self.ultima_cartella = os.path.dirname(dest)
                if self.ripiegato:
                    nota += f' — non ho potuto scrivere nella cartella scelta, l\u2019ho messa in {self.ultima_cartella}'
                self._segnala(f'✓ {os.path.basename(dest)}', tag='ok', coda=nota)
            except Exception as e:
                self._segnala(f'✗ {os.path.basename(src)}: {e}', tag='male')
            self.fatte += 1
        self._finito()

    def _salva(self, img, src, formato, suffisso):
        """Salva dove ha chiesto l'utente, con due reti sotto.

        Se la cartella scelta non si lascia scrivere (chiavetta tolta, cartella
        di sistema, disco pieno) si prova accanto all'originale e poi sul
        desktop: meglio un file in un posto diverso che il lavoro buttato.
        """
        import converti as C
        casa = os.path.expanduser('~')
        scrivania = os.path.join(casa, 'Desktop')
        ultimo = None
        scelta = self.opzioni['cartella']
        for cartella in (scelta, None, scrivania if os.path.isdir(scrivania) else casa):
            try:
                dest = C.salva(img, src, formato, cartella, 92, suffisso)
                self.ripiegato = cartella != scelta
                return dest
            except OSError as e:
                ultimo = e
        raise ultimo

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
