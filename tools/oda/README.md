# ODA File Converter — куда положить конвертер

Этот каталог монтируется в контейнер бэкенда как `/opt/ода` (только чтение).

Сам ODA File Converter здесь **не хранится**: это сторонняя программа
Open Design Alliance, у неё собственные лицензионные условия, поэтому
в репозиторий она положить не может.

## Что сделать

1. Скачайте ODA File Converter с официальной страницы:
   https://www.opendesign.com/guestfiles/oda_file_converter
   (регистрация бесплатная, версии для Linux/Windows/macOS)

2. Распакуйте и скопируйте **исполняемый файл** `ODAFileConverter`
   (на Windows — `ODAFileConverter.exe`) в этот каталог:

   ```
   tools/oda/ODAFileConverter
   ```

3. Перезапустите сервисы:

   ```bash
   docker compose up -d --build backend
   ```

4. Проверьте, что конвертер виден:

   ```bash
   docker compose exec backend python -c \
     "from services.ai_plugins import cad; print(cad.oda_available())"
   ```

Ожидаемый ответ: `(True, '/opt/oda/ODAFileConverter')`.

## Если конвертер не установлен

Система работает, но проверки `CAD_STRUCTURE` и `AI_CAD_VISION`
для файлов DWG будут помечены как **не проведённые**, с указанием причины.
Это сделано намеренно: лучше честно сказать, что проверка не выполнена,
чем делать вид, что чертёж был разобран.

Альтернатива — экспортировать чертежи из AutoCAD в **DXF** или **PDF**
вручную. Тогда конвертер не нужен вовсе.