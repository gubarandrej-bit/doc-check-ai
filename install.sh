#!/bin/bash
set -e

INSTALL_DIR="/opt/doccheck"
BACKEND_DIR="${INSTALL_DIR}/backend"
FRONTEND_DIR="${INSTALL_DIR}/frontend"
TOOLS_DIR="${INSTALL_DIR}/tools"

echo "=== DocCheck Installer ==="
echo "Режим: $(whoami)"

echo "--- Проверка прав root ---"
if [ "$(id -u)" -ne 0 ]; then
    echo "Ошибка: требуются права root (sudo)"
    exit 1
fi

# --- Обработка аргументов ---
WITH_ODA=0
WITH_MODELS=0
NO_START=0
SKIP_NODE=0
SKIP_PYTHON=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --with-oda|-WithOda)
            WITH_ODA=1
            shift
            ;;
        --with-models|-WithModels)
            WITH_MODELS=1
            shift
            ;;
        --no-start|-NoStart)
            NO_START=1
            shift
            ;;
        --skip-node)
            SKIP_NODE=1
            shift
            ;;
        --skip-python)
            SKIP_PYTHON=1
            shift
            ;;
        --help|-?)
            echo "Использование: sudo bash install.sh [--with-oda] [--with-models] [--no-start] [--skip-node] [--skip-python] [--help]"
            exit 0
            ;;
        *)
            echo "Неизвестный аргумент: $1"
            exit 1
            ;;
    esac
done

# --- Базовая установка ---
echo "--- Обновление пакетов ---"
apk update || apt-get update || yum update

echo "--- Установка Docker ---"
if ! command -v docker &> /dev/null; then
    if command -v apt-get &> /dev/null; then
        apt-get install -y ca-certify curl gnupg lsb-release
        curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add -
        add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian \$(lsb_release -cs) stable"
        apt-get update
        apt-get install -y docker-ce docker-ce-cli containerd.io
    elif command -v yum &> /dev/null; then
        yum install -y yum-utils
        yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        yum install -y docker-ce docker-ce-cli containerd.io
    fi
fi

echo "--- Установка Docker Compose ---"
DOCKER_COMPOSE_VERSION="v2.24.5"
mkdir -p /etc/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /opt/docker-compose
chmod +x /opt/docker-compose
ln -sf /opt/docker-compose /usr/local/bin/docker-compose

# --- Node.js ---
if [ "$SKIP_NODE" -ne 1 ]; then
    if ! command -v node &> /dev/null; then
        if command -v apt-get &> /dev/null; then
            curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
            apt-get install -y nodejs
        elif command -v yum &> /dev/null; then
            curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
            yum install -y nodejs
        fi
    fi
fi

# --- Python ---
if [ "$SKIP_PYTHON" -ne 1 ]; then
    if ! command -v python3 &> /dev/null; then
        if command -v apt-get &> /dev/null; then
            apt-get install -y python3 python3-pip python3-venv
        elif command -v yum &> /dev/null; then
            yum install -y python3 python3-pip
        fi
    fi
fi

# --- Клонирование репозитория ---
echo "--- Клонирование репозитория ---"
if [ -d "${INSTALL_DIR}/.git" ]; then
    cd "${INSTALL_DIR}"
    git pull origin main
else
    git clone https://github.com/gubarandrej-bit/doc-check-ai.git "${INSTALL_DIR}"
fi
cd "${INSTALL_DIR}"

# --- Установка зависимостей бэкенда ---
echo "--- Установка зависимостей бэкенда ---"
pip install -r backend/requirements.txt

# --- Установка зависимостей фронтенда ---
echo "--- Установка зависимостей фронтенда ---"
cd "${FRONTEND_DIR}"
npm install
cd "${INSTALL_DIR}"

# --- Базовые конфиги ---
echo "--- Настройка конфигов ---"
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
fi

# --- ODA File Converter ---
if [ "$WITH_ODA" -eq 1 ]; then
    echo "--- Обработка ODA File Converter ---"
    # Ищем .deb файл в текущей директории
    ODA_DEB=$(ls ODAFileConverter_QT6_lnxX64_11dll_*.deb 2>/dev/null || true)
    if [ -n "$ODA_DEB" ]; then
        echo "Найден установщик ODA: $ODA_DEB"
        # Проверяем gdebi
        if command -v gdebi &> /dev/null; then
            echo "Установка ODA через gdebi..."
            gdebi --non-interactive "$ODA_DEB"
        else
            echo "gdebi не найден, пробуем dpkg..."
            dpkg -i "$ODA_DEB" 2>/dev/null || true
        fi
        # Копируем конвертер в tools/oba/
        mkdir -p "${TOOLS_DIR}/oba"
        # Ищем сам исполняемый в распространенных местах
        ODA_EXE=$(which ODAFileConverter 2>/dev/null || find /opt/ODAFileConverter -name "ODAFileConverter" -type f 2>/dev/null | head -1)
        if [ -n "$ODA_EXE" ]; then
            cp "$ODA_EXE" "${TOOLS_DIR}/oba/ODAFileConverter"
            chmod +x "${TOOLS_DIR}/oba/ODAFileConverter"
            echo "ODA скопирован в ${TOOLS_DIR}/oba/"
        else
            echo "ОДА конвертер не найден в распространенных путях. Добавьте путь через ODA_CONVERTER_PATH."
        fi
        # Перезапуск бэкенда
        echo "Перезапуск бэкенда с ODA..."
        cd "${INSTALL_DIR}"
        docker compose up -d --build backend
    else
        echo "Файл ODAFileConverter*.deb не найден в текущей директории."
        echo "Необходимо скачать файл с https://www.opendesign.com/guestfiles/oda_file_converter"
        echo "Или запустите без флага --with-oda."
        echo "Для ручной установки:"
        echo "  1. Скачайте ODAFileConverter_QT6_lnxX64_11dll_*.deb"
        echo "  2. Положите его в ту же директорию, где этот скрипт"
        echo "  3. Запустите: sudo bash install.sh --with-oda"
    fi
fi

# --- Запуск ---
if [ "$NO_START" -ne 1 ]; then
    echo "--- Запуск системы ---"
    cd "${INSTALL_DIR}"
    docker compose up -d
    echo "Система запущена. Откройте http://localhost:80"
else
    echo "Установка завершена без запуска. Запустите: cd ${INSTALL_DIR} && docker compose up -d"
fi