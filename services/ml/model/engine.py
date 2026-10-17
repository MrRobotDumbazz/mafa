from dataclasses import dataclass, field

import primitives as P
import scenarios as SC


@dataclass
class Violation:
    label: str
    rule: str
    channel: str
    t_start: float
    t_end: float
    conf: float
    frames: tuple = ()
    note: str = ""

    def as_dict(self):
        return {
            "label": self.label,
            "rule": self.rule,
            "channel": self.channel,
            "t_start": self.t_start,
            "t_end": self.t_end,
            "conf": round(self.conf, 3),
            "frames": list(self.frames),
            "note": self.note,
        }


@dataclass
class EngineConfig:
    op_windows: tuple = ()
    default_window: float = 120.0
    leave_gap: float = 2.0
    max_evidence_frames: int = 3
    enable_steps: bool = True


def _cap(conf, dur, min_dur):
    factor = 1.0 if min_dur <= 0 else min(1.0, dur / (2.0 * min_dur))
    return min(0.95, conf * (0.5 + 0.5 * factor))


def _who_ok(prim, channel):
    if not prim.who:
        return True
    if channel == "client":
        return prim.who.startswith("client")
    if channel == "employee":
        return not prim.who.startswith("client")
    return True


class Engine:
    def __init__(self, config=None):
        self.cfg = config or EngineConfig()

    def run(self, prims):
        prims = sorted(prims, key=lambda p: (p.t, p.dur))
        violations = []
        self._global_state_rules(prims, violations)
        self._global_event_rules(prims, violations)
        self._money_rules(prims, violations)
        for op, t0, t1 in self._windows(prims):
            self._scenario(SC.OPERATIONS[op], prims, t0, t1, violations)
        return sorted(violations, key=lambda v: v.t_start)

    def _windows(self, prims):
        wins = []
        for p in prims:
            if p.kind == "OP_CLS":
                op = p.args.get("op")
                t0, t1 = p.args.get("t0", p.t), p.args.get("t1", p.t + p.dur)
                if op in SC.OPERATIONS:
                    wins.append((op, float(t0), float(t1)))
        return wins

    def _global_state_rules(self, prims, out):
        for inv in SC.GLOBAL_INVARIANTS:
            last_fire = None
            for p in prims:
                if p.kind != inv.state_kind:
                    continue
                if p.dur < inv.min_dur:
                    continue
                if last_fire is not None and p.t < last_fire + inv.cooldown:
                    continue
                last_fire = p.t
                out.append(
                    Violation(
                        label=inv.label,
                        rule=inv.iid,
                        channel="env",
                        t_start=p.t,
                        t_end=p.t + p.dur,
                        conf=_cap(p.conf, p.dur, inv.min_dur),
                        frames=p.frames[: self.cfg.max_evidence_frames],
                    )
                )

    def _global_event_rules(self, prims, out):
        for p in prims:
            if p.kind == "CLIENT_DEPARTS_EMPTY":
                out.append(
                    Violation(
                        label="ANOM_CLIENT_LEFT_EMPTY",
                        rule="ev_client_empty",
                        channel="client",
                        t_start=p.t,
                        t_end=p.t + max(p.dur, 1.0),
                        conf=_cap(p.conf, p.dur, 0.0),
                        frames=p.frames[: self.cfg.max_evidence_frames],
                    )
                )

    def _money_rules(self, prims, out):
        client_leaves = sorted(p.t for p in prims if p.kind == "ZONE_LEAVE" and p.who.startswith("client"))
        leaves_station = [(p.t, p.t + p.dur) for p in prims if p.kind == "LEAVE_STATION"]
        for p in prims:
            if p.kind != "STATE_MONEY_TABLE":
                continue
            seg = (p.t, p.t + p.dur)
            for lv in leaves_station:
                if seg[0] <= lv[0] and lv[1] - seg[0] >= SC.MONEY_NO_CASHIER_MIN_DUR:
                    out.append(
                        Violation(
                            label=SC.MONEY_NO_CASHIER_LABEL,
                            rule="money_no_cashier",
                            channel="env",
                            t_start=lv[0],
                            t_end=min(seg[1], lv[1]),
                            conf=_cap(p.conf, p.dur, SC.MONEY_NO_CASHIER_MIN_DUR),
                            frames=p.frames[: self.cfg.max_evidence_frames],
                            note="money on table while cashier absent",
                        )
                    )
                    break
            else:
                if client_leaves and seg[0] <= client_leaves[-1] <= seg[1] - SC.MONEY_AFTER_CLIENT_LEAVE_SEC:
                    lv = next(t for t in client_leaves if seg[0] <= t <= seg[1] - SC.MONEY_AFTER_CLIENT_LEAVE_SEC)
                    out.append(
                        Violation(
                            label=SC.MONEY_AFTER_LEAVE_LABEL,
                            rule="money_after_leave",
                            channel="employee",
                            t_start=lv,
                            t_end=seg[1],
                            conf=_cap(p.conf, seg[1] - lv, SC.MONEY_AFTER_CLIENT_LEAVE_SEC),
                            frames=p.frames[: self.cfg.max_evidence_frames],
                            note="money not stored after client departed",
                        )
                    )

    def _scenario(self, opdef, prims, t0, t1, out):
        window = [p for p in prims if t0 <= p.t <= t1]
        last_t = t0
        if self.cfg.enable_steps:
            for step in opdef.steps:
                match = None
                for p in window:
                    if p.kind in step.accept and p.t >= last_t - 1e-9 and _who_ok(p, step.channel):
                        match = p
                        break
                if match is not None:
                    last_t = match.t
                    continue
                if step.label and not step.optional:
                    miss_t = min(t1, t0 + step.deadline)
                    out.append(
                        Violation(
                            label=step.label,
                            rule=f"{opdef.op}:{step.sid}:missing",
                            channel=step.channel,
                            t_start=t0,
                            t_end=miss_t,
                            conf=0.7,
                            note=f"required step not observed: {step.sid}",
                        )
                    )
        for p in window:
            if p.kind == "LEAVE_STATION" and p.dur >= self.cfg.leave_gap:
                out.append(
                    Violation(
                        label=opdef.leave_station_label,
                        rule=f"{opdef.op}:leave_station",
                        channel="employee",
                        t_start=p.t,
                        t_end=p.t + p.dur,
                        conf=_cap(p.conf, p.dur, self.cfg.leave_gap),
                        frames=p.frames[: self.cfg.max_evidence_frames],
                    )
                )
            if p.kind == "PILE_MERGE":
                out.append(
                    Violation(
                        label=opdef.pile_merge_label,
                        rule=f"{opdef.op}:pile_merge",
                        channel="employee",
                        t_start=p.t,
                        t_end=p.t + max(p.dur, 1.0),
                        conf=_cap(p.conf, p.dur, 0.0),
                        frames=p.frames[: self.cfg.max_evidence_frames],
                    )
                )


def verdict(violations):
    return "violation" if violations else "no_violation"
