# Финальный подробный отчёт зоны ml (W3) — для P2

Дата: 2026-10-18 (утро). Статус: Этап 2 (п.1–4) выполнен до эвристического потолка; стык с backend проверен. Документ заменяет `REPORT_W3_DETAILED_2026-10-17.md`.

---

## 1. Резюме

1. Построен и **встроен в backend** полный локальный конвейер: `.mov → валидация → детекция (YOLOv5n ONNX) → трекинг (ByteLite) → зоны/роли → стат-объекты → примитивы → rule-engine (K1∨K2∨K3) → события (label + пункт НПА + confidence + JPEG-кадры) → JSON v1 + summary`.
2. Нормативная база: ПП НБРК № 231 (основной), № 120, № 58 (методологический) → **35 label**, маппинг всей разметки.
3. **Финальные метрики (holdout, честные):** recall 0.57, precision 0.50, FPR 0.67, таймкод ±10 с — 3/7. Recall по вердикту на gt-типах «дверь» 3/3, «сейф» 2/3 — но прокси-label'ами.
4. Проведены и **доказаны численно пределы эвристик**: сейф/дверь через «смену сцены» неотличимы от чистых видео (X-21 clean ≡ X-20 violation по сигнатурам региона); свет не вытащить (автоэкспозиция). Дальнейший рост — только веса объектов/позы (запросы §9).

## 2. Хронология версий

| Версия | Стек | holdout R / P / FPR | Комментарий |
|---|---|---|---|
| v0 (classic) | ffmpeg + stdlib, дифф-блобы | 0.71 / 0.56 / 0.67 | базовая линия без пакетов |
| v1 (DNN) | YOLOv5n ONNX + onnxruntime, ByteLite | 0.57 / 0.57 / 0.50 | точнее, строже; пороги v0 не перетюнены |
| v3a (+сейф/дверь наивно) | v1 + сценовые состояния | 1.00 / 0.52 / 1.00 | все нарушения, но и все чистые — FP |
| v3b (+дискриминаторы) | v1 + край кадра/время | 0.20 / 0.43 / 0.29 | передавил — потеряли находки |
| **v3-финал** | v1 + слияния + доступность + FP-ретюн; сценовые выкл. | **0.57 / 0.50 / 0.67** | паритет с v1, новые типы, потолок |

## 3. Архитектура (текущая)

```
run.py (валидация .mov: ffprobe; --backend auto|dnn|classic; авто-.venv)
  └ pipeline/vision.py: ffmpeg rawvideo 270×480@3fps
       ├ detector.py: YOLOv5n v7.0 ONNX (ORT, fp16, letterbox, NMS) — люди + COCO-объекты
       ├ tracker.py: ByteLite (IoU+центроида, скорость) → registry треков
       ├ zones.py: кассир (самый постоянный трек), staff-зона, зона входа (дверь), клиенты
       ├ vision.StaticFast: EMA-фон → персистентные ячейки → стат-объекты,
       │   слияния соседних кластеров (merges), персистентные-к-концу регионы
       └ clips.py: категории service/solo_count/bag_incass/item_in_staff + взаимодействия
  └ emit.py: примитивы (ZONE_*, LEAVE_STATION, THIRD, STATE_*, PILE_MERGE, OP_CLS…)
  └ model/engine.py: OR-семантика, инварианты + сценарии + денежные правила + cooldown
  └ catalog.py: label → (title RU, документ, пункт НПА, verified)
  → JSON по contracts/ml_events.schema.json v1 (+summary), кадры-доказательства JPEG
```

Продуктовые выходы: `run.py` (стык backend), `batch_report.py` (отчёт по загруженным видео: вердикт + расшифровка label + норматив + клипы), `holdout.py` (стратифицированный split seed 42, тюнинг только на tune), `eda.py`.

## 4. Окружение (как решено)

pip заблокирован PEP 668 + TLS-сбои → wheel-файлы качались curl'ом (докачка/ретраи), установлены в `services/ml/.venv`: numpy 2.5.4, opencv-python-headless 5.0, pandas 3.0.6, openpyxl 3.1.5, onnxruntime 1.31.0. Веса: `weights/yolov5n_v7.0.onnx` (3.98 МБ). YOLOX-ассеты GitHub дефектны (obj ≡ 0 при любом входе; проверено на cv2.dnn и ORT) — заменены на YOLOv5n. cv2 5.0 имеет баги нового DNN-движка → инференс через onnxruntime, cv2 только для resize.

## 5. НПА и каталог

