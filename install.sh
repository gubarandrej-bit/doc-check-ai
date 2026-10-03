#!/usr/bin/env bash
#
# DocCheck — единый скрипт установки (Linux / Proxmox LXC / Ubuntu / Debian).
#
# Устанавливает всё необходимое и запускает систему:
#   - Docker Engine + Docker Compose
#   - Node.js 20 LTS + npm        (для сборки фронтенда без Docker)
#   - Python 3.11 + pip + venv    (для запуска бэкенда без Docker)
#   - переменные окружения .env со случайным SECRET_KEY
#   - контейнеры бэкенда, фронтенда и Ollama
#
# Скрипт идемпотентен: его можно запускать повторно без вреда.
#
# Использование:
#   sudo ./install.sh                     # всё по умолчанию
#   sudo ./install.sh --with-models       # + скачать бесплатные модели в Ollama
#   sudo ./install.sh --skip-node         # не ставить Node.js (Docker его не требует)
#   sudo ./install.sh --skip-python       # не ставить Python
#   sudo ./install.sh --no-start          # только установить, не запускать
#   ./install.sh --help
#
set -uo pipefail

# ---------------------------------------------------------------------------
# Настройки запуска
# ---------------------------------------------------------------------------
WITH_MODELS=0
SKIP_NODE=0
SKIP_PYTHON=0
NO_START=0
OLLAMA_TEXT_MODEL="${OLLAMA_TEXT_MODEL:-qwen2.5:7b-instruct}"
OLLAMA_VISION_MODEL="${OLLAMA_VISION_MODEL:-qwen2.5vl:7b}"

RED=''; GREEN=''; YELLOW=''; BLUE=''; RESET=''
if [ -t 1 ]; then
  RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[0;33m'
  BLUE=$'\033[0;34m'; RESET=$'\033[0m'
fi

log()  { printf '%s[DocCheck]%s %s\n' "$BLUE" "$RESET" "$*"; }
ok()   { printf '%s  ✓%s %s\n' "$GREEN" "$RESET" "$*"; }
warn() { printf '%s  !%s %s\n' "$YELLOW" "$RESET" "$*"; }
err()  { printf '%s  ✗%s %s\n' "$RED" "$RESET" "$*"; }

usage() {
  # Печатаем шапку скрипта (комментарии) как справку, без пустых строк по краям.
  sed -n '3,20p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

while [ $# -gt 0 ]; do
  case "$1" in
    --with-models) WITH_MODELS=1 ;;
    --skip-node)   SKIP_NODE=1 ;;
    --skip-python) SKIP_PYTHON=1 ;;
    --no-start)    NO_START=1 ;;
    -h|--help)     usage ;;
    *) err "Неизвестный аргумент: $1 (см. --help)"; exit 1 ;;
  esac
  shift
done

# ---------------------------------------------------------------------------
# Проверка прав: нужен root 或 sudo
# ---------------------------------------------------------------------------
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
    warn "Запуск не от root — команды будут выполняться через sudo"
  else
    err "Нужен root или sudo. Запустите: sudo ./install.sh"
    exit 1
  fi
fi

as_root() { if [ -n "$SUDO" ]; then sudo "$@"; else "$@"; fi; }

# Каталог проекта — тот, где лежит сам скрипт.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || { err "Не удалось перейти в каталог $SCRIPT_DIR"; exit 1; }

# ---------------------------------------------------------------------------
# Определение дистрибутива
# ---------------------------------------------------------------------------
DISTRO_ID="$( . /etc/os-release 2>/dev/null && echo "$ID" )"
DISTRO_CODENAME="$( . /etc/os-release 2>/dev/null && echo "${VERSION_CODENAME:-}" )"
DISTRO_VERSION="$( . /etc/os-release 2>/dev/null && echo "${VERSION_ID:-}" )"

case "$DISTRO_ID" in
  ubuntu|debian) SUPPORTED=1 ;;
  *) SUPPORTED=0 ;;
esac

log "Дистрибутив: ${DISTRO_ID:-неизвестен} ${DISTRO_VERSION:-} (${DISTRO_CODENAME:-})"
if [ "$SUPPORTED" -ne 1 ]; then
  warn "Скрипт рассчитан на Ubuntu и Debian. На ${DISTRO_ID:-другой} дистрибутив"
  warn "автоматическая установка пакетов не выполняется — продолжение может завершиться ошибкой."
