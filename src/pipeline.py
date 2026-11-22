import csv
import io
import time

import requests

from processing.bma import clean_arcgis, clean_intersections, clean_roads, clean_traffic
from processing.cameras import clean_cameras
from processing.osm import clean_osm
from processing.traffy import clean_traffy
from core.db import bronze_sources, get_conn, latest_raw, append_rejects, append_rows, save_raw
from ingest.downloader import DataDownloader
from gold import to_gold
from ingest.sources import CAMERAS_CSV, register_sources
from model.bma import BmaPoint, RoadWidth, TrafficCount
from model.camera import Camera
from model.osm import OsmFeature
from model.traffy import TraffyReport

# source prefix (before ":") -> (cleaner, silver table, model)
_csv = lambda p: list(csv.DictReader(io.StringIO(p)))
CLEANERS = {
    "bma_vendors": (lambda p: clean_arcgis(p, "vendor_zone", "HAWKER_AREA"), "bma_points", BmaPoint),
    "bma_parking": (lambda p: clean_arcgis(p, "paid_parking", "ROAD_NAME"), "bma_points", BmaPoint),
    "bma_intersections": (lambda p: clean_intersections(_csv(p)), "bma_points", BmaPoint),
    "bma_roads": (lambda p: clean_roads(_csv(p)), "roads", RoadWidth),
    "bma_traffic": (lambda p: clean_traffic(_csv(p)), "traffic", TrafficCount),
    "cameras": (lambda p: clean_cameras(list(csv.DictReader(io.StringIO(p)))), "cameras", Camera),
    "overpass": (clean_osm, "osm", OsmFeature),
    "traffy": (lambda p: clean_traffy(list(csv.DictReader(io.StringIO(p)))), "traffy", TraffyReport),
}


def fetch(d: DataDownloader, name: str, tries: int = 3):
    """Overpass is often overloaded (timeouts, 502/504): retry a few times before giving up on a source."""
    for i in range(tries):
        try:
            return d.download(name)
        except requests.RequestException:
            if i == tries - 1:
                raise
            time.sleep(10 * (i + 1))


def to_bronze(month: str, refresh: bool = False) -> None:
    """Download every source for `month` (YYYY-MM) and store the payload untouched in bronze.raw_data.
    Sources already in bronze are skipped (re-running resumes after failures) unless `refresh`."""
    d = DataDownloader()
    register_sources(d, month)
    with get_conn() as conn:
        have = set(bronze_sources(conn))
    for name in d.sources:
        if name in have and not refresh:
            continue
        try:
            save_raw(name, fetch(d, name))
            print("bronze", name)
        except requests.RequestException as e:  # one flaky source shouldn't lose the rest
            print(f"bronze {name}: FAILED, {e}")

    save_raw("cameras", CAMERAS_CSV.read_text(encoding="utf-8"))
    print("bronze cameras")


def clean_source(conn, source: str) -> None:
    clean, table, cls = CLEANERS[source.split(":")[0]]
    bronze_id, payload = latest_raw(conn, source)
    res = clean(payload)
    conn.begin()  # rows + rejects land together or not at all
    try:
        append_rows(conn, table, cls, res.good, source, bronze_id)
        append_rejects(conn, res.rejected, source, bronze_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    print(f"silver {source}: {len(res.good)} good, {len(res.rejected)} rejected")


def to_silver() -> None:
    """Clean the latest bronze payload of each source into typed silver tables (+ silver.rejects)."""
    with get_conn() as conn:
        for source in bronze_sources(conn):
            if source.split(":")[0] not in CLEANERS:
                continue  # no cleaner for this source
            try:
                clean_source(conn, source)
            except (ValueError, TypeError, csv.Error) as e:  # bad payload shape: report, keep going
                print(f"silver {source}: FAILED, {e}")


def run(layer: str, month: str, refresh: bool = False) -> None:
    if layer in ("bronze", "all"):
        to_bronze(month, refresh)
    if layer in ("silver", "all"):
        to_silver()
    if layer in ("gold", "all"):
        to_gold()
