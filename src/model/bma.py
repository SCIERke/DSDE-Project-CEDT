from dataclasses import dataclass
from datetime import datetime


@dataclass
class BmaPoint:
    """A located thing from BMA open data. Lines are flattened to their vertices."""
    kind: str  # vendor_zone | paid_parking | intersection
    lat: float
    lon: float
    name: str | None = None


@dataclass
class RoadWidth:
    """One segment of a road in the BMA local-highway register. No coordinates: join to OSM by `name`."""
    name: str  # e.g. "ถนนกรุงเกษม", same spelling as the OSM `name` tag
    width_m: float
    origin: str | None = None
    destination: str | None = None
    length_km: float | None = None
    district: str | None = None


@dataclass
class TrafficCount:
    """One BMA traffic-volume survey row: vehicles counted on one approach of one junction."""
    crossroads: str
    road: str | None
    date: datetime
    total_vol: int
    lat: float
    lon: float
