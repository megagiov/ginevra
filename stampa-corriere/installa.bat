@echo off
echo ===========================================
echo   Installazione - Maschera LDV GM Vegasi
echo ===========================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo PROBLEMA: Python non risulta installato su questo computer.
    echo.
    echo Installa prima Python da python.org, poi rilancia questo file.
    echo.
    pause
    exit /b
)

echo [1 di 3] Installo le librerie PyMuPDF e Playwright...
echo.
py -m pip install PyMuPDF playwright
if errorlevel 1 (
    echo.
    echo PROBLEMA durante l'installazione delle librerie: leggi il messaggio sopra.
    pause
    exit /b
)

echo.
echo [2 di 3] Scarico il browser Chromium, puo' richiedere qualche minuto...
echo.
py -m playwright install chromium
if errorlevel 1 (
    echo.
    echo PROBLEMA durante il download di Chromium: leggi il messaggio sopra.
    pause
    exit /b
)

echo.
echo [3 di 3] Verifico che sia tutto a posto...
py -c "import fitz, playwright" 2>nul
if errorlevel 1 (
    echo.
    echo PROBLEMA: le librerie risultano installate ma non si avviano.
    pause
    exit /b
)

echo.
echo ===========================================
echo   Installazione completata.
echo.
echo   Da ora usa avvia_osservatore.bat:
echo   lascialo aperto e le LDV che scarichi
echo   vengono brandizzate da sole.
echo ===========================================
echo.
pause
