import json

from core.db import get_conn, save_raw, sql_type
from dataclasses import fields

from model.feature import FeatureRow
from model.osm import OsmFeature
from model.traffy import TraffyReport
from pipeline import clean_source, to_silver


def test_sql_types_from_annotations():
    t = {f: sql_type(a) for f, a in TraffyReport.__annotations__.items()}
    assert (t["ticket_id"], t["star"], t["count_reopen"], t["timestamp"], t["problemtype_tag"]) == (
        "VARCHAR", "DOUBLE", "BIGINT", "TIMESTAMP", "VARCHAR[]")
    assert sql_type(OsmFeature.__annotations__["tags"]) == "JSON"


OSM = {"elements": [{"type": "node", "id": 1, "lat": 13.76, "lon": 100.53, "tags": {"highway": "bus_stop"}}]}
CAMERAS = ("camera_id,location_en,latitude,longitude,image_count\n"
           "1,A,13.7600,100.5300,5\n2,B,13.9000,100.7000,6\n3,C,99,100.5,7\n")


def test_silver_is_idempotent_and_keeps_rejects():
    save_raw("cameras", CAMERAS)
    with get_conn() as conn:
        for _ in range(2):  # second run must replace, not duplicate
            clean_source(conn, "cameras")
        assert conn.execute("SELECT count(*) FROM silver.cameras").fetchone()[0] == 2
        assert conn.execute("SELECT reason FROM silver.rejects").fetchall() == [("coords out of range",)]
        bronze_id = conn.execute("SELECT id FROM bronze.raw_data").fetchone()[0]
        assert conn.execute("SELECT DISTINCT bronze_id FROM silver.cameras").fetchall() == [(bronze_id,)]  # lineage


def test_to_silver_skips_unknown_sources_and_survives_bad_payload():
    save_raw("holidays", {"2025-01-01": "New Year"})  # no cleaner -> skipped
    save_raw("overpass:bad", {"error": True})          # wrong shape -> FAILED, others continue
    save_raw("overpass:cam", OSM)
    to_silver()
    with get_conn() as conn:
        assert json.loads(conn.execute("SELECT tags FROM silver.osm").fetchone()[0]) == {"highway": "bus_stop"}


def test_silver_on_empty_lake_does_nothing():
    to_silver()  # no bronze yet: must not crash


def test_gold_one_row_per_camera_with_osm_and_bma_features():
    from gold import to_gold
    save_raw("cameras", CAMERAS)
    save_raw("overpass:cam1", {"elements": [
        {"type": "way", "id": 1, "center": {"lat": 13.76, "lon": 100.53},
         "tags": {"highway": "primary", "name": "ถนนกรุงเกษม", "lanes": "4", "maxspeed": "60", "oneway": "yes"}},
        {"type": "node", "id": 2, "lat": 13.76, "lon": 100.53, "tags": {"highway": "traffic_signals"}},
        {"type": "node", "id": 3, "lat": 13.76, "lon": 100.53, "tags": {"highway": "bus_stop"}}]})
    save_raw("bma_roads", "ชื่อสายทาง,จาก,ถึง,กว้าง (ม.),ยาว (กม.),พื้นที่เขต\n"
                          "ถนนกรุงเกษม,a,b,21.00,0.4,x\nถนนกรุงเกษม,b,c,17.00,0.5,x\nถนนอื่น,a,b,,0.5,x\n")
    save_raw("bma_intersections", "no,n_code,n_intesec,Lat,Long\n1,1,test,13.761,100.53\n")
    save_raw("bma_vendors", {"features": [{"attributes": {"HAWKER_AREA": "v"}, "geometry": {"x": 100.53, "y": 13.7609}}]})
    save_raw("bma_parking", {"features": [{"attributes": {"ROAD_NAME": "p"}, "geometry": {"paths": [[[100.5, 13.7], [100.531, 13.76]]]}}]})
    save_raw("bma_traffic", "Crossroads,Road,Date,Total_Vol,Lat,Long\nj,r,2025-01-02,100,13.76,100.5301\nj,r,2025-01-03,300,13.76,100.5301\n")
    to_silver()
    to_gold()
    with get_conn() as conn:
        cols = [(c[0], c[1]) for c in conn.execute("DESCRIBE gold.features").fetchall()]
        rows = {r[0]: dict(zip([c[0] for c in cols], r)) for r in conn.execute("SELECT * FROM gold.features").fetchall()}
    assert cols == [(f.name, sql_type(f.type)) for f in fields(FeatureRow)]  # gold matches its contract
    assert set(rows) == {"1", "2"}  # camera 3 was rejected in silver
    c1, c2 = rows["1"], rows["2"]
    assert (c1["n_roads"], c1["n_bus_stops"], c1["n_traffic_signals"], c1["n_oneway"], c1["max_lanes"], c1["max_speed_kmh"]) == (1, 1, 1, 1, 4, 60)
    assert c1["road_width_m"] == 19.0  # mean of that road's two registered segments
    assert 100 < c1["dist_intersection_m"] < 125 and 90 < c1["dist_vendor_zone_m"] < 110 and 100 < c1["dist_paid_parking_m"] < 115
    assert c1["traffic_vol"] == 200 and c1["dist_traffic_site_m"] < 15
    assert c2["n_roads"] is None and c2["road_width_m"] is None  # no OSM download for camera 2: unknown, not 0
    assert c2["dist_intersection_m"] > 10_000  # distances still exist: they only need the camera's coordinates