fi

# ---------------------------------------------------------------------------
# 1. Базовые утилиты
# ---------------------------------------------------------------------------
log "Шаг 1/6: базовые утилиты"
export DEBIAN_FRONTEND=noninteractive
if [ "$SUPPORTED" -eq 1 ]; then
  as_root apt-get update -qq 2>/dev/null
  as_root apt-get install -y -qq curl ca-certificates gnupg git 2>/dev/null \
    && ok "curl, ca-certificates, gnupg, git установлены" \
    || warn "не удалось установить базовые пакеты через apt"
else
  command -v curl >/dev/null 2>&1 && ok "curl уже есть" \
    || err "curl отсутствует и не может быть установлен автоматически"
fi

# ---------------------------------------------------------------------------
# 2. Docker Engine + Docker Compose
# ---------------------------------------------------------------------------
log "Шаг 2/6: Docker Engine и Docker Compose"

have_compose() { docker compose version >/dev/null 2>&1; }

if command -v docker >/dev/null 2>&1 && have_compose; then
  ok "Docker и Compose уже установлены: $(docker --version)"
else
  if [ "$SUPPORTED" -eq 1 ]; then
    log "устанавливаю Docker из официального репозитория..."
    as_root install -m 0755 -d /etc/apt/keyrings
    as_root curl -fsSL "https://download.docker.com/linux/${DISTRO_ID}/gpg" \
      -o /etc/apt/keyrings/docker.asc
    as_root chmod a+r /etc/apt/keyrings/docker.asc
    as_root sh -c "echo 'deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/${DISTRO_ID} ${DISTRO_CODENAME} stable' \
> /etc/apt/sources.list.d/docker.list"
    as_root apt-get update -qq
    as_root apt-get install -y -qq docker-ce docker-ce-cli containerd.io \
      docker-buildx-plugin docker-compose-plugin
  else
    warn "пытаюсь установить Docker универсальным скриптом get.docker.com"
    as_root sh -c "curl -fsSL https://get.docker.com -o /tmp/get-docker.sh && sh /tmp/get-docker.sh"
  fi

  if command -v docker >/dev/null 2>&1; then
    as_root systemctl enable --now docker >/dev/null 2>&1 || true
    ok "Docker установлен: $(docker --version)"
  else
    err "Docker не установился. Установите его вручную и запустите скрипт заново."
    exit 1
  fi
fi

have_compose || warn "плагин docker compose недоступен — проверьте docker-buildx-plugin/docker-compose-plugin"

# ---------------------------------------------------------------------------
# 3. Node.js и npm
# ---------------------------------------------------------------------------
log "Шаг 3/6: Node.js и npm"
if [ "$SKIP_NODE" -eq 1 ]; then
  warn "пропущено по --skip-node"
elif command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
  ok "Node.js уже есть: $(node --version), npm $(npm --version)"
elif [ "$SUPPORTED" -eq 1 ]; then
  log "устанавливаю Node.js 20 LTS (NodeSource)..."
  as_root curl -fsSL "https://deb.nodesource.com/setup_20.x" | as_root bash - >/dev/null 2>&1
  if as_root apt-get install -y -qq nodejs; then
    ok "Node.js установлен: $(node --version)"
  else
    warn "Node.js не установился через NodeSource — фронтенд соберётся внутри Docker"
  fi
else
  warn "пропускаю установку Node.js (дистрибутив не поддерживается автоматически)"
fi

# ---------------------------------------------------------------------------
# 4. Python и pip
# ---------------------------------------------------------------------------
log "Шаг 4/6: Python, pip и venv"
if [ "$SKIP_PYTHON" -eq 1 ]; then
  warn "пропущено по --skip-python"
else
  if [ "$SUPPORTED" -eq 1 ] && ! command -v python3 >/dev/null 2>&1; then
    log "устанавливаю Python 3..."
    as_root apt-get install -y -qq python3 python3-pip python3-venv 2>/dev/null || true
  fi
  if command -v python3 >/dev/null 2>&1; then
    ok "Python: $(python3 --version)"
    python3 -m pip --version >/dev/null 2>&1 \
      || warn "pip недоступен (в Debian 12+: установите python3-pip)"
    python3 -c "import venv" >/dev/null 2>&1 \
      || warn "модуль venv отсутствует (установите python3-venv)"
  else
    warn "Python 3 не найден — бэкенд запустится внутри Docker"
  fi
