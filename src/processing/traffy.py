from dataclasses import fields
from datetime import datetime

from processing.common import Cleaned
from model.traffy import TraffyReport

_dt = datetime.fromisoformat
_int = lambda v: int(float(v))

CASTS = {  # field -> string converter; fields not listed stay str
    "timestamp": _dt, "last_activity": _dt, "timestamp_inprogress": _dt, "timestamp_finished": _dt,
    "star": float, "count_reopen": _int, "message_id": _int,
    "duration_minutes_inprogress": _int, "duration_minutes_finished": _int, "duration_minutes_total": _int,
    "problemtype_tag": lambda v: [t.strip() for t in v.strip("{}").split(",") if t.strip()],
}


def cast(row: dict) -> TraffyReport:
    kw = {}
    for f in fields(TraffyReport):
        v = row.get(f.name)
        try:
            kw[f.name] = None if v in (None, "") else CASTS.get(f.name, str)(v)
        except (ValueError, TypeError):
            raise ValueError(f"bad {f.name}: {v!r}") from None
    return TraffyReport(**kw)


def validate(r: TraffyReport) -> str | None:
    if not r.ticket_id:
        return "missing ticket_id"
    if r.timestamp is None:
        return "missing timestamp"
    try:
        ll = r.lon_lat
    except ValueError:
        return "malformed coords"
    if ll is None:
        return "missing coords"

    if r.star is not None and not 0 <= r.star <= 5:
        return "star out of range"
    if any(d is not None and d < 0 for d in (
            r.duration_minutes_inprogress, r.duration_minutes_finished, r.duration_minutes_total)):
        return "negative duration"
    return None


def clean_traffy(rows: list[dict]) -> Cleaned:
    out, seen = Cleaned(), set()
    for row in rows:
        try:
            r = cast(row)
        except ValueError as e:
            out.rejected.append((row, str(e)))
            continue
        reason = validate(r) or ("duplicate ticket_id" if r.ticket_id in seen else None)
        if reason:
            out.rejected.append((row, reason))
        else:
            seen.add(r.ticket_id)
            out.good.append(r)
    return out
