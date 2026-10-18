# forte-vision — AI-сервис анализа кассовой дисциплины (Datathon 26, ForteBank)

Полностью локальный сервис: загружает .mov → детектирует признаки нарушений кассовой дисциплины → вердикт, таймкоды, кадры-доказательства, ссылка на нормативный акт РК. Веб-интерфейс + API для жюри (`X-API-Key`). Облачные AI/API не используются (раздел 7 ТЗ).

## Быстрый старт (один процесс — сайт + API + ML)

```bash
# 1) перенести в `services/ml/`: weights/ (4 файла ONNX, ~165 МБ) и .venv/ (numpy, opencv, onnxruntime) — вне git
# 2) запуск:
FORTE_API_KEY=<ключ жюри> services/api/deploy.sh        # порт 8000 (FORTE_PORT)
```

- Сайт: `http://<host>:8000/` — загрузка видео, статус, вердикт, события с кадрами и НПА. Ключ не нужен.
- API жюри (раздел 10 ТЗ): только с заголовком `X-API-Key`.

```bash
curl -X POST http://<host>:8000/api/v1/analyze -H "X-API-Key: <ключ>" -F "file=@video_017.mov"
# → {"job_id": "...", "status": "processing"}
curl http://<host>:8000/api/v1/jobs/<job_id> -H "X-API-Key: <ключ>"
# → status: done; verdict: no_violation|violation; violations[]: type, timecode_sec,
#   description, evidence_frames[{timestamp_sec, image_base64}], normative{document, clause}
```

Без `weights/`/`.venv` пайплайн автоматически деградирует до classic-режима (stdlib+ffmpeg) — сервис остаётся работоспособным.

## Архитектура

```
frontend (services/web, Vite+React, dist/ раздаётся backend'ом)
   └── /web/api/v1/* (без ключа, маршрут сайта)      /api/v1/* (жюри, X-API-Key)
        backend (services/api, чистый stdlib: http.server, очередь, 5-мин лимит, ffmpeg-кадры)
        └── FORTE_PIPELINE_CMD → services/ml/run.py (таймаут 280 с, адаптивный бюджет)
             ffmpeg → YOLOv5n (люди) → ByteLite-трекинг → зоны/роли
             → OWLv2 open-vocab (дверь/сейф/купюры/ключи/удостоверение)
             → RTMPose (запястья: пересчёт/передача) → стат-объекты (EMA-фон)
             → примитивы → rule-engine (K1∨K2∨K3) → события + каталог НПА → JSON
```

Контракты: `contracts/api.openapi.yaml` (владелец backend), `contracts/ml_events.schema.json` v1, `contracts/violation_catalog.yaml` (владелец ml; в ответы идут только `verified: true`).

## Типы нарушений (детектируются; НПА — ПП НБРК № 231 от 29.11.2019)

RECV_LEFT_STATION (п. 22) · RECV_FUNDS_ACCESSIBLE / ROOM_MONEY_ON_TABLE (п. 20 ч.2) · CNT_UNATTENDED (п. 20 ч.2, п. 22) · CNT_NO_CONTROLLER (п. 42) · CASH_MIXED_WORN (п. 43, 45) · RECV_NO_ID (п. 19-1) · ROOM_PERSONAL_ITEMS (п. 12) · ROOM_SAFE_OPEN (п. 20 ч.2, 76–78). Полный каталог гипотез (35 типов с пунктами): `services/ml/research/violation_hypotheses.yaml`, `services/ml/research/npa_analysis.md`.

## Метрики (holdout 13 видео, split seed 42, тюнинг только на tune)

| версия | recall | precision | комментарий |
|---|---|---|---|
| v4 (финал) | **1.00** | 0.54 | пропуск нарушений = 0 (FAQ 16); FPR высокий — осознанный trade-off |
| v1 (YOLOv5n) | 0.57 | 0.57 | без open-vocab весов |

Тайминг: худший случай (142-с видео) — 173 с < лимита 300 с.

## Ограничения (честно)

1. Precision 0.54: чистые видео могут помечаться violation (recall-приоритет по FAQ 16; главный источник FP — правило RECV_NO_ID: удостоверение сверху не видно).
2. Сейф/дверь детектируются через объектные детекции OWLv2, свет — не детектируется (автоэкспозиция доказана численно).
3. Обучено/проверено на одном ракурсе (вид сверху); тестовое видео жюри может быть под другим углом (критерий 5).
4. weights/ и .venv/ не в git — перенос при деплое файлами.
5. Результат — подсказка для проверки человеком, не юридическое заключение (раздел 7 ТЗ).

## Команда

| Зона | Человек | ИИ-агент |
|---|---|---|
| backend + координация | **Abay Mukhametali** (P1) | W1 (opencode/GLM) |
| ML-ядро | **Maxat Kenbayev** (P2) | W3 |
| фронтенд | **Fatima Zhulmanova** (P3) | W2 (Claude Code) |
| тестирование | **Almaz Baimakhan** (P4) | W4 (Codex) |

4 человека + 4 ИИ-агента разных вендоров в одном репо. Управление: ZTACP (`docs/ztacp-pattern.md`), план: `PLAN.md`.