35 label (RECV_/ISSUE_/EXCH_/CASH_/CNT_/ROOM_/INCASS_/ANOM_) с пунктами НПА и наблюдаемостью: `research/npa_analysis.md`, `research/violation_hypotheses.yaml`. verified: none → ROOM_DOOR_OPEN, ROOM_LOW_LIGHT, ROOM_THIRD_PARTY (частично), ANOM_*, CNT_STATION_LEFT — нужны тексты Правил № 14 (24.02.2020) и № 230 (29.11.2017). adilet-URL не перепроверены (JS; на сайт не хожу по указанию P2).

## 6. Покрытие gt-типов финальным билдом (все 22 нарушения)

| gt-тип | n | вердикт TP | точный label |
|---|---|---|---|
| ROOM_DOOR_OPEN | 3 | 3 | 0 (прокси: деньги/уходы) |
| ROOM_SAFE_OPEN | 3 | 2 | 0 (прокси) |
| ROOM_MONEY_ON_TABLE | 1 | 1 | 1 |
| ROOM_KEY_ABANDONED | 1 | 1 | 0 |
| ROOM_LOW_LIGHT | 1 | 1 | 0 (прокси) |
| ROOM_PERSONAL_ITEMS | 1 | 1 | 0 |
| CASH_MIXED_WORN | 2 | 1 | 0 |
| RECV_FUNDS_ACCESSIBLE | 3 | 0 | 0 |
| ISSUE_NO_ID | 2 | 1 | 0 |
| ISSUE_NO_RECOUNT | 1 | 0 | 0 |
| ANOM_CLIENT_LEFT_EMPTY | 1 | 0 | 0 |
| ROOM_THIRD_PARTY | 1 | 0 | 0 |
| без гипотезы (X-32/X-47) | 2 | 1 | — |

FP: 11 чистых видео помечены нарушением (источники: прокси-срабатывания денег/уходов на benign-сценах). Таймкод: 3/7 на holdout.

## 7. Ключевые эксперименты v3 (данные, не мнения)

1. **Сейф/дверь = смена сцены**: персистентные-к-концу регионы ловят все 5 gt-видео (X-20 → ROOM_SAFE_OPEN 5.3 с при gt 5) — но у 20/20 чистых регионов те же сигнатуры (X-21 clean: 31 ячейка rect [0.06,0.17,0.5,0.6] ≡ X-20 violation: 29 ячеек). Дискриминаторы (край кадра, «после ухода клиента», размер) режут recall до 0.2. Код сохранён под флагом `scene_states=False`.
2. **Слияние стопок**: активация ячейки рядом с существующей ≥1.5 с → PILE_MERGE → CASH_MIXED_WORN/RECV_MIXED_FUNDS; кластеризация + cooldown 6 с против каскадов.
3. **Money-детект**: поячеечный фильтр staff-зоны (центр ячейки в расширенной зоне, 1–25 ячеек) — устойчив к склейке фона в мега-регионы.
4. **Свет**: X-15 ≈ X-1 по яркости/гистограммам — автоэкспозиция камеры, метки не разделить.

## 8. Интеграция с backend

`cd services/api && FORTE_PIPELINE_CMD="python3 ../ml/run.py" ./selfcheck.sh` → **SELFCHECK PASSED** (health / 401 / полный цикл upload→job→вердикт→кадры / 404 / web-keyless). Схема `ml_events.schema.json` — v1 (optional `summary`, обратно совместимо).

## 9. Запросы к человеку (единственный путь поднять метрики)

1. **ONNX-детектор ключевых объектов** (дверь, сейф, счётный аппарат, купюры/пачки, ключи, удостоверение, пломба): скачать на машине с сетью готовую модель (кандидаты: YOLO-World v2 ONNX, GroundingDINO ONNX, RF-DETR) → положить в `services/ml/weights/` — подключу через существующий интерфейс `detector.py` одним шагом; `scene_states`-правила включатся автоматически с реальными зонами объектов.
2. **Поза**: образ/vEnv с py3.12 (MediaPipe) или RTMPose ONNX → жесты пересчёта/документа/слияния.
3. **Тексты** Правил № 14 и № 230 (верификация 4 label, критерий 4 ТЗ).
4. **W1**: gitignore для `services/ml/run_evidence/`, `services/ml/weights/`.

## 10. Карта файлов зоны

`run.py, batch_report.py, holdout.py, eda.py` · `model/` (формула, движок, планы, selfcheck) · `pipeline/` (labels, frames, motion, states, zones, featurize, detector, tracker, vision, clips, emit, catalog) · `weights/` · `run_evidence/` · `research/` (npa_analysis, violation_hypotheses, eda_videos, holdout_report{,_v1,_v3}, uploads_report_*, REPORT_*) · `NOTES.md` (журнал+блокеры) · `.venv/` · `contracts/ml_events.schema.json` (v1).
