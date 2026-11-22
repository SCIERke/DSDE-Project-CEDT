import argparse
from datetime import datetime

from ingest.sources import last_full_month
from pipeline import run


def month(s: str) -> str:
    try:
        return datetime.strptime(s, "%Y-%m").strftime("%Y-%m")
    except ValueError:
        raise argparse.ArgumentTypeError(f"{s!r} is not YYYY-MM")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("layer", nargs="?", default="all", choices=["bronze", "silver", "gold", "all"])
    p.add_argument("--month", type=month, default=last_full_month(), help="YYYY-MM to download (default: last full month)")
    p.add_argument("--refresh", action="store_true", help="re-download sources already in bronze")
    a = p.parse_args()
    run(a.layer, a.month, a.refresh)
