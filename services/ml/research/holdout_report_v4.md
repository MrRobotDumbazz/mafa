# Holdout-отчёт v4 (OWLv2 open-vocab + RTMPose-позы + omission-правила)

Итог: **holdout recall 1.00 (FN=0), precision 0.54, FPR 1.00; таймкод 5/7** | tune recall 0.93. Впервые выполнен FAQ 16 (пропуск недопустим). Прецизионность — задача тюнинга порогов (RECV_NO_ID окно, merge-чувствительность), задокументировано в NOTES.

Дата: 2026-10-18 07:53 | Split: seed 42, стратифицированный 70/30 по вердикту.
Tune: 29 видео | Holdout: 13 видео. Тюнинг порогов — только на tune.

## Вердикт по видео (recall-приоритет, FAQ 16)

| набор | TP | FP | FN | TN | recall | precision | F1 | FPR |
|---|---|---|---|---|---|---|---|---|
| tune | 14 | 12 | 1 | 2 | 0.93 | 0.54 | 0.68 | 0.86 |
| holdout | 7 | 6 | 0 | 0 | 1.00 | 0.54 | 0.70 | 1.00 |

## Попадание в таймкод (±10 с) среди нарушений с известным t

- tune: 10/15
- holdout: 5/7

## Детали по holdout (тип разметки → предсказанные типы)

| видео | гипотеза разметки | ожидаемый label | t_gt | предсказано |
|---|---|---|---|---|
| X-1 | Вернула сдачу, не посчитав деньги в аппарате | ISSUE_NO_RECOUNT | 22 | RECV_NO_ID |
| X-13 | Сложить деньги вместе | CASH_MIXED_WORN | 47 | RECV_FUNDS_ACCESSIBLE, RECV_NO_ID, ROOM_DOOR_OPEN, ROOM_MONEY_ON_TABLE |
| X-2 | Не Показал удостоверение личности | ISSUE_NO_ID | 10 | RECV_NO_ID |
| X-24 | Не проверили закрыт ли сейф или нет | ROOM_SAFE_OPEN | 8 | CASH_MIXED_WORN, ROOM_MONEY_ON_TABLE |
| X-30 | Дверь не закрыта | ROOM_DOOR_OPEN | 13 | CASH_MIXED_WORN, RECV_MIXED_FUNDS, RECV_NO_ID |
| X-32 | — | — | 5 | CASH_MIXED_WORN |
| X-34 | Ушел человек не получив ничего | ANOM_CLIENT_LEFT_EMPTY | 13 | RECV_NO_ID |

## Детали по tune

| видео | гипотеза разметки | ожидаемый label | t_gt | предсказано |
|---|---|---|---|---|
| X-11 | Не закрыли кабинет | ROOM_DOOR_OPEN | 18 | CASH_MIXED_WORN |
| X-15 | Свет не включили | ROOM_LOW_LIGHT | 15 | CASH_MIXED_WORN, RECV_NO_ID |
| X-17 | Отдал ушел без удостоверение | ISSUE_NO_ID | 7 | RECV_FUNDS_ACCESSIBLE, RECV_NO_ID |
| X-18 | Заходит другой человек | ROOM_THIRD_PARTY | 20 | RECV_NO_ID |
| X-20 | Не закрыли сейф | ROOM_SAFE_OPEN | 5 | ROOM_DOOR_OPEN |
| X-22 | Ключ не забрали от сейфа | ROOM_KEY_ABANDONED | 14 | CASH_MIXED_WORN, ROOM_MONEY_ON_TABLE |
| X-26 | Оставили деньги на столе | ROOM_MONEY_ON_TABLE | 9 | CASH_MIXED_WORN, CNT_UNATTENDED, ROOM_DOOR_OPEN, ROOM_MONEY_ON_TABLE |
| X-28 | Не проверили закрыт ли сейф или нет | ROOM_SAFE_OPEN | 7 | CASH_MIXED_WORN, ROOM_DOOR_OPEN |
| X-33 | Дверь не закрыта | ROOM_DOOR_OPEN | 6 | CASH_MIXED_WORN, RECV_MIXED_FUNDS, RECV_NO_ID, ROOM_DOOR_OPEN |
| X-38 | Деньги должны быть отложены в недоступное для клиента место | RECV_FUNDS_ACCESSIBLE | 33 | RECV_NO_ID, ROOM_DOOR_OPEN |
| X-4 | Деньги должны быть отложены в недоступное для клиента место | RECV_FUNDS_ACCESSIBLE | 57 | RECV_NO_ID |
| X-40 | Лишние вещи на столе | ROOM_PERSONAL_ITEMS | 17 | CASH_MIXED_WORN, ROOM_DOOR_OPEN |
| X-44 | Совместили деньги | CASH_MIXED_WORN | 16 | — |
| X-46 | Деньги должны быть отложены в недоступное для клиента место | RECV_FUNDS_ACCESSIBLE | 11 | ROOM_DOOR_OPEN |
| X-47 | — | — | 68 | RECV_NO_ID |
