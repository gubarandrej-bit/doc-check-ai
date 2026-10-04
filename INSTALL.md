# Установка и запуск DocCheck

Система проверки проектной и рабочей документации по инженерным системам зданий
на соответствие нормативно-техническим требованиям (НТД) Российской Федерации.

---

## Способ 1: единый скрипт (рекомендуется)

Скрипт сам установит всё необходимое, создаст конфигурацию, соберёт и запустит систему.

### Linux, Proxmox LXC, Ubuntu, Debian

```bash
git clone https://github.com/gubarandrej-bit/doc-check-ai.git
cd doc-check-ai
sudo bash install.sh
```

Скрипт устанавливает: Docker Engine и Docker Compose, Node.js 20 LTS с npm,
Python 3 с pip и venv, генерирует случайный `SECRET_KEY`, поднимает контейнеры
бэкенда, фронтенда и Ollama, затем проверяет готовность бэкенда.

### Windows

```powershell
git clone https://github.com/gubarandrej-bit/doc-check-ai.git
cd doc-check-ai
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

На Windows Docker Desktop устанавливается отдельно:
<https://www.docker.com/products/docker-desktop/>

### Ключи скрипта

`install.sh` и `install.ps1` понимают одинаковые аргументы:

| Аргумент | Действие |
|---|---|
| `--with-models` / `-WithModels` | после запуска скачать бесплатные модели в Ollama |
| `--no-start` / `-NoStart` | только установить, не запускать |
| `--skip-node` (только `sh`) | не устанавливать Node.js |
| `--skip-python` (только `sh`) | не устанавливать Python |
| `--help` / `-?` | справка |

Запуск через `bash install.sh` работает независимо от прав на файл.
Если хотите запускать как `./install.sh`, выполните один раз `chmod +x install.sh`.

Скрипт идемпотентен — его можно запускать повторно, существующие данные и `.env`
не перезаписываются.

После установки:

- Веб-интерфейс — `http://<адрес-сервера>` (порт 80)
- API — `http://<адрес-сервера>/api/...` (тот же порт, запросы проксирует nginx)
- Swagger — `http://<адрес-сервера>:8000/docs`

Интерфейс и API живут на одном адресе: контейнер фронтенда запускает nginx,
который отдаёт статику и проксирует `/api/*` на бэкенд. Благодаря этому
браузеру не мешает политика CORS. Порт 8000 наружу открывать не обязательно.

---

## Способ 2: Docker вручную

Требуется Docker 20+ и Docker Compose v2.

```bash
git clone https://github.com/gubarandrej-bit/doc-check-ai.git
cd doc-check-ai

cp backend/.env.example .env
# Обязательно замените SECRET_KEY на случайную строку:
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

docker compose up -d --build
```

`SECRET_KEY` генерируется командой выше — вставьте результат в файл `.env`.

---

## Способ 3: без Docker (разработка)

### Бэкенд

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # отредактируйте SECRET_KEY
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Фронтенд

```bash
cd frontend
npm install
npm run dev
```

Фронтенд проксирует `/api` на `http://localhost:8000` — это делает сам Vite
из `vite.config.js`, отдельный обратный прокси для разработки не нужен.

Для продакшена: `npm run build`, затем раздайте каталог `dist` веб-сервером.
Учтите, что обычная раздача статики без проксирования вернёт 404 на запросах
`/api/*`. Готовую рабочую схему смотрите в `frontend/nginx.conf` — там же
настроены лимит загрузки и таймаут ожидания ответа модели.

---

## Вход администратора

```
логин:    admin
пароль:   admin123
```

После первого входа смените пароль: раздел **Пользователи**.

---

## Модели ИИ

### Облачные (OpenRouter)

Раздел **Модели ИИ** → Добавить: провайдер `openrouter`, `model_id` —
например `openrouter/free` (подбор бесплатных моделей) или конкретная модель.
Ключ вводится в поле «API ключ» либо задаётся переменной `OPENROUTER_API_KEY`
в `.env`.

### Локальные (Ollama)

Ollama уже запускается контейнером `doccheck-ollama`.
Скачать модели:

```bash
docker compose exec ollama ollama pull qwen2.5:7b-instruct   # текст
docker compose exec ollama ollama pull qwen2.5vl:7b          # чтение чертежей
```

Затем добавьте их в разделе **Модели ИИ**: провайдер `ollama`, `model_id` —
`qwen2.5:7b-instruct`.

