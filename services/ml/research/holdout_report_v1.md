# Holdout-отчёт v0.2 (perception YOLOv5n+onnxruntime; пороги v0 не перетюнены под детектор)

Дата: 2026-10-17 21:47 | Split: seed 42, стратифицированный 70/30 по вердикту (тот же, что в v0.1).
Tune: 29 видео | Holdout: 13 видео. Тюнинг порогов — только на tune.

## Вердикт по видео (recall-приоритет, FAQ 16)

| набор | TP | FP | FN | TN | recall | precision | F1 | FPR |
|---|---|---|---|---|---|---|---|---|
| tune | 9 | 10 | 6 | 4 | 0.60 | 0.47 | 0.53 | 0.71 |
| holdout | 4 | 3 | 3 | 3 | 0.57 | 0.57 | 0.57 | 0.50 |

## Попадание в таймкод (±10 с) среди нарушений с известным t

- tune: 7/15
- holdout: 3/7

## Детали по holdout (тип разметки → предсказанные типы)

| видео | гипотеза разметки | ожидаемый label | t_gt | предсказано |
|---|---|---|---|---|
| X-1 | Вернула сдачу, не посчитав деньги в аппарате | ISSUE_NO_RECOUNT | 22 | — |
| X-13 | Сложить деньги вместе | CASH_MIXED_WORN | 47 | CNT_UNATTENDED, ROOM_MONEY_ON_TABLE |
| X-2 | Не Показал удостоверение личности | ISSUE_NO_ID | 10 | — |
| X-24 | Не проверили закрыт ли сейф или нет | ROOM_SAFE_OPEN | 8 | ROOM_MONEY_ON_TABLE |
| X-30 | Дверь не закрыта | ROOM_DOOR_OPEN | 13 | CNT_UNATTENDED, ROOM_MONEY_ON_TABLE |
| X-32 | — | — | 5 | CNT_UNATTENDED |
| X-34 | Ушел человек не получив ничего | ANOM_CLIENT_LEFT_EMPTY | 13 | — |

## Детали по tune

| видео | гипотеза разметки | ожидаемый label | t_gt | предсказано |
|---|---|---|---|---|
| X-11 | Не закрыли кабинет | ROOM_DOOR_OPEN | 18 | CNT_UNATTENDED, ROOM_MONEY_ON_TABLE |
| X-15 | Свет не включили | ROOM_LOW_LIGHT | 15 | CNT_UNATTENDED |
| X-17 | Отдал ушел без удостоверение | ISSUE_NO_ID | 7 | — |
| X-18 | Заходит другой человек | ROOM_THIRD_PARTY | 20 | RECV_LEFT_STATION |
| X-20 | Не закрыли сейф | ROOM_SAFE_OPEN | 5 | — |
| X-22 | Ключ не забрали от сейфа | ROOM_KEY_ABANDONED | 14 | CNT_UNATTENDED, ROOM_MONEY_ON_TABLE |
| X-26 | Оставили деньги на столе | ROOM_MONEY_ON_TABLE | 9 | CNT_UNATTENDED, ROOM_MONEY_ON_TABLE |
| X-28 | Не проверили закрыт ли сейф или нет | ROOM_SAFE_OPEN | 7 | ROOM_MONEY_ON_TABLE |
| X-33 | Дверь не закрыта | ROOM_DOOR_OPEN | 6 | — |
| X-38 | Деньги должны быть отложены в недоступное для клиента место | RECV_FUNDS_ACCESSIBLE | 33 | — |
| X-4 | Деньги должны быть отложены в недоступное для клиента место | RECV_FUNDS_ACCESSIBLE | 57 | RECV_LEFT_STATION |
| X-40 | Лишние вещи на столе | ROOM_PERSONAL_ITEMS | 17 | CNT_UNATTENDED |
| X-44 | Совместили деньги | CASH_MIXED_WORN | 16 | — |
| X-46 | Деньги должны быть отложены в недоступное для клиента место | RECV_FUNDS_ACCESSIBLE | 11 | — |
| X-47 | — | — | 68 | RECV_LEFT_STATION |
