"""Overpass payload -> list of OsmFeature. Same stages as processing/traffy.py: cast/validate/dedupe, rejects keep a reason."""
from model.osm import OsmFeature
from processing.common import LAT, LON, Cleaned


def clean_osm(payload: dict) -> Cleaned:
    elements = payload.get("elements")

    if not isinstance(elements, list) or "runtime error" in payload.get("remark", ""):
        raise ValueError("unexpected or failed overpass payload")

    out, seen = Cleaned(), set()
    for e in elements:
        c = e if "lat" in e else (e.get("center") or {})
        key = (e.get("type"), e.get("id"))
        if key[0] not in ("node", "way", "relation") or not isinstance(key[1], int):
            reason = "bad type/id"
        elif not e.get("tags"):
            reason = "no tags"
        elif "lat" not in c or "lon" not in c:
            reason = "missing coords"
        elif not (LON[0] <= c["lon"] <= LON[1] and LAT[0] <= c["lat"] <= LAT[1]):
            reason = "coords outside Thailand"
        elif key in seen:
            reason = "duplicate element"
        else:
            reason = None
        if reason:
            out.rejected.append((e, reason))
        else:
            seen.add(key)
            out.good.append(OsmFeature(key[0], key[1], c["lat"], c["lon"], e["tags"]))
    return out
