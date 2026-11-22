"""BMA open data -> BmaPoint / RoadWidth / TrafficCount. Same stages as processing/traffy.py: cast -> validate, rejects keep a reason."""
import json
from datetime import datetime

from model.bma import BmaPoint, RoadWidth, TrafficCount
from processing.common import LAT, LON, Cleaned


def _in_thailand(lat: float, lon: float) -> bool:
    return LAT[0] <= lat <= LAT[1] and LON[0] <= lon <= LON[1]


def clean_arcgis(payload: dict | str, kind: str, name_field: str) -> Cleaned:
    """ArcGIS FeatureServer JSON. Points give one BmaPoint, polylines one per vertex (ponytail: vertex distance, not line distance)."""
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload.get("features"), list):
        raise ValueError("unexpected arcgis payload")
    out = Cleaned()
    for f in payload["features"]:
        g, name = f.get("geometry") or {}, (f.get("attributes") or {}).get(name_field)
        pts = [(g["x"], g["y"])] if "x" in g else [(x, y) for path in g.get("paths", []) for x, y in path]
        if not pts:
            out.rejected.append((f.get("attributes", {}), "no geometry"))
        elif not all(_in_thailand(y, x) for x, y in pts):
            out.rejected.append((f.get("attributes", {}), "coords outside Thailand"))
        else:
            out.good += [BmaPoint(kind, y, x, name) for x, y in pts]
    return out


def clean_intersections(rows: list[dict]) -> Cleaned:
    out = Cleaned()
    for r in rows:
        try:
            p = BmaPoint("intersection", float(r["Lat"]), float(r["Long"]), r.get("n_intesec") or None)
        except (KeyError, ValueError, TypeError):
            out.rejected.append((r, "bad value"))
            continue
        if _in_thailand(p.lat, p.lon):
            out.good.append(p)
        else:
            out.rejected.append((r, "coords outside Thailand"))
    return out


def clean_roads(rows: list[dict]) -> Cleaned:
    out = Cleaned()
    for r in rows:
        try:
            w = RoadWidth(r["ชื่อสายทาง"].strip(), float(r["กว้าง (ม.)"]), r.get("จาก") or None, r.get("ถึง") or None,
                          float(r["ยาว (กม.)"]) if r.get("ยาว (กม.)") else None, r.get("พื้นที่เขต") or None)
        except (KeyError, ValueError, TypeError, AttributeError):
            out.rejected.append((r, "missing or bad width"))  # ~1/3 of the register has no width
            continue
        if w.name and 0 < w.width_m < 100:
            out.good.append(w)
        else:
            out.rejected.append((r, "width out of range"))
    return out


def clean_traffic(rows: list[dict]) -> Cleaned:
    out = Cleaned()
    for r in rows:
        try:
            t = TrafficCount(r["Crossroads"], r.get("Road") or None, datetime.fromisoformat(r["Date"]),
                             int(float(r["Total_Vol"])), float(r["Lat"]), float(r["Long"]))
        except (KeyError, ValueError, TypeError):
            out.rejected.append((r, "bad value"))
            continue
        if t.total_vol >= 0 and _in_thailand(t.lat, t.lon):
            out.good.append(t)
        else:
            out.rejected.append((r, "negative volume or coords outside Thailand"))
    return out
