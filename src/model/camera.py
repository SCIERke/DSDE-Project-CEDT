from dataclasses import dataclass


@dataclass
class Camera:
    """One CCTV camera (a row of data/cctv_info.csv)."""
    camera_id: str
    latitude: float
    longitude: float
    location_en: str | None = None
    image_count: int | None = None
