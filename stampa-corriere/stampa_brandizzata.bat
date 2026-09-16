@echo off
rem Trascina sopra questo file il PDF della LDV scaricato dal corriere.
rem Genera <nome>_brandizzato.pdf nella stessa cartella e lo apre subito,
rem pronto per Ctrl+P. Il PDF originale non viene toccato.

if "%~1"=="" (
    echo Trascina il PDF della LDV sopra questo file, non fare doppio click a vuoto.
    pause
    exit /b
)

py "%~dp0applica_maschera.py" "%~1"
if errorlevel 1 (
    echo.
    echo Qualcosa e' andato storto: leggi il messaggio sopra.
    pause
    exit /b
)

start "" "%~dp1%~n1_brandizzato.pdf"
