from dataclasses import dataclass
from datetime import datetime


@dataclass
class TraffyReport:
    """One Traffy Fondue complaint (a row of the bangkok_monthly file). Timestamps are naive UTC+7."""
    ticket_id: str
    type: str | None = None
    organization: str | None = None
    organization_action: str | None = None
    comment: str | None = None
    coords: str | None = None  # "lon,lat"
    photo: str | None = None
    photo_after: str | None = None
    address: str | None = None
    subdistrict: str | None = None
    district: str | None = None
    province: str | None = None
    timestamp: datetime | None = None
    state: str | None = None  # รอรับเรื่อง / กำลังดำเนินการ / เสร็จสิ้น / ไม่เกี่ยวข้อง
    star: float | None = None
    count_reopen: int | None = None
    last_activity: datetime | None = None
    duration_minutes_inprogress: int | None = None
    duration_minutes_finished: int | None = None
    duration_minutes_total: int | None = None
    timestamp_inprogress: datetime | None = None
    timestamp_finished: datetime | None = None
    message_id: int | None = None
    problemtype_tag: list[str] | None = None  # source looks like "{ภัยทางถนน,...}"

    @property
    def lon_lat(self) -> tuple[float, float] | None:
        if not self.coords:
            return None
        lon, lat = self.coords.split(",")
        return float(lon), float(lat)
