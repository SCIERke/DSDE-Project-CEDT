import csv
from datetime import date, timedelta
from pathlib import Path

from core.config import ROOT, TRAFFY_IDENTITY
from ingest.downloader import DataDownloader

CAMERAS_CSV = ROOT / "data" / "cctv_info.csv"


def load_cameras(path: Path = CAMERAS_CSV) -> dict[str, tuple[float, float]]:
    """camera_id -> (lat, lon), one row per camera. Key is `cam<id>` (colon-free: bronze source names split on ':')."""
    with open(path, encoding="utf-8") as f:
        return {f"cam{r['camera_id']}": (float(r["latitude"]), float(r["longitude"])) for r in csv.DictReader(f)}


CAMERAS = load_cameras()
UA = {"User-Agent": "dsde-course-project/0.1"}  # Overpass answers 406 without one

OVERPASS = """[out:json][timeout:25];
(way(around:150,{lat},{lon})[highway];
 node(around:150,{lat},{lon})[highway~"^(traffic_signals|crossing)$"];
 nwr(around:300,{lat},{lon})[highway=bus_stop];
 nwr(around:300,{lat},{lon})[railway=subway_entrance];
 nwr(around:300,{lat},{lon})[amenity~"^(parking|school|hospital|marketplace)$"];
);out center;"""

# BMA (Bangkok) open data: not per camera, one file each; gold measures distances from each camera to them.
ARCGIS = "https://cpudgiportal.bangkok.go.th/arcgis/rest/services/OKR2568/HighValueDataset/FeatureServer/{}/query"
ARCGIS_PARAMS = {"where": "1=1", "outFields": "*", "outSR": 4326, "f": "json"}
CKAN = "https://data.bangkok.go.th/dataset/"
BMA_CSV = {  # source name -> CKAN resource url
    "bma_intersections": CKAN + "ffdde9f8-22d1-42f3-a517-447ba11153ca/resource/32eb5b7c-0e50-4b90-b331-3551adf64180/download/intersec_20251117_14.57_new-1.csv",
    "bma_roads": CKAN + "0c6394c7-b741-470e-b62f-f979a8e53184/resource/c997f718-d36b-46d1-a94b-5b4402ac8712/download/data_bangkok_yota_road_2026_10.csv",
    # ponytail: one month of the survey as a static traffic-level proxy; average more months if it proves useful
    "bma_traffic": CKAN + "81df7ca2-6464-4949-9842-3090893989db/resource/cf87dc79-6367-4c3b-b1fd-70cb740d1bae/download/opendata-jan-2025.csv",
}


def last_full_month() -> str:
    """Default month: Traffy publishes one file per month (bangkok_YYYY-MM), so the last finished one."""
    return (date.today().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")


def register_sources(d: DataDownloader, month: str) -> None:
    d.register("bma_vendors", ARCGIS.format(0), ARCGIS_PARAMS)  # permitted street-vendor zones (points)
    d.register("bma_parking", ARCGIS.format(3), ARCGIS_PARAMS)  # paid on-street parking streets (lines)
    for name, url in BMA_CSV.items():
        d.register(name, url)

    for name, (lat, lon) in CAMERAS.items():
        d.register(f"overpass:{name}", "https://overpass-api.de/api/interpreter",
                   {"data": OVERPASS.format(lat=lat, lon=lon)}, headers=UA, timeout=90)

    who = {k: v for k, v in TRAFFY_IDENTITY.items() if v}
    missing = [k for k in ("name", "org", "email", "purpose") if k not in who]
    if missing:
        print(f"skipping traffy: set TRAFFY_{', TRAFFY_'.join(k.upper() for k in missing)} in .env")
    else:
        d.register(f"traffy:{month}", "https://publicapi.traffy.in.th/teamchadchart-stat-api/download/bangkok_monthly",
                   {**who, "file_name": f"bangkok_{month}"}, timeout=120)