fi

# ---------------------------------------------------------------------------
# 5. Файлы конфигурации
# ---------------------------------------------------------------------------
log "Шаг 5/6: конфигурация"

# Секретный ключ: генерируем, только если .env ещё нет.
if [ -f .env ]; then
  ok ".env уже существует — не перезаписываю"
else
  cp backend/.env.example .env 2>/dev/null || {
    warn "не нашёл backend/.env.example — создам .env с нуля"
    cat > .env <<EOF
MODE=local
SECRET_KEY=CHANGE-ME
DATABASE_URL=sqlite:///data/doccheck.db
FRONTEND_URL=http://localhost
OPENROUTER_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
EOF
  }
  if command -v python3 >/dev/null 2>&1; then
    NEW_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  else
    NEW_KEY="$(head -c 48 /dev/urandom | base64 | tr -d '=+/' | head -c 48)"
  fi
  if command -v sed >/dev/null 2>&1; then
    sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${NEW_KEY}|" .env
    ok ".env создан, SECRET_KEY сгенерирован"
  else
    warn ".env создан, но SECRET_KEY не удалось подставить — замените его вручную"
  fi
fi

if [ ! -f .env ]; then
  err ".env не создан и не найден — дальнейший запуск невозможен"
  exit 1
fi

# Каталог для ODA File Converter (монтируется в контейнер как /opt/oda).
mkdir -p tools/oda
ok "каталог tools/oda готов (положите туда ODAFileConverter — см. tools/oda/README.md)"

# ---------------------------------------------------------------------------
# 6. Запуск
# ---------------------------------------------------------------------------
log "Шаг 6/6: сборка и запуск контейнеров"

if [ "$NO_START" -eq 1 ]; then
  warn "запуск пропущен (--no-start). Запустить позже: docker compose up -d --build"
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  err "Docker недоступен — запустите систему позже командой: docker compose up -d --build"
  exit 1
fi

log "собираю и запускаю контейнеры (это может занять несколько минут)..."
if as_root docker compose up -d --build; then
  ok "контейнеры запущены"
else
  err "не удалось запустить контейнеры — смотрите вывод выше"
  exit 1
fi

# Ждём готовности бэкенда.
log "жду готовности бэкенда (до 60 секунд)..."
READY=0
for _ in $(seq 1 30); do
  if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then READY=1; break; fi
  sleep 2
done
if [ "$READY" -eq 1 ]; then
  ok "бэкенд отвечает: http://localhost:8000/health"
else
  warn "бэкенд не ответил за 60 секунд — проверьте: docker compose logs -f backend"
fi

# ---------------------------------------------------------------------------
# Необязательно: бесплатные модели для Ollama
# ---------------------------------------------------------------------------
if [ "$WITH_MODELS" -eq 1 ]; then
  log "скачиваю бесплатные модели в Ollama (это может занять много времени)"
  if as_root docker compose exec -T ollama ollama pull "$OLLAMA_TEXT_MODEL"; then
    ok "текстовая модель: $OLLAMA_TEXT_MODEL"
  else
    warn "не удалось скачать $OLLAMA_TEXT_MODEL"
  fi
  if as_root docker compose exec -T ollama ollama pull "$OLLAMA_VISION_MODEL"; then
    ok "vision-модель: $OLLAMA_VISION_MODEL"
  else
    warn "не удалось скачать $OLLAMA_VISION_MODEL (нужна для анализа чертежей)"
  fi
  warn "не забудьте добавить эти модели через веб-интерфейс: Модели ИИ → Добавить"
fi

# ---------------------------------------------------------------------------
# Итог
# ---------------------------------------------------------------------------
echo
log "Установка завершена."
echo
echo "  Веб-интерфейс:  http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo localhost)"
echo "  API бэкенда:    http://localhost:8000/docs"
echo
echo "  Вход по умолчанию:  admin / admin123   (смените пароль после первого входа)"
echo
echo "  Полезные команды:"
echo "    docker compose logs -f backend      логи бэкенда"
echo "    docker compose ps                   состояние контейнеров"
echo "    docker compose down                 остановить систему"
echo "    docker compose up -d --build        запустить заново после изменений"
echo
warn "Чертежи DWG требуют ODA File Converter — инструкция в tools/oda/README.md"
echo