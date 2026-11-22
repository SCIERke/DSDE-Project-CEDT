# Violated car detection platform

Data pipeline for a Bangkok CCTV project: decide, from a camera image plus context about where the camera is, whether a car violates a traffic rule (for example illegal parking).

This repo builds the **context side**: for each CCTV camera, a table of static surroundings (road network, junctions, paid parking, street-vendor zones, traffic level). Image detection and the violation labels are not in the repo yet.

## How it works

Three layers, stored in a local [DuckLake](https://ducklake.select/) (`data/lake.ducklake` plus Parquet files in `data/lake/`):

| Layer | Table(s) | What it holds |
|---|---|---|
| **bronze** | `bronze.raw_data` | Every download stored untouched as JSON, one row per fetch. |
| **silver** | `silver.cameras`, `osm`, `bma_points`, `roads`, `traffic`, `traffy`, `rejects` | Typed, validated rows. Bad rows go to `silver.rejects` with a reason instead of being dropped. |
| **gold** | `gold.features` | One row per camera with its OSM and BMA features. Join image detections on `camera_id`. |

The silver tables are generated from the dataclasses in [src/model/](src/model/), and the cleaners in [src/processing/](src/processing/) cast raw rows into them. Gold is one SQL statement in [src/gold.py](src/gold.py), and its column contract is [FeatureRow](src/model/feature.py).

Time-based sources (weather, holidays) were deliberately dropped: photos carry no reliable timestamp, so everything in gold is static per camera.

## Run it

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cd src
uv run python main.py bronze      # download (resumes: sources already in bronze are skipped)
uv run python main.py silver      # clean into typed tables
uv run python main.py gold        # build gold.features
uv run python main.py all         # all three
```

Options: `--refresh` re-downloads sources already in bronze, `--month YYYY-MM` picks the Traffy month (default: last full month).

A full download takes a while: Overpass is queried once per camera (100 requests), is often overloaded, and each source gets 3 tries. Cameras that still fail are reported as `FAILED`; their OSM columns stay NULL, and re-running `bronze` retries only them.

Only one process can write the lake at a time, so close any DuckDB shell on it before running the pipeline.

## Look at the data

```bash
duckdb -cmd "INSTALL ducklake; LOAD ducklake; ATTACH 'ducklake:/ABSOLUTE/PATH/data/lake.ducklake' AS lake; USE lake;"
```

```sql
SELECT * FROM gold.features LIMIT 10;
SELECT source, reason, count(*) FROM silver.rejects GROUP BY 1, 2;
```

Use the absolute path (the catalog remembers where its data lives). To share the result, export one file instead of the lake:

```bash
cd src && uv run python -c "from core.db import get_conn; get_conn().execute(\"COPY gold.features TO '../data/gold_features.parquet' (FORMAT parquet)\")"
```

## Data sources

| Source | Used for | Notes |
|---|---|---|
| `data/cctv_info.csv` | The camera list (id, lat/lon, description) | The base of the analysis. |
| [OpenStreetMap](https://www.openstreetmap.org/) via Overpass | Roads, bus stops, signals, crossings, amenities, lanes, speed limits near each camera | ODbL: credit "© OpenStreetMap contributors". Parking-restriction tags are almost absent in Thailand. |
| [BMA open data](https://data.bangkok.go.th/) | Road width, intersections, paid parking streets, street-vendor zones, traffic survey | No key needed. Licence mostly "not specified". |
| [Traffy Fondue](https://publicapi.traffy.in.th/) (optional) | Citizen complaints, downloaded into bronze/silver only | Needs your identity in `.env` (see below). Not used in gold. |

Every gold column, with its source and caveats, is documented in [docs/gold_features.md](docs/gold_features.md).

## Configuration

Copy `.env.example` to `.env`. Everything is optional:

- `TRAFFY_NAME`, `TRAFFY_ORG`, `TRAFFY_EMAIL`, `TRAFFY_PURPOSE` (and optional `TRAFFY_TEL`): Traffy asks callers to identify themselves. Without them the Traffy download is skipped.
- `LAKE_META`, `LAKE_DATA`: move the lake somewhere else.

## Tests

```bash
uv run pytest
```

Each test runs against a throwaway lake, so `data/` is never touched.

## Layout

```text
src/
  main.py          CLI
  pipeline.py      bronze -> silver -> gold orchestration
  gold.py          the gold.features SQL
  ingest/          what we download and from where (sources.py), plus the downloader
  processing/      one cleaner per source: cast -> validate, rejects keep a reason
  model/           dataclasses = the silver table schemas (+ FeatureRow for gold)
  core/            config and DuckLake helpers
docs/gold_features.md   data dictionary for gold
test/
```

## Not done yet

- Getting the camera images and running a detector (would become `silver.images`).
- A source of violation labels (hand labels, Traffy as weak labels, or a rule on detections).
- Model training (`src/ml/` is a placeholder).
