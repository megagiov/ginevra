@echo off
rem Avvia la sorveglianza automatica della cartella Download.
rem Lascia aperta questa finestra: ogni LDV che scarichi da un corriere
rem viene brandizzata da sola e si apre pronta per Ctrl+P.
rem Per fermarla, chiudi questa finestra.

where py >nul 2>nul
if errorlevel 1 (
    echo Non trovo il comando "py". Installa Python prima di continuare.
    pause
    exit /b
)

py "%~dp0osserva_cartella.py"
pause