Для мультимодальной модели включите флажок **vision** — без него проверка
распознавания чертежей будет помечена как не проведена.

---

## Плагины анализа

В системе три плагина. Каждый всегда присутствует в отчёте: либо с замечаниями,
либо со статусом «не проведена» и указанием причины.

| Код | Что делает | Нужна модель |
|---|---|---|
| `CAD_STRUCTURE` | слои, надписи, блоки и атрибуты из DXF/DWG | нет |
| `AI_DOC_TEXT` | анализ текста PDF/DOC по НТД со ссылками на пункты | да (text) |
| `AI_CAD_VISION` | понимание содержимого чертежа по изображению | да (vision) |

Список доступных плагинов смотрите в разделе **Модели ИИ** или через
`GET /api/ai-models/plugins`.

---

## Чертежи DWG

DWG — закрытый бинарный формат, читать его напрямую нельзя. Нужен посредник:

```
DWG → [ODA File Converter] → DXF → [ezdxf] → слои, надписи, блоки
                                ↘ [matplotlib] → PNG → [vision-модель] → описание
```

**ODA File Converter** — сторонняя программа Open Design Alliance, она не
распространяется вместе с DocCheck. Установите её и положите исполняемый файл
в каталог `tools/oda/`:

1. Скачайте: <https://www.opendesign.com/guestfiles/oda_file_converter>
2. Скопируйте `ODAFileConverter` (Linux/macOS) или `ODAFileConverter.exe`
   (Windows) в `tools/oda/`
3. Перезапустите: `docker compose up -d --build backend`

Проверка видимости:

```bash
docker compose exec backend python -c \
  "from services.ai_plugins import cad; print(cad.oda_available())"
```

Если конвертер не установлен, проверки `CAD_STRUCTURE` и `AI_CAD_VISION`
для DWG помечаются как **не проведённые**, с указанием причины. Это намеренно:
лужше честно сообщить, что чертёж не разобран, чем делать вид.

**Альтернатива** — экспортировать чертежи из AutoCAD в DXF или PDF вручную.
Тогда конвертер не нужен.

---

## Настройка под сервер (Proxmox)

Конфигурация: CPU 8 ядер AMD-FX 8120, RAM 24 ГБ, SSD 60 ГБ, GPU нет
(при необходимости — AMD HD 7950 3 ГБ).

- Без GPU система работает полностью, включая локальную модель ИИ —
  медленнее, но корректно.
- Для GPU в `docker-compose.yml` в сервисе `ollama` раскомментируйте секцию
  `devices: /dev/dri` и `group_add: video`. Требуется образ Ollama под ROCm
  и драйвер `amdgpu` на хосте.
- Данные (БД, загрузки, отчёты) — в volume `doccheck-data`, модели Ollama —
  в `ollama-models`. Оба переживают пересборку контейнеров.
- Лимит загрузки файла задаётся переменной `MAX_FILE_SIZE` (МБ, по умолчанию 200).

---

## Импорт и актуальность НТД

База заполняется автоматически при первом запуске: 15 документов
(123-ФЗ, СП 3.13130.2009, СП 6.13130.2021, СП 76.13330.2016,
СП 484.1311500.2020, СП 486.1311500.2020, ПУЭ изд. 7, ГОСТ 21.208-2013,
ГОСТ Р 21.101-2026, ГОСТ 21.210-2014, ГОСТ Р 21.703-2020, ГОСТ 31565-2012,
ГОСТ Р 53246-2025, ГОСТ Р 58238-2018, СП 48.13330.2019) — см. `backend/seed.py`.

Актуальность проверяется перед каждым запуском проверки. Устаревшие документы
помечаются статусом `expired` и попадают в отчёт. Документы добавляются
и редактируются в разделе **НТД**.

---

## Поддерживаемые форматы

`xls`, `xlsx`, `doc`, `docx`, `pdf`, `dwg`, `dxf`, `zip`.

Сканированные PDF без текстового слоя текста для анализа не дают —
плагин `AI_DOC_TEXT` сообщит, что данных недостаточно.

---

## Полезные команды

```bash
docker compose ps                   состояние контейнеров
docker compose logs -f backend      логи бэкенда
docker compose restart backend      перезапуск бэкенда
docker compose down                 остановить
docker compose up -d --build        пересобрать после изменений
```