from processing.bma import clean_arcgis, clean_intersections, clean_roads, clean_traffic

LINE = {"features": [{"attributes": {"R": "a"}, "geometry": {"paths": [[[100.5, 13.7], [100.51, 13.71]]]}},
                     {"attributes": {"R": "b"}, "geometry": {"x": 1, "y": 1}},
                     {"attributes": {"R": "c"}}]}


def test_arcgis_lines_become_vertices_and_bad_geometry_is_rejected():
    r = clean_arcgis(LINE, "paid_parking", "R")
    assert [(p.kind, p.name, p.lat, p.lon) for p in r.good] == [("paid_parking", "a", 13.7, 100.5), ("paid_parking", "a", 13.71, 100.51)]
    assert [why for _, why in r.rejected] == ["coords outside Thailand", "no geometry"]


def test_intersections_roads_traffic_reject_with_reason():
    assert [w for _, w in clean_intersections([{"Lat": "x", "Long": "1"}, {"Lat": "1", "Long": "1"}]).rejected] == ["bad value", "coords outside Thailand"]
    roads = clean_roads([{"ชื่อสายทาง": "ถนน ก", "กว้าง (ม.)": "12.5"}, {"ชื่อสายทาง": "ถนน ข", "กว้าง (ม.)": ""},
                         {"ชื่อสายทาง": "ถนน ค", "กว้าง (ม.)": "900"}])
    assert [r.width_m for r in roads.good] == [12.5] and [w for _, w in roads.rejected] == ["missing or bad width", "width out of range"]
    ok = {"Crossroads": "j", "Date": "2025-01-02", "Total_Vol": "10", "Lat": "13.7", "Long": "100.5"}
    t = clean_traffic([ok, {**ok, "Total_Vol": "-1"}, {**ok, "Date": "nope"}])
    assert len(t.good) == 1 and len(t.rejected) == 2
