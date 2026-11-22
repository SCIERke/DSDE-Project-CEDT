"""Shared by every cleaner: the result type and the coordinate box."""
from dataclasses import dataclass, field

LON, LAT = (97.0, 106.0), (5.0, 21.0)


@dataclass
class Cleaned:
    good: list = field(default_factory=list)
    rejected: list[tuple[dict, str]] = field(default_factory=list)  # (raw row, reason)
