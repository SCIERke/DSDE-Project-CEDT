import pytest

from processing.osm import clean_osm

NODE = {"type": "node", "id": 1, "lat": 13.76, "lon": 100.53, "tags": {"highway": "bus_stop"}}
WAY = {"type": "way", "id": 2, "center": {"lat": 13.77, "lon": 100.54}, "nodes": [1], "tags": {"highway": "primary"}}


def reasons(*els):
    return [why for _, why in clean_osm({"elements": list(els)}).rejected]


def test_node_and_way_centre_are_used():
    good = clean_osm({"elements": [NODE, WAY]}).good
    assert [(f.osm_type, f.lat, f.lon) for f in good] == [("node", 13.76, 100.53), ("way", 13.77, 100.54)]
    assert good[1].tags == {"highway": "primary"}


def test_bad_elements_rejected_with_reason():
    assert reasons({**NODE, "tags": {}}) == ["no tags"]
    assert reasons({"type": "way", "id": 3, "tags": {"a": "b"}}) == ["missing coords"]
    assert reasons({**NODE, "lat": 0.0, "lon": 0.0}) == ["coords outside Thailand"]
    assert reasons({**NODE, "id": "x"}) == ["bad type/id"]
    assert reasons(NODE, NODE) == ["duplicate element"]


def test_failed_query_raises():
    with pytest.raises(ValueError):
        clean_osm({"elements": [NODE], "remark": "runtime error: Query timed out"})
    with pytest.raises(ValueError):
        clean_osm({})
