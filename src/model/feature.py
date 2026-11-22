from dataclasses import dataclass


@dataclass
class FeatureRow:
    """One row of gold.features: a camera and its surroundings. Column order matches gold.py's SELECT.
    None = unknown (that source is missing or has no match for this camera), never 0."""
    camera_id: str
    location_en: str | None
    latitude: float
    longitude: float
    # OSM, within ~150-300 m of the camera
    n_roads: int | None
    n_bus_stops: int | None
    n_subway_entrances: int | None
    n_parking: int | None
    n_schools: int | None
    n_hospitals: int | None
    n_marketplaces: int | None
    n_traffic_signals: int | None
    n_crossings: int | None
    n_oneway: int | None  # road segments with oneway=yes
    max_lanes: int | None  # max `lanes` tag among nearby roads (sparsely mapped)
    max_speed_kmh: int | None  # max numeric `maxspeed` tag (sparsely mapped)
    # BMA open data
    road_width_m: float | None  # widest registered road with the same name as a nearby OSM road
    dist_intersection_m: float | None  # to the nearest BMA-listed intersection
    dist_vendor_zone_m: float | None  # to the nearest permitted street-vendor zone
    dist_paid_parking_m: float | None  # to the nearest paid on-street parking street (vertex distance)
    dist_traffic_site_m: float | None  # to the nearest traffic-survey junction
    traffic_vol: float | None  # average daily vehicles counted at that junction (one survey month)
