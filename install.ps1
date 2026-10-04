# DocCheck Installer (PowerShell)
# Использование: powershell -ExecutionPolicy Bypass -File install.ps1 [-WithOda] [-WithModels] [-NoStart]

param(
    [switch]$WithOda,
    [switch]$WithModels,
    [switch]$NoStart,
    [switch]$SkipNode,
    [switch]$SkipPython,
    [switch]$Help
)

$INSTALL_DIR = "C:\opt\doccheck"
$BACKEND_DIR = "$INSTALL_DIR\backend"
$FRONTEND_DIR = "$INSTALL_DIR\frontend"
$TOOLS_DIR = "$INSTALL_DIR\tools"

Write-Host "=== DocCheck Installer (PowerShell) ==="

if ($Help) {
    Write-Host "Использование: install.ps1 [-WithOda] [-WithModels] [-NoStart] [-SkipNode] [-SkipPython] [-Help]"
    exit 0
}

# --- Docker ---
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Установка Docker..."
    winget install --id Docker.DockerDesktop -e --silent
}

# --- Docker Compose ---
$composePath = "$env:ProgramFiles\Docker\Docker\resources\bin\docker-compose.exe"
if (-not (Test-Path $composePath)) {
    Write-Host "Установка Docker Compose..."
    Invoke-WebRequest -Uri "https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-windows-x86_64.exe" -OutFile "$env:USERPROFILE\docker-compose.exe"
    Write-Host "Скопируйте docker-compose.exe в $composePath"
}

# --- Node.js ---
if (-not $SkipNode -and -not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "Установка Node.js..."
    winget install --id OpenJS.NodeJS -e --silent
}

# --- Python ---
if (-not $SkipPython -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Установка Python..."
    winget install --id Python.Python.3.12 -e --silent
}

# --- Клонирование ---
if (-not (Test-Path $INSTALL_DIR)) {
    Write-Host "Клонирование репозитория..."
    git clone https://github.com/gubarandrej-bit/doc-check-ai.git $INSTALL_DIR
}
else {
    cd $INSTALL_DIR
    git pull origin main
}
cd $INSTALL_DIR

# --- Зависимости ---
Write-Host "Установка зависимостей бэкенда..."
pip install -r backend\requirements.txt

Write-Host "Установка зависимостей фронтенда..."
cd $FRONTEND_DIR
npm install
cd $INSTALL_DIR

# --- Конфиги ---
if (-not (Test-Path backend\.env)) {
    Copy-Item backend\.env.example backend\.env
}

# --- ODA File Converter ---
if ($WithOda) {
    Write-Host "Обработка ODA File Converter..."
    $deb = Get-ChildItem -Path . -Filter "ODAFileConverter*.deb" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($deb) {
        Write-Host "Найден установщик ODA: $($deb.Name)"
        # Установка через winget или ручная
        Write-Host "Установите ODA вручную: dpkg -i $($deb.Name)"
        Write-Host "Или: winget install --id OpenDesign.ODAFileConverter"
        # Копируем конвертер
        New-Item -ItemType Directory -Force -Path "$TOOLS_DIR\oba" | Out-Null
        $odaExe = "C:\Program Files\ODAFileConverter\ODAFileConverter.exe"
        if (Test-Path $odaExe) {
            Copy-Item $odaExe "$TOOLS_DIR\oba\ODAFileConverter.exe"
            Write-Host "ODA скопирован в $TOOLS_DIR\oba"
        }
        else {
            Write-Host "ODA конвертер не найден. Укажите путь через ODA_CONVERTER_PATH."
        }
        # Перезапуск бэкенда
        docker compose up -d --build backend
    }
    else {
        Write-Host "Файл ODAFileConverter*.deb не найден."
        Write-Host "Скачайте с https://www.opendesign.com/guestfiles/oda_file_converter"
    }
}

# --- Запуск ---
if (-not $NoStart) {
    Write-Host "Запуск системы..."
    docker compose up -d
    Write-Host "Система запущена. Откройте http://localhost:80"
}
else {
    Write-Host "Установка завершена без запуска."
}