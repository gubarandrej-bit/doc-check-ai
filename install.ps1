<#
.SYNOPSIS
    DocCheck — единый скрипт установки для Windows.

.DESCRIPTION
    Готовит окружение и запускает систему проверки документации:
      - проверяет (и при необходимости подсказывает как установить) Docker Desktop,
        Node.js, npm и Python;
      - создаёт .env со случайным SECRET_KEY;
      - поднимает контейнеры бэкенда, фронтенда и Ollama;
      - проверяет готовность бэкенда.

    Скрипт идемпотентен — его можно запускать повторно.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\install.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\install.ps1 -WithModels
#>

[CmdletBinding()]
param(
    # Скачать бесплатные модели в Ollama после запуса
    [switch]$WithModels,
    # Не запускать контейнеры (только подготовить окружение)
    [switch]$NoStart,
    # Текстовая модель для Ollama
    [string]$TextModel = 'qwen2.5:7b-instruct',
    # Мультимодальная модель для анализа чертежей
    [string]$VisionModel = 'qwen2.5vl:7b'
)

$ErrorActionPreference = 'Continue'

function Write-Step { param([string]$Message) Write-Host "[DocCheck] $Message" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Message) Write-Host "  OK  $Message" -ForegroundColor Green }
function Write-Warn { param([string]$Message) Write-Host "  !   $Message" -ForegroundColor Yellow }
function Write-Err  { param([string]$Message) Write-Host "  X   $Message" -ForegroundColor Red }

# Каталог проекта — тот, где лежит сам скрипт.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host ''
Write-Step 'DocCheck — установка на Windows'
Write-Host ''

# ---------------------------------------------------------------------------
# 1. Docker Desktop
# ---------------------------------------------------------------------------
Write-Step 'Шаг 1/5: Docker Desktop'
$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($docker) {
    try {
        $ver = docker --version 2>&1
        Write-Ok "Docker найден: $ver"
    } catch {
        Write-Warn 'Docker установлен, но не отвечает — запустите Docker Desktop'
    }
} else {
    Write-Warn 'Docker не найден. Установите Docker Desktop:'
    Write-Host '      https://www.docker.com/products/docker-desktop/'
    Write-Host '      После установки перезапустите терминал и запустите скрипт заново.'
    if (-not $NoStart) {
        Write-Warn 'Продолжение невозможно без Docker — прерываю.'
        exit 1
    }
}

# Проверяем, запущен ли Docker Engine (а не только установлен клиент).
if ($docker -and -not $NoStart) {
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Warn 'Docker Engine не запущен. Откройте Docker Desktop и дождитесь'
        Write-Host '      сообщения о готовности, затем запустите скрипт заново.'
        exit 1
    }
}

# ---------------------------------------------------------------------------
# 2. Node.js и npm
# ---------------------------------------------------------------------------
Write-Step 'Шаг 2/5: Node.js и npm'
$node = Get-Command node -ErrorAction SilentlyContinue
$npm  = Get-Command npm  -ErrorAction SilentlyContinue
if ($node -and $npm) {
    Write-Ok "Node.js $(node --version), npm $(npm --version)"
} else {
    Write-Warn 'Node.js или npm не найдены. Docker соберёт фронтенд самостоятельно.'
    Write-Host '      Если нужен локальный запуск: https://nodejs.org/'
}

# ---------------------------------------------------------------------------
# 3. Python
# ---------------------------------------------------------------------------
Write-Step 'Шаг 3/5: Python'
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if ($py) {
    try { Write-Ok "Python $(python --version 2>&1)" }
    catch { Write-Ok "Python найден ($($py.Source))" }
} else {
    Write-Warn 'Python не найден. Docker запустит бэкенд самостоятельно.'
    Write-Host '      Если нужен локальный запус: https://www.python.org/downloads/'
    Write-Host '      При установке включите галочку "Add Python to PATH".'
}

# ---------------------------------------------------------------------------
# 4. Конфигурация
# ---------------------------------------------------------------------------
Write-Step 'Шаг 4/5: конфигурация'
$EnvFile = Join-Path $ScriptDir '.env'

