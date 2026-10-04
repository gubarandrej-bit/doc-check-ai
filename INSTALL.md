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
браузер не мешает политика CORS. Порт 8000 наружу открывать не обязательно.