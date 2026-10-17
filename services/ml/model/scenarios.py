from dataclasses import dataclass

ID = ("DOC_SHOW", "DOC_CHECK")


@dataclass(frozen=True)
class Step:
    sid: str
    channel: str
    accept: tuple
    label: str = ""
    optional: bool = False
    deadline: float = 90.0


@dataclass(frozen=True)
class Invariant:
    iid: str
    label: str
    state_kind: str
    min_dur: float
    cooldown: float = 20.0


@dataclass(frozen=True)
class Operation:
    op: str
    starts: tuple
    steps: tuple
    leave_station_label: str = "RECV_LEFT_STATION"
    pile_merge_label: str = "CASH_MIXED_WORN"


RECEIVE = Operation(
    op="receive",
    starts=("MONEY_TO_CASHIER",),
    steps=(
        Step("id", "client", ID, "RECV_NO_ID"),
        Step("count", "employee", ("COUNT_MONEY", "COUNT_MACHINE"), "RECV_NO_RECOUNT"),
        Step("auth", "employee", ("AUTH_CHECK",), "RECV_NO_AUTH_CHECK"),
        Step("receipt", "employee", ("DOC_TO_CLIENT",), "", optional=True),
    ),
    leave_station_label="RECV_LEFT_STATION",
    pile_merge_label="RECV_MIXED_FUNDS",
)

ISSUE = Operation(
    op="issue",
    starts=("MONEY_TO_CLIENT",),
    steps=(
        Step("id", "client", ID, "ISSUE_NO_ID"),
        Step("count", "employee", ("COUNT_MONEY", "COUNT_MACHINE"), "ISSUE_NO_RECOUNT"),
        Step("money", "employee", ("MONEY_TO_CLIENT",)),
        Step("client_count", "client", ("COUNT_MONEY", "COUNT_MACHINE"), "ISSUE_NO_CLIENT_RECOUNT"),
        Step("receipt", "employee", ("DOC_TO_CLIENT",), "ISSUE_NO_RECEIPT"),
    ),
    leave_station_label="RECV_LEFT_STATION",
    pile_merge_label="RECV_MIXED_FUNDS",
)

EXCHANGE = Operation(
    op="exchange",
    starts=("MONEY_TO_CASHIER",),
    steps=(
        Step("id", "client", ID, "RECV_NO_ID", optional=True),
        Step("auth", "employee", ("AUTH_CHECK",), "EXCH_NO_AUTH_CHECK"),
        Step("money_out", "employee", ("MONEY_TO_CLIENT",)),
    ),
    pile_merge_label="CASH_MIXED_WORN",
)

CASHOUT = Operation(
    op="cashout",
    starts=("AUTH_CHECK",),
    steps=(
        Step("controller", "employee", ("CONTROLLER_PRESENT",), "CASH_SUSP_NO_ACT"),
        Step("sort", "employee", ("SORT_PILES",), "CASH_MIXED_WORN", optional=True),
    ),
    pile_merge_label="CASH_MIXED_WORN",
)

COUNT = Operation(
    op="count",
    starts=("COUNT_MONEY", "COUNT_MACHINE"),
    steps=(
        Step("controller", "employee", ("CONTROLLER_PRESENT",), "CNT_NO_CONTROLLER"),
        Step("machine", "employee", ("COUNT_MACHINE",), "CNT_NO_EQUIPMENT"),
        Step("sort", "employee", ("SORT_PILES",), "", optional=True),
    ),
    leave_station_label="CNT_UNATTENDED",
    pile_merge_label="CASH_MIXED_WORN",
)

INCASS = Operation(
    op="incass",
    starts=("BAG_TO_CASHIER",),
    steps=(
        Step("bag_check", "employee", ("BAG_CHECK",), "INCASS_BAG_NO_CHECK"),
    ),
)

OPERATIONS = {op.op: op for op in (RECEIVE, ISSUE, EXCHANGE, CASHOUT, COUNT, INCASS)}

GLOBAL_INVARIANTS = (
    Invariant("inv_safe", "ROOM_SAFE_OPEN", "STATE_SAFE_OPEN", 2.5, cooldown=25.0),
    Invariant("inv_door", "ROOM_DOOR_OPEN", "STATE_DOOR_OPEN", 3.0, cooldown=25.0),
    Invariant("inv_light", "ROOM_LOW_LIGHT", "STATE_LIGHT_OFF", 5.0, cooldown=60.0),
    Invariant("inv_item", "ROOM_PERSONAL_ITEMS", "STATE_ITEM_TABLE", 5.0, cooldown=40.0),
    Invariant("inv_key", "ROOM_KEY_ABANDONED", "STATE_KEY_TABLE", 2.0, cooldown=25.0),
    Invariant("inv_third", "ROOM_THIRD_PARTY", "THIRD_IN_STAFF", 3.0, cooldown=30.0),
)

EVENT_RULES = (
    ("CLIENT_DEPARTS_EMPTY", "ANOM_CLIENT_LEFT_EMPTY"),
    ("PILE_MERGE", None),
)

MONEY_AFTER_CLIENT_LEAVE_SEC = 8.0
MONEY_NO_CASHIER_MIN_DUR = 4.0
MONEY_NO_CASHIER_LABEL = "ROOM_MONEY_ON_TABLE"
MONEY_AFTER_LEAVE_LABEL = "RECV_FUNDS_ACCESSIBLE"
