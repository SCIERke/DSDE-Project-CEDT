"""cctv_info.csv rows -> list of Camera. Same stages as processing/traffy.py: cast -> validate, rejects keep a reason."""
from model.camera import Camera
from processing.common import LAT, LON, Cleaned


def clean_cameras(rows: list[dict]) -> Cleaned:
    out, seen = Cleaned(), set()
    for row in rows:
        try:  # Stage 1: cast
            c = Camera(row["camera_id"].strip(), float(row["latitude"]), float(row["longitude"]),
                       row.get("location_en") or None, int(row["image_count"]) if row.get("image_count") else None)
        except (KeyError, ValueError, TypeError, AttributeError):
            out.rejected.append((row, "bad value"))
            continue
        # Stage 2: validate
        if not c.camera_id:
            reason = "missing camera_id"
        elif c.camera_id in seen:
            reason = "duplicate camera_id"
        elif not (LAT[0] <= c.latitude <= LAT[1] and LON[0] <= c.longitude <= LON[1]):
            reason = "coords out of range"
        else:
            reason = None
        if reason:
            out.rejected.append((row, reason))
        else:
            seen.add(c.camera_id)
            out.good.append(c)
    return out
