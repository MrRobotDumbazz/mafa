# forte-vision API (зона backend, W1)

Сервис-оболочка по контракту `contracts/api.openapi.yaml`: приём .mov, очередь заданий, `X-API-Key`, кадры-доказательства (ffmpeg → JPEG base64), вердикт-JSON. **Внешних Python-зависимостей нет** — только stdlib (окружение без интернета; переносимость по разделу 7 ТЗ). Пайплайн — мок (контракт `contracts/ml_events.schema.json`); реальный подключит зона ml на этапе интеграции.

Требования: Python ≥ 3.10, ffmpeg/ffprobe в PATH.

## Запуск

```bash
cd services/api
export FORTE_API_KEY=<ключ>
python3 -m app.main               # порт 8000; или FORTE_PORT=8080
```

## Переменные окружения

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `FORTE_API_KEY` / `FORTE_API_KEYS` | — | ключ(и) жюри, через запятую; без них API отдаёт 503 |
| `FORTE_PORT` | 8000 | порт слушателя |
| `FORTE_STORAGE_DIR` | `services/api/.storage` | каталог загрузок и кадров |
| `FORTE_MAX_UPLOAD_MB` | 200 | лимит размера файла |
| `FORTE_JOB_TIMEOUT_SEC` | 300 | лимит обработки одного видео (раздел 10 ТЗ) |

## Самопроверка

```bash
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/api/v1/analyze \
     -H "X-API-Key: $FORTE_API_KEY" -F "file=@datasets/open/videos/X-1.mov"
curl -s http://127.0.0.1:8000/api/v1/jobs/<job_id> -H "X-API-Key: $FORTE_API_KEY"
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8000/api/v1/analyze -F "file=@x.mov"   # 401
```
