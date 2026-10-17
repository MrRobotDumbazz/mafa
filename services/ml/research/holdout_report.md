# Holdout-отчёт v0.1 (perception ffmpeg+stdlib, без весов)

Дата: 2026-10-17 18:46 | Split: seed 42, стратифицированный 70/30 по вердикту.
Tune: 29 видео | Holdout: 13 видео. Тюнинг порогов — только на tune.

## Вердикт по видео (recall-приоритет, FAQ 16)

| набор | TP | FP | FN | TN | recall | precision | F1 | FPR |
|---|---|---|---|---|---|---|---|---|
| tune | 12 | 9 | 3 | 5 | 0.80 | 0.57 | 0.67 | 0.64 |
| holdout | 5 | 4 | 2 | 2 | 0.71 | 0.56 | 0.63 | 0.67 |

## Попадание в таймкод (±10 с) среди нарушений с известным t

- tune: 8/15
- holdout: 4/7

## Детали по holdout (тип разметки → предсказанные типы)

| видео | гипотеза разметки | ожидаемый label | t_gt | предсказано |
|---|---|---|---|---|
| X-1 | Вернула сдачу, не посчитав деньги в аппарате | ISSUE_NO_RECOUNT | 22 | ROOM_THIRD_PARTY |
| X-13 | Сложить деньги вместе | CASH_MIXED_WORN | 47 | RECV_LEFT_STATION, ROOM_MONEY_ON_TABLE |
| X-2 | Не Показал удостоверение личности | ISSUE_NO_ID | 10 | ROOM_THIRD_PARTY |
| X-24 | Не проверили закрыт ли сейф или нет | ROOM_SAFE_OPEN | 8 | — |
| X-30 | Дверь не закрыта | ROOM_DOOR_OPEN | 13 | RECV_LEFT_STATION, ROOM_THIRD_PARTY |
| X-32 | — | — | 5 | — |
| X-34 | Ушел человек не получив ничего | ANOM_CLIENT_LEFT_EMPTY | 13 | ROOM_THIRD_PARTY |

## Детали по tune

| видео | гипотеза разметки | ожидаемый label | t_gt | предсказано |
|---|---|---|---|---|
| X-11 | Не закрыли кабинет | ROOM_DOOR_OPEN | 18 | ROOM_THIRD_PARTY |
| X-15 | Свет не включили | ROOM_LOW_LIGHT | 15 | ROOM_THIRD_PARTY |
| X-17 | Отдал ушел без удостоверение | ISSUE_NO_ID | 7 | — |
| X-18 | Заходит другой человек | ROOM_THIRD_PARTY | 20 | ROOM_THIRD_PARTY |
| X-20 | Не закрыли сейф | ROOM_SAFE_OPEN | 5 | ROOM_THIRD_PARTY |
| X-22 | Ключ не забрали от сейфа | ROOM_KEY_ABANDONED | 14 | — |
| X-26 | Оставили деньги на столе | ROOM_MONEY_ON_TABLE | 9 | ROOM_MONEY_ON_TABLE, ROOM_THIRD_PARTY |
| X-28 | Не проверили закрыт ли сейф или нет | ROOM_SAFE_OPEN | 7 | ROOM_THIRD_PARTY |
| X-33 | Дверь не закрыта | ROOM_DOOR_OPEN | 6 | ROOM_THIRD_PARTY |
| X-38 | Деньги должны быть отложены в недоступное для клиента место | RECV_FUNDS_ACCESSIBLE | 33 | ROOM_THIRD_PARTY |
| X-4 | Деньги должны быть отложены в недоступное для клиента место | RECV_FUNDS_ACCESSIBLE | 57 | RECV_LEFT_STATION, ROOM_MONEY_ON_TABLE, ROOM_THIRD_PARTY |
| X-40 | Лишние вещи на столе | ROOM_PERSONAL_ITEMS | 17 | ROOM_THIRD_PARTY |
| X-44 | Совместили деньги | CASH_MIXED_WORN | 16 | ROOM_THIRD_PARTY |
| X-46 | Деньги должны быть отложены в недоступное для клиента место | RECV_FUNDS_ACCESSIBLE | 11 | — |
| X-47 | — | — | 68 | RECV_LEFT_STATION, ROOM_MONEY_ON_TABLE, ROOM_THIRD_PARTY |

## Интерпретация и ограничения v0 (честно, E8)

- **Что реально работает:** ROOM_MONEY_ON_TABLE / RECV_FUNDS_ACCESSIBLE (стат-объект в зоне кассира, переживший людей) — X-26, X-4, X-13, X-47; ZONE/LEAVE-логика. X-47 (нарушение без гипотезы разметчика) пойман как violation.
- **ROOM_THIRD_PARTY перенакален** (срабатывает на 10+/22 нарушений и на чистых видео): трек-фрагменты при перекрытиях людей неотличимы от третьего человека классическим CV → главный источник FP (FPR 0.64–0.67). Лечится детектором людей (YOLOX/RT-DETR) — интерфейс примитивов готов.
- **Недетектируемо в v0:** ROOM_LOW_LIGHT (авто-экспозиция камеры выравнивает яркость: X-15 ≈ X-1 по метрикам), жестовые типы (ISSUE_NO_RECOUNT, *_NO_ID, CASH_MIXED_WORN, сейф/дверь/ключ/вещи) — нужны поза/объекты/классификатор клипов.
- **Таймкод:** 4/7 на holdout — у THIRD окно широкое (весь трек), у MONEY точный.
- Веса детектора/позы — блокер для v1 (принести файлами, NOTES.md).
