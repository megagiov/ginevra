@echo off
setlocal
cd /d "%~dp0"
echo.
echo   SCONTORNO - preparo tutto. Ci vogliono un paio di minuti,
echo   solo questa volta. Non chiudere la finestra.
echo.

set PY=py
where py >nul 2>&1 || set PY=python
%PY% --version >nul 2>&1 || goto senza_python

if not exist "venv\Scripts\python.exe" (
  echo   [1/3] creo l'ambiente...
  %PY% -m venv venv || goto storto
)

echo   [2/3] installo Pillow, numpy e onnxruntime...
venv\Scripts\python -m pip install --quiet --upgrade pip
venv\Scripts\python -m pip install --quiet -r requirements.txt || goto storto

venv\Scripts\python -m pip install --quiet pillow-heif 2>nul || echo   Nota: niente HEIC su questo Python, il resto dei formati funziona.
echo   [3/3] scarico il modello ^(176 MB, solo la prima volta^)...
venv\Scripts\python -c "import scontorno; scontorno.percorso_modello('u2net')" || goto storto

venv\Scripts\python -c "import tkinter" >nul 2>&1 || echo   Nota: questo Python e' senza finestra, l'icona aprira' il programma nel browser.
venv\Scripts\python installa_icona.py || goto storto
echo.
echo   FATTO. Sul desktop c'e' l'icona SCONTORNO: doppio clic e si apre.
echo   Ci puoi anche trascinare sopra le foto direttamente.
echo.
pause
exit /b 0

:senza_python
echo.
echo   Non trovo Python su questo computer.
echo   Scaricalo da https://www.python.org/downloads/ e durante
echo   l'installazione spunta "Add python.exe to PATH".
echo   Poi rilancia questo file.
echo.
pause
exit /b 1

:storto
echo.
echo   Qualcosa non ha funzionato: copia le righe qui sopra e mandamele.
echo.
pause
exit /b 1
