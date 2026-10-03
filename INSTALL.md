# Установка и запуск DocCheck

## Вариант 1: Docker / docker-compose (рекомендуется для Proxmox)

Требования: Docker 20+, docker-compose.

```bash
git clone https://github.com/gubarandrej-bit/doc-check-ai.git
cd doc-check-ai

# 1. Скопируйте и отредактируйте конфигуляцию
cp backend/.env.example backend/.env
# Обязательно замените SECRET_KEY на случайную строку, например:
python3 -c "import secrets; print(secrets.token_hex(32))"

# 2. Запустите
docker compose up -d --build

# 3. Откройте в браузере
http://localhost:80
```

- Фронтенд: `http://localhost:80`
- API + Swagger: `http://localhost:8000/docs`
- Логи: `docker compose logs -f`

### Настройка под ваш сервер (Proxmox)

Сервер: CPU 8 ядер AMD-FX 8120, RAM 24 ГБ, SSD 60 ГБ, без GPU (при необходимости — AMD HD 7950 3 ГБ).

- Процессор и память — достаточны для работы системы и локальной модели ИИ (Ollama).
- При использовании **локальной** модели ИИ установите Ollama отдельно:
  `curl -fsSL https://ollama.com/install.sh | sh` и загрузите модель `ollama pull llama3.1:8b`.
- При использовании **облачной** модели — укажите API-ключ в модели ИИ (например, OpenRouter).
- Данные (БД, загрузки, отчёты) хранятся в volume `doccheck-data`.

## Вариант 2: Без Docker (локальная разработка)

### Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Логин и пароль администратора (по умолчанию)
```
login:    admin
password: admin123
```
После первого входа обязательно смените пароль через раздел **Пользователи**.

## Поддерживаемые форматы входных данных
`xls`, `xlsx`, `doc`, `docx`, `pdf`, `dwg`, `zip`.

**Важно:** `dwg`-файлы (AutoCAD) не могут быть расшифрованы системой без специализированного
ПО (например, ODA File Converter). При загрузке только `dwg` соответствующие проверки
помечаются как не проведённые с указанием причины — данные не придумываются.