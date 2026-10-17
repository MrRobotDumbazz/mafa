import sys

from primitives import Prim
from engine import Engine, verdict


def case_clean_receive_issue():
    return [
        Prim("ROLE", 0, who="cashier-1", args={"role": "cashier"}),
        Prim("OP_CLS", 10, args={"op": "receive", "t0": 10, "t1": 21}),
        Prim("ZONE_ENTER", 10, who="client-1"),
        Prim("DOC_SHOW", 11, who="client-1", frames=(11.0,)),
        Prim("DOC_CHECK", 12, who="cashier-1"),
        Prim("MONEY_TO_CASHIER", 13, who="client-1"),
        Prim("COUNT_MACHINE", 14, dur=4, who="cashier-1", frames=(14.0, 16.0)),
        Prim("AUTH_CHECK", 15, dur=2, who="cashier-1"),
        Prim("DOC_TO_CLIENT", 19, who="cashier-1"),
        Prim("ZONE_LEAVE", 20, who="client-1"),
        Prim("OP_CLS", 30, args={"op": "issue", "t0": 30, "t1": 41}),
        Prim("ZONE_ENTER", 30, who="client-2"),
        Prim("DOC_SHOW", 31, who="client-2", frames=(31.0,)),
        Prim("COUNT_MONEY", 33, dur=3, who="cashier-1"),
        Prim("MONEY_TO_CLIENT", 36, who="cashier-1"),
        Prim("COUNT_MONEY", 37, dur=2, who="client-2"),
        Prim("DOC_TO_CLIENT", 38, who="cashier-1"),
        Prim("ZONE_LEAVE", 39, who="client-2"),
    ]


def case_dirty_receive():
    return [
        Prim("ROLE", 0, who="cashier-1", args={"role": "cashier"}),
        Prim("OP_CLS", 5, args={"op": "receive", "t0": 5, "t1": 14}),
        Prim("ZONE_ENTER", 5, who="client-1"),
        Prim("MONEY_TO_CASHIER", 6, who="client-1"),
        Prim("LEAVE_STATION", 8, dur=6, who="cashier-1", frames=(8.0, 10.0)),
        Prim("ZONE_LEAVE", 12, who="client-1"),
    ]


def case_room_states():
    return [
        Prim("ROLE", 0, who="cashier-1", args={"role": "cashier"}),
        Prim("STATE_SAFE_OPEN", 2, dur=40, frames=(2.0, 20.0)),
        Prim("STATE_ITEM_TABLE", 5, dur=30),
        Prim("THIRD_IN_STAFF", 10, dur=8, who="third-1", frames=(10.0,)),
        Prim("STATE_KEY_TABLE", 15, dur=6),
        Prim("STATE_DOOR_OPEN", 25, dur=20),
        Prim("STATE_LIGHT_OFF", 50, dur=30),
        Prim("CLIENT_DEPARTS_EMPTY", 70, dur=2, who="client-3", frames=(70.0,)),
    ]


def case_dirty_count():
    return [
        Prim("ROLE", 0, who="cashier-1", args={"role": "cashier"}),
        Prim("OP_CLS", 0, args={"op": "count", "t0": 0, "t1": 60}),
        Prim("COUNT_MONEY", 5, dur=40, who="cashier-1", args={"tool": "manual"}),
        Prim("LEAVE_STATION", 20, dur=10, who="cashier-1"),
        Prim("PILE_MERGE", 30, dur=3, frames=(30.0,)),
    ]


def case_money_after_leave():
    return [
        Prim("ROLE", 0, who="cashier-1", args={"role": "cashier"}),
        Prim("OP_CLS", 5, args={"op": "receive", "t0": 5, "t1": 15}),
        Prim("ZONE_ENTER", 5, who="client-1"),
        Prim("DOC_SHOW", 6, who="client-1"),
        Prim("MONEY_TO_CASHIER", 7, who="client-1"),
        Prim("COUNT_MACHINE", 8, dur=4, who="cashier-1"),
        Prim("AUTH_CHECK", 9, dur=2, who="cashier-1"),
        Prim("ZONE_LEAVE", 12, who="client-1"),
        Prim("STATE_MONEY_TABLE", 6, dur=44, frames=(12.0, 20.0)),
    ]


CASES = [
    ("clean_receive_issue", case_clean_receive_issue, set()),
    (
        "dirty_receive",
        case_dirty_receive,
        {"RECV_NO_ID", "RECV_NO_RECOUNT", "RECV_NO_AUTH_CHECK", "RECV_LEFT_STATION"},
    ),
    (
        "room_states",
        case_room_states,
        {"ROOM_SAFE_OPEN", "ROOM_PERSONAL_ITEMS", "ROOM_THIRD_PARTY", "ROOM_KEY_ABANDONED", "ROOM_DOOR_OPEN", "ROOM_LOW_LIGHT", "ANOM_CLIENT_LEFT_EMPTY"},
    ),
    (
        "dirty_count",
        case_dirty_count,
        {"CNT_NO_CONTROLLER", "CNT_NO_EQUIPMENT", "CNT_UNATTENDED", "CASH_MIXED_WORN"},
    ),
    (
        "money_after_leave",
        case_money_after_leave,
        {"RECV_FUNDS_ACCESSIBLE"},
    ),
]


def main():
    engine = Engine()
    ok = True
    for name, factory, expected in CASES:
        got = {v.label for v in engine.run(factory())}
        status = "PASS" if got == expected else "FAIL"
        if got != expected:
            ok = False
        print(f"[{status}] {name}: expected={sorted(expected)} got={sorted(got)}")
        for v in engine.run(factory()):
            print(f"    {v.as_dict()}")
    print("verdict(clean) =", verdict(engine.run(case_clean_receive_issue())))
    print("verdict(dirty_count) =", verdict(engine.run(case_dirty_count())))
    if not ok:
        sys.exit(1)
    print("ALL PASS")


if __name__ == "__main__":
    main()
