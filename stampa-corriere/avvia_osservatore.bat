@echo off
rem Avvia la sorveglianza automatica della cartella Download.
rem Lascia aperta questa finestra: ogni LDV che scarichi da un corriere
rem viene brandizzata da sola e si apre pronta per Ctrl+P.
rem Per fermarla, chiudi questa finestra.

if not exist "%~dp0osserva_cartella.py" (
    echo Non trovo i file che mi servono qui accanto.
    echo.
    echo Probabilmente stai lanciando questo file DENTRO lo zip, senza
    echo averlo estratto: Windows lo copia da solo in una cartella
    echo temporanea e il resto non lo trova.
    echo.
    echo Tasto destro sullo zip, "Estrai tutto...", scegli il Desktop,
    echo poi rilancia questo file dalla cartella estratta.
    echo.
    pause
    exit /b
)

where py >nul 2>nul
if errorlevel 1 (
    echo Non trovo il comando "py". Installa Python prima di continuare.
    pause
    exit /b
)

py "%~dp0osserva_cartella.py"
pause
