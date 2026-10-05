# Installa tutto il necessario per l'agente video su Windows.
# Uso: tasto destro su setup.ps1 -> "Esegui con PowerShell"
#   oppure da PowerShell:  powershell -ExecutionPolicy Bypass -File setup.ps1
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
$riapri = $false

if (-not (Have 'py')) {
    Write-Host '> Installo Python 3.12...'
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    $riapri = $true
}
if (-not (Have 'ffmpeg')) {
    Write-Host '> Installo FFmpeg (build completa, con sottotitoli)...'
    winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
    $riapri = $true
}
if ($riapri) {
    Write-Host ''
    Write-Host 'Python/FFmpeg installati. CHIUDI e RIAPRI PowerShell, poi rilancia setup.ps1.' -ForegroundColor Yellow
    exit 0
}

Write-Host '> Installo i pacchetti Python...'
py -m pip install --upgrade pip
py -m pip install -r requirements.txt

New-Item -ItemType Directory -Force fonts, music, assets, projects, outputs | Out-Null
$fonts = @{
    'Montserrat-ExtraBold.woff' = 'https://cdn.jsdelivr.net/npm/@fontsource/montserrat@5/files/montserrat-latin-800-normal.woff'
    'OpenSans-Bold.woff'        = 'https://cdn.jsdelivr.net/npm/@fontsource/open-sans@5/files/open-sans-latin-700-normal.woff'
}
foreach ($k in $fonts.Keys) {
    if (-not (Test-Path "fonts/$k")) {
        Write-Host "> Scarico il font $k"
        Invoke-WebRequest $fonts[$k] -OutFile "fonts/$k"
    }
}

Write-Host '> Preparo il modello di trascrizione (la prima volta ~500 MB)...'
py -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"

Write-Host ''
py ve.py doctor
