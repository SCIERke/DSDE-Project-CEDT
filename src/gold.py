"""gold.features: one row per camera, the table to join image detections onto (by camera_id).

silver.cameras + static context around each camera: OSM counts/attributes (silver.osm), BMA road width,
distances to BMA intersections / vendor zones / paid-parking streets, nearest traffic-survey site.
Only the latest bronze load of each source is used, so re-downloading never double-counts.
NULL = unknown (source missing or no match), never 0.
"""
from core.db import ensure_table, get_conn
from model.bma import BmaPoint, RoadWidth, TrafficCount
from model.camera import Camera
from model.osm import OsmFeature


def haversine_m(lat1: str, lon1: str, lat2: str, lon2: str) -> str:
    """SQL expression: metres between two lat/lon columns."""
    return (f"2 * 6371000 * asin(sqrt(pow(sin(radians({lat2} - {lat1}) / 2), 2) "
            f"+ cos(radians({lat1})) * cos(radians({lat2})) * pow(sin(radians({lon2} - {lon1}) / 2), 2)))")


def tag(key: str) -> str:
    return f"json_extract_string(tags, '$.{key}')"


LATEST = "bronze_id IN (SELECT id FROM latest)"

SQL = f"""
CREATE OR REPLACE TABLE gold.features AS
WITH latest AS (SELECT arg_max(id, fetched_at) AS id FROM bronze.raw_data GROUP BY source),
cams AS (SELECT 'cam' || camera_id AS cam, camera_id, location_en, latitude, longitude
         FROM silver.cameras WHERE {LATEST}),
elems AS (SELECT split_part(source, ':', 2) AS cam, osm_type, tags FROM silver.osm WHERE {LATEST}),
osm AS (
  SELECT cam,
    count(*) FILTER (WHERE osm_type = 'way' AND {tag('highway')} IS NOT NULL) AS n_roads,
    count(*) FILTER (WHERE {tag('highway')} = 'bus_stop') AS n_bus_stops,
    count(*) FILTER (WHERE {tag('railway')} = 'subway_entrance') AS n_subway_entrances,
    count(*) FILTER (WHERE {tag('amenity')} = 'parking') AS n_parking,
    count(*) FILTER (WHERE {tag('amenity')} = 'school') AS n_schools,
    count(*) FILTER (WHERE {tag('amenity')} = 'hospital') AS n_hospitals,
    count(*) FILTER (WHERE {tag('amenity')} = 'marketplace') AS n_marketplaces,
    count(*) FILTER (WHERE osm_type = 'node' AND {tag('highway')} = 'traffic_signals') AS n_traffic_signals,
    count(*) FILTER (WHERE osm_type = 'node' AND {tag('highway')} = 'crossing') AS n_crossings,
    count(*) FILTER (WHERE osm_type = 'way' AND {tag('oneway')} = 'yes') AS n_oneway,
    max(try_cast({tag('lanes')} AS BIGINT)) FILTER (WHERE osm_type = 'way') AS max_lanes,
    max(try_cast({tag('maxspeed')} AS BIGINT)) FILTER (WHERE osm_type = 'way') AS max_speed_kmh
  FROM elems GROUP BY 1),
rw AS (  -- widest BMA-registered road among the named roads near the camera (exact name match)
  SELECT n.cam, max(r.width_m) AS road_width_m
  FROM (SELECT DISTINCT cam, {tag('name')} AS name FROM elems WHERE osm_type = 'way') n
  JOIN (SELECT name, avg(width_m) AS width_m FROM silver.roads WHERE {LATEST} GROUP BY name) r ON r.name = n.name
  GROUP BY 1),
nr AS (
  SELECT cam,
    min(d) FILTER (WHERE kind = 'intersection') AS dist_intersection_m,
    min(d) FILTER (WHERE kind = 'vendor_zone') AS dist_vendor_zone_m,
    min(d) FILTER (WHERE kind = 'paid_parking') AS dist_paid_parking_m
  FROM (SELECT c.cam, p.kind, {haversine_m('c.latitude', 'c.longitude', 'p.lat', 'p.lon')} AS d
        FROM cams c CROSS JOIN (SELECT * FROM silver.bma_points WHERE {LATEST}) p) GROUP BY 1),
tf AS (
  SELECT cam, min(d) AS dist_traffic_site_m, arg_min(vol, d) AS traffic_vol
  FROM (SELECT c.cam, t.vol, {haversine_m('c.latitude', 'c.longitude', 't.lat', 't.lon')} AS d
        FROM cams c CROSS JOIN (SELECT lat, lon, avg(total_vol) AS vol FROM silver.traffic WHERE {LATEST}
                                GROUP BY lat, lon) t) GROUP BY 1)
SELECT cams.camera_id, cams.location_en, cams.latitude, cams.longitude,
  osm.n_roads, osm.n_bus_stops, osm.n_subway_entrances, osm.n_parking, osm.n_schools, osm.n_hospitals,
  osm.n_marketplaces, osm.n_traffic_signals, osm.n_crossings, osm.n_oneway, osm.max_lanes, osm.max_speed_kmh,
  rw.road_width_m,
  nr.dist_intersection_m, nr.dist_vendor_zone_m, nr.dist_paid_parking_m,
  tf.dist_traffic_site_m, tf.traffic_vol
FROM cams
LEFT JOIN osm ON osm.cam = cams.cam
LEFT JOIN rw ON rw.cam = cams.cam
LEFT JOIN nr ON nr.cam = cams.cam
LEFT JOIN tf ON tf.cam = cams.cam
"""


def to_gold() -> None:
    with get_conn() as conn:
        for table, cls in (("cameras", Camera), ("osm", OsmFeature), ("bma_points", BmaPoint),
                           ("roads", RoadWidth), ("traffic", TrafficCount)):
            ensure_table(conn, table, cls)  # a source not loaded yet gives NULL features, not a crash
        conn.execute("CREATE SCHEMA IF NOT EXISTS gold")
        conn.execute(SQL)
        n, osm, nr = conn.execute("SELECT count(*), count(n_roads), count(dist_intersection_m) FROM gold.features").fetchone()
        print(f"gold.features: {n} cameras ({osm} with OSM data, {nr} with BMA distances)")