if (Test-Path $EnvFile) {
    Write-Ok '.env уже существует — не перезаписываю'
} else {
    $Example = Join-Path $ScriptDir 'backend\.env.example'
    if (Test-Path $Example) {
        Copy-Item $Example $EnvFile
        Write-Ok '.env создан из backend\.env.example'
    } else {
        @"
MODE=local
SECRET_KEY=CHANGE-ME
DATABASE_URL=sqlite:///data/doccheck.db
FRONTEND_URL=http://localhost
OPENROUTER_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
"@ | Set-Content -Path $EnvFile -Encoding UTF8
        Write-Ok '.env создан с нуля'
    }

    # Генерируем криптографически стойкий ключ.
    $bytes = New-Object byte[] 48
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $key = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '').Replace('/', '')

    $content = Get-Content $EnvFile -Raw -Encoding UTF8
    $content = [regex]::Replace($content, '(?m)^SECRET_KEY=.*$', "SECRET_KEY=$key")
    Set-Content -Path $EnvFile -Value $content -Encoding UTF8 -NoNewline
    Write-Ok 'SECRET_KEY сгенерирован'
}

# Каталог для ODA File Converter.
$OdaDir = Join-Path $ScriptDir 'tools\oda'
if (-not (Test-Path $OdaDir)) {
    New-Item -ItemType Directory -Path $OdaDir | Out-Null
}
Write-Ok 'каталог tools\oda готов (инструкция: tools\oda\README.md)'

# ---------------------------------------------------------------------------
# 5. Запуск
# ---------------------------------------------------------------------------
Write-Step 'Шаг 5/5: сборка и запуск контейнеров'

if ($NoStart) {
    Write-Warn 'Запуск пропущен (-NoStart). Запустить позже: docker compose up -d --build'
    exit 0
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Err 'Docker недоступен — запустите систему позже: docker compose up -d --build'
    exit 1
}

Write-Host '  Сборка и запуск занимает несколько минут...'
docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Err 'Не удалось запустить контейнеры — смотрите вывод выше'
    exit 1
}
Write-Ok 'Контейнеры запущены'

# Ждём готовность бэкенда.
Write-Host '  Ожидание готовности бэкенда (до 60 секунд)...'
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        Invoke-WebRequest -Uri 'http://localhost:8000/health' -UseBasicParsing -TimeoutSec 3 | Out-Null
        $ready = $true
        break
    } catch { Start-Sleep -Seconds 2 }
}
if ($ready) {
    Write-Ok 'Бэкенд отвечает: http://localhost:8000/health'
} else {
    Write-Warn 'Бэкенд не ответил за 60 секунд — проверьте: docker compose logs -f backend'
}

# ---------------------------------------------------------------------------
# Необязательно: бесплатные модели
# ---------------------------------------------------------------------------
if ($WithModels) {
    Write-Step 'Скачивание бесплатных моделей в Ollama (это долго)'
    docker compose exec -T ollama ollama pull $TextModel
    if ($LASTEXITCODE -eq 0) { Write-Ok "текстовая модель: $TextModel" }
    else { Write-Warn "не удалось скачать $TextModel" }

    docker compose exec -T ollama ollama pull $VisionModel
    if ($LASTEXITCODE -eq 0) { Write-Ok "vision-модель: $VisionModel" }
    else { Write-Warn "не удалось скачать $VisionModel" }

    Write-Warn 'Добавьте модели через веб-интерфейс: Модели ИИ -> Добавить'
}

# ---------------------------------------------------------------------------
# Итог
# ---------------------------------------------------------------------------
Write-Host ''
Write-Step 'Установка завершена.'
Write-Host ''
Write-Host '  Веб-интерфейс:  http://localhost'
Write-Host '  API бэкенда:    http://localhost:8000/docs'
Write-Host ''
Write-Host '  Вход по умолчанию:  admin / admin123   (смените пароль после первого входа)'
Write-Host ''
Write-Host '  Полезные команды:'
Write-Host '    docker compose logs -f backend      логи бэкенда'
Write-Host '    docker compose ps                   состояние контейнеров'
Write-Host '    docker compose down                 остановить систему'
Write-Host '    docker compose up -d --build        пересобрать после изменений'
Write-Host ''
Write-Warn 'Для чертежей DWG нужен ODA File Converter — инструкция в tools\oda\README.md'
Write-Host ''