from dataclasses import dataclass, field

KINDS = {
    "OP_CLS",
    "ZONE_ENTER",
    "ZONE_LEAVE",
    "ROLE",
    "DOC_SHOW",
    "DOC_CHECK",
    "DOC_TO_CLIENT",
    "MONEY_TO_CASHIER",
    "MONEY_TO_CLIENT",
    "BAG_TO_CASHIER",
    "BAG_CHECK",
    "COUNT_MONEY",
    "COUNT_MACHINE",
    "AUTH_CHECK",
    "PILE_MERGE",
    "SORT_PILES",
    "STATE_SAFE_OPEN",
    "STATE_DOOR_OPEN",
    "STATE_LIGHT_OFF",
    "STATE_MONEY_TABLE",
    "STATE_ITEM_TABLE",
    "STATE_KEY_TABLE",
    "LEAVE_STATION",
    "CONTROLLER_PRESENT",
    "THIRD_IN_STAFF",
    "CLIENT_DEPARTS_EMPTY",
}

ZONES = {"staff", "client", "door", "safe", "back"}
ROLES = {"cashier", "client", "controller", "incassator", "third"}


@dataclass
class Prim:
    kind: str
    t: float
    dur: float = 0.0
    conf: float = 1.0
    who: str = ""
    args: dict = field(default_factory=dict)
    frames: tuple = ()

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"unknown primitive kind: {self.kind}")


def load_prims(rows):
    return sorted((Prim(**r) for r in rows), key=lambda p: (p.t, p.dur))
