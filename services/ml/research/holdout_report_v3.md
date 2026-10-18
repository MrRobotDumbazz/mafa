# Holdout-отчёт v3 (финал: YOLOv5n + слияния + доступность денег; сценовые сейф/дверь отключены — доказанная неразделимость с чистыми, см. NOTES)

Итог: tune R=0.53/P=0.53/FPR=0.50 | holdout R=0.57/P=0.50/FPR=0.67 | TC 3/7. Сравнение с v1 (R=0.57/P=0.57/FPR=0.50): паритет — эвристический потолок; дальнейший рост только с весами объектов/позы (запрос в NOTES).

Дата: 2026-10-18 06:28 | Split: seed 42, стратифицированный 70/30 по вердикту.
Tune: 29 видео | Holdout: 13 видео. Тюнинг порогов — только на tune.

## Вердикт по видео (recall-приоритет, FAQ 16)

| набор | TP | FP | FN | TN | recall | precision | F1 | FPR |
|---|---|---|---|---|---|---|---|---|
| tune | 8 | 7 | 7 | 7 | 0.53 | 0.53 | 0.53 | 0.50 |
| holdout | 4 | 4 | 3 | 2 | 0.57 | 0.50 | 0.53 | 0.67 |

## Попадание в таймкод (±10 с) среди нарушений с известным t

- tune: 8/15
- holdout: 3/7

## Детали по holdout (тип разметки → предсказанные типы)

| видео | гипотеза разметки | ожидаемый label | t_gt | предсказано |
|---|---|---|---|---|
| X-1 | Вернула сдачу, не посчитав деньги в аппарате | ISSUE_NO_RECOUNT | 22 | — |
| X-13 | Сложить деньги вместе | CASH_MIXED_WORN | 47 | RECV_FUNDS_ACCESSIBLE, ROOM_MONEY_ON_TABLE |
| X-2 | Не Показал удостоверение личности | ISSUE_NO_ID | 10 | — |
| X-24 | Не проверили закрыт ли сейф или нет | ROOM_SAFE_OPEN | 8 | CASH_MIXED_WORN, ROOM_MONEY_ON_TABLE |
| X-30 | Дверь не закрыта | ROOM_DOOR_OPEN | 13 | CASH_MIXED_WORN, RECV_MIXED_FUNDS |
| X-32 | — | — | 5 | CASH_MIXED_WORN |
| X-34 | Ушел человек не получив ничего | ANOM_CLIENT_LEFT_EMPTY | 13 | — |

## Детали по tune

| видео | гипотеза разметки | ожидаемый label | t_gt | предсказано |
|---|---|---|---|---|
| X-11 | Не закрыли кабинет | ROOM_DOOR_OPEN | 18 | CASH_MIXED_WORN |
| X-15 | Свет не включили | ROOM_LOW_LIGHT | 15 | CASH_MIXED_WORN |
| X-17 | Отдал ушел без удостоверение | ISSUE_NO_ID | 7 | RECV_FUNDS_ACCESSIBLE |
| X-18 | Заходит другой человек | ROOM_THIRD_PARTY | 20 | — |
| X-20 | Не закрыли сейф | ROOM_SAFE_OPEN | 5 | — |
| X-22 | Ключ не забрали от сейфа | ROOM_KEY_ABANDONED | 14 | CASH_MIXED_WORN, ROOM_MONEY_ON_TABLE |
| X-26 | Оставили деньги на столе | ROOM_MONEY_ON_TABLE | 9 | CASH_MIXED_WORN, CNT_UNATTENDED, ROOM_MONEY_ON_TABLE |
| X-28 | Не проверили закрыт ли сейф или нет | ROOM_SAFE_OPEN | 7 | CASH_MIXED_WORN |
| X-33 | Дверь не закрыта | ROOM_DOOR_OPEN | 6 | CASH_MIXED_WORN, RECV_MIXED_FUNDS |
| X-38 | Деньги должны быть отложены в недоступное для клиента место | RECV_FUNDS_ACCESSIBLE | 33 | — |
| X-4 | Деньги должны быть отложены в недоступное для клиента место | RECV_FUNDS_ACCESSIBLE | 57 | — |
| X-40 | Лишние вещи на столе | ROOM_PERSONAL_ITEMS | 17 | CASH_MIXED_WORN |
| X-44 | Совместили деньги | CASH_MIXED_WORN | 16 | — |
| X-46 | Деньги должны быть отложены в недоступное для клиента место | RECV_FUNDS_ACCESSIBLE | 11 | — |
| X-47 | — | — | 68 | — |
