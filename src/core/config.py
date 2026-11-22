import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")  # real env vars win over the file

# DuckLake: catalog metadata in one file, table data as Parquet files under LAKE_DATA.
LAKE_META = os.getenv("LAKE_META") or str(ROOT / "data" / "lake.ducklake")
LAKE_DATA = os.getenv("LAKE_DATA") or str(ROOT / "data" / "lake") + "/"

# Traffy Fondue asks callers to identify themselves; name/org/email/purpose are required, tel optional.
TRAFFY_IDENTITY = {k: os.getenv(f"TRAFFY_{k.upper()}", "") for k in ("name", "org", "email", "purpose", "tel")}
