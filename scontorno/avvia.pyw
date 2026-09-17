"""Quello che lancia l'icona sul desktop.

Di norma apre la finestra. Se pero' il Python installato e' senza tkinter —
capita con certe versioni dallo Store o dal gestore `py` — invece di morire in
silenzio (pythonw non ha una console dove scrivere l'errore) avvia il server e
apre la pagina nel browser, che fa le stesse cose.
"""
import os, sys

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)

try:
    import tkinter                                    # noqa: F401
except ImportError:
    import server
    server.main(['--apri'])
else:
    import runpy
    sys.argv[0] = os.path.join(QUI, 'Scontorno.pyw')
    runpy.run_path(sys.argv[0], run_name='__main__')
