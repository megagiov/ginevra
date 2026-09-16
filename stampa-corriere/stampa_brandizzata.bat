@echo off
rem Trascina sopra questo file il PDF della LDV scaricato dal corriere.
rem Genera <nome>_brandizzato.pdf nella stessa cartella e lo apre subito,
rem pronto per Ctrl+P. Il PDF originale non viene toccato.

if "%~1"=="" (
    echo Trascina il PDF della LDV sopra questo file, non fare doppio click a vuoto.
    pause
    exit /b
)

where py >nul 2>nul
if errorlevel 1 (
    echo Non trovo il comando "py". Python non e' installato, oppure non e'
    echo stato aggiunto al PATH. Riapri il Prompt dei comandi dopo averlo
    echo installato: "py install 3.13".
    pause
    exit /b
)

echo Elaborazione di "%~1" in corso...
py "%~dp0applica_maschera.py" "%~1"
if errorlevel 1 (
    echo.
    echo Qualcosa e' andato storto: leggi il messaggio sopra.
    pause
    exit /b
)

if not exist "%~dp1%~n1_brandizzato.pdf" (
    echo Lo script e' terminato ma non trovo il file
    echo "%~dp1%~n1_brandizzato.pdf" — controlla il messaggio sopra.
    pause
    exit /b
)

echo Fatto: apro "%~n1_brandizzato.pdf"
start "" "%~dp1%~n1_brandizzato.pdf"
timeout /t 3 >nul
