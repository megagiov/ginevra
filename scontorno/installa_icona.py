"""Crea il collegamento 'Scontorno' sul desktop. Lo chiama installa.bat.

Il percorso del desktop va chiesto a Windows e non costruito a mano: con
OneDrive attivo la cartella e' dentro OneDrive e `%USERPROFILE%\\Desktop` non
esiste piu'.
"""
import os, subprocess, sys, tempfile

QUI = os.path.dirname(os.path.abspath(__file__))


def _ps(valore):
    """Stringa per PowerShell: gli apici singoli si raddoppiano."""
    return "'" + str(valore).replace("'", "''") + "'"


def crea():
    avvio = os.path.join(QUI, 'venv', 'Scripts', 'pythonw.exe')
    if not os.path.exists(avvio):                       # senza pythonw resta la console
        avvio = os.path.join(QUI, 'venv', 'Scripts', 'python.exe')
    if not os.path.exists(avvio):
        raise SystemExit("manca venv\\Scripts\\python.exe: lancia prima installa.bat")
    copione = f"""$ErrorActionPreference = 'Stop'
$desktop = [Environment]::GetFolderPath('Desktop')
$link = Join-Path $desktop 'Scontorno.lnk'
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($link)
$s.TargetPath = {_ps(avvio)}
$s.Arguments = {_ps('"' + os.path.join(QUI, 'avvia.pyw') + '"')}
$s.WorkingDirectory = {_ps(QUI)}
$s.IconLocation = {_ps(os.path.join(QUI, 'scontorno.ico'))}
$s.Description = 'Toglie lo sfondo dalle foto, tutto in locale'
$s.Save()
Write-Output ('collegamento creato: ' + $link)
"""
    with tempfile.NamedTemporaryFile('w', suffix='.ps1', delete=False, encoding='utf-8') as f:
        f.write(copione)
        strada = f.name
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                            '-File', strada], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit('non riesco a creare il collegamento:\n' + (r.stderr or r.stdout))
        print(r.stdout.strip())
    finally:
        os.unlink(strada)


if __name__ == '__main__':
    if sys.platform != 'win32':
        print("il collegamento sul desktop si crea solo su Windows; altrove si lancia\n"
              f"  python3 {os.path.join(QUI, 'avvia.pyw')}")
        sys.exit(0)
    crea()
