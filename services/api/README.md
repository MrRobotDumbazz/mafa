# forte-vision API (зона backend, W1)

Сервис-оболочка по контракту `contracts/api.openapi.yaml`: приём .mov, очередь заданий, `X-API-Key`, кадры-доказательства (ffmpeg → JPEG base64), вердикт-JSON. **Внешних Python-зависимостей нет** — только stdlib (окружение без интернета; переносимость по разделу 7 ТЗ).

Требования: Python ≥ 3.10, ffmpeg/ffprobe в PATH.

## Запуск

```bash
cd services/api
export FORTE_API_KEY=<ключ>
python3 -m app.main               # порт 8000; или FORTE_PORT=8080
```

## Подключение реального ML-пайплайна (интеграция с зоной ml)

Пока `FORTE_PIPELINE_CMD` пуст — работает мок. При установке переменной backend вызывает внешнюю команду:

```
FORTE_PIPELINE_CMD="python3 ../ml/run.py"
```

Интерфейс (потребительская сторона контракта `contracts/ml_events.schema.json`):
- аргумент argv[1] — путь к загруженному .mov;
- stdout — JSON по схеме: `{video_id, pipeline_version, events: [{type, timecode_sec, description, evidence: [{timestamp_sec, frame}], ...}]}`;
- `frame` — base64 JPEG **или** путь к JPEG-файлу (backend сам закодирует);
- `events: []` (пустой список) легитимен → вердикт `no_violation` (раздел 4 п.3 ТЗ); отсутствие ключа `events` — ошибка;
- таймаут 280 с (< лимита задания 300 с).

## Самопроверка

```bash
services/api/selfcheck.sh                 # поднимет сервер на :8123 и прогонит батарею
services/api/selfcheck.sh путь/к/видео.mov
```

Проверяет: /health, 401 без ключа, полный цикл analyze → done (вердикт, события, кадры > 1 КБ base64), 404 на неизвестный job.

## Docker (НЕ ПРОВЕРЕНО: docker-демон и сеть недоступны в среде разработки — E8)

```bash
cd services/api
FORTE_API_KEY=<ключ> docker compose up -d --build
```

## Переменные окружения

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `FORTE_API_KEY` / `FORTE_API_KEYS` | — | ключ(и) жюри, через запятую; без них API отдаёт 503 |
| `FORTE_PIPELINE_CMD` | `python3 ../ml/run.py` — реальный ML зоны ml (мок удалён 2026-10-18; переопределяется при необходимости) | команда пайплайна (см. выше) |
| `FORTE_STATIC_DIR` | пусто (выкл.) | каталог `dist/` фронтенда: backend раздаёт сайт (`/`, ассеты, SPA-fallback) |
| `FORTE_WEB_KEYLESS` | 1 | `/web/api/v1/*` — маршрут сайта без ключа; `/api/v1/*` (жюри) **всегда** строго с `X-API-Key` (раздел 10 ТЗ) |
| `FORTE_VIOLATION_CATALOG` | `contracts/violation_catalog.yaml` | каталог нормативов: пункты с `verified: true` подмешиваются в `violation.normative` по `type` |
| `FORTE_PORT` | 8000 | порт слушателя |
| `FORTE_STORAGE_DIR` | `services/api/.storage` | каталог загрузок и кадров |
| `FORTE_MAX_UPLOAD_MB` | 200 | лимит размера файла |
| `FORTE_JOB_TIMEOUT_SEC` | 300 | лимит обработки одного видео (раздел 10 ТЗ) |

## Сайт + API жюри в одном процессе (деплой)

```bash
# на машине с сетью: сборка фронта (реальный режим = мимо моков, через /web)
cd services/web && VITE_USE_MOCK=false VITE_API_URL=/web npm ci && npm run build
# запуск (один процесс отдаёт и сайт, и API):
cd ../api
export FORTE_API_KEY=<ключ жюри> FORTE_STATIC_DIR=../web/dist
python3 -m app.main
```

- Сайт: `http://host:8000/` — ключ не нужен (сам ходит через `/web/api/v1/*`).
- Жюри: `/api/v1/analyze`, `/api/v1/jobs/{id}` — только с заголовком `X-API-Key`.

## curl-примеры

```bash
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/api/v1/analyze \
     -H "X-API-Key: $FORTE_API_KEY" -F "file=@../../datasets/open/videos/X-1.mov"
curl -s http://127.0.0.1:8000/api/v1/jobs/<job_id> -H "X-API-Key: $FORTE_API_KEY"
```
