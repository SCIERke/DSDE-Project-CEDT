from dataclasses import dataclass


@dataclass
class OsmFeature:
    """One OpenStreetMap element near a camera (road, bus stop, parking, ...). Ways/relations use their centre point."""
    osm_type: str  # node | way | relation
    osm_id: int
    lat: float
    lon: float
    tags: dict[str, str]
