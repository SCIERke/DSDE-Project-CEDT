# `gold.features` — data dictionary

One row per CCTV camera (up to 100, from `data/cctv_info.csv`), describing the **static surroundings** of the camera. There is no date or time in this table: join image detections onto it by `camera_id`.

Built by `uv run python src/main.py gold` ([src/gold.py](../src/gold.py)); the column contract is [`FeatureRow`](../src/model/feature.py), and a test fails if they drift apart.

## Read this first

- **NULL means unknown, never zero.** It appears when a source is missing for that camera (for example the Overpass download failed) or nothing matched. A real count of "none nearby" is `0`.
- **Distances are straight-line metres** (haversine) and are never NULL once the BMA data is loaded, even when the nearest object is 20 km away. Check the magnitude before treating "near" as meaningful.
- **Static snapshot.** OSM and BMA data are as of the day they were downloaded; nothing here changes with the hour of the image.
- **Licences.** OSM is ODbL (credit "© OpenStreetMap contributors"). Most BMA datasets say "license not specified" on data.bangkok.go.th; credit them as the source if you publish.

## Camera

| Column | Type | Meaning | Source | Caveats |
|---|---|---|---|---|
| `camera_id` | text | Camera id from the CCTV list (e.g. `915`). Join key for images. | `cctv_info.csv` | Cameras with bad coordinates or a duplicate id are rejected in silver and absent here. |
| `location_en` | text | English location description. | `cctv_info.csv` | Free text, inconsistent (e.g. `connect BMAcctv` for one camera, a long footbridge description for another). Use for labels, not as a feature. |
| `latitude`, `longitude` | double | Camera position (WGS84). | `cctv_info.csv` | Everything below is measured from this point. If a coordinate is off by 100 m, every feature shifts with it. |

## OpenStreetMap features (Overpass API)

Queried per camera, then counted in gold. Radius differs by feature: **150 m** for roads, traffic signals and crossings; **300 m** for the rest.

| Column | Meaning | Caveats |
|---|---|---|
| `n_roads` | Number of OSM ways tagged `highway=*` within 150 m. | Counts every way type, including footpaths, service lanes and steps, and a long road split into several ways counts several times. A busyness proxy, not a road count. |
| `n_bus_stops` | Features tagged `highway=bus_stop` within 300 m. | OSM mapping in Bangkok is uneven; stops can be missing or duplicated (a stop and its platform). |
| `n_subway_entrances` | `railway=subway_entrance` within 300 m. | Covers MRT entrances only where someone mapped them; BTS (elevated) stations are not subway entrances. |
| `n_parking` | `amenity=parking` features within 300 m. | Parking lots and buildings, not kerbside parking. Says nothing about whether street parking is allowed. |
| `n_schools`, `n_hospitals`, `n_marketplaces` | `amenity=school / hospital / marketplace` within 300 m. | Informal markets and small clinics are often unmapped. A large site may be counted as one feature or as several. |
| `n_traffic_signals` | Nodes tagged `highway=traffic_signals` within 150 m. | One junction can have several signal nodes. Not a junction count. |
| `n_crossings` | Nodes tagged `highway=crossing` within 150 m. | Crossings mapped as ways instead of nodes are not counted. |
| `n_oneway` | Ways with `oneway=yes` within 150 m. | Counts road segments, so it grows with `n_roads`; use the ratio if you want a share. |
| `max_lanes` | Largest numeric `lanes` tag among nearby ways. | **Sparse**: about 100k ways tagged in all of Thailand. NULL does not mean one lane. Values like `2;3` are ignored. |
| `max_speed_kmh` | Largest numeric `maxspeed` tag among nearby ways. | **Sparse**: about 41k ways tagged in Thailand. Values with units (`50 mph`) are ignored. Posted limit, not actual speed. |

All OSM columns are NULL for a camera whose Overpass download failed. Overpass is often overloaded; re-run `main.py bronze` to retry only those cameras.

## Bangkok Metropolitan Administration (BMA) open data

| Column | Meaning | Source | Caveats |
|---|---|---|---|
| `road_width_m` | Registered road width in metres. Takes the nearby OSM roads (within 150 m), matches their Thai `name` exactly against the BMA road register, averages each road's registered segments, and keeps the **widest** match. | BMA register of roads under Public Works (`dpw001`, Oct 2026 file) | **Partial.** The register has 662 segments and only about 429 have a width (6–60 m, median about 20.5). It has no coordinates, so matching is by exact road name only. Roads BMA does not register, or whose OSM name is spelt differently, give NULL. A camera facing a different road than the widest nearby one still gets the widest. Width varies along a road, so the average of segments is approximate. |
| `dist_intersection_m` | Metres to the nearest BMA-listed intersection. | BMA intersections list (`intersec_bma`, 570 intersections) | The list is only BMA's named junctions, not every junction. OSM `n_traffic_signals` and `n_crossings` give the local picture. |
| `dist_vendor_zone_m` | Metres to the nearest permitted street-vendor zone. | BMA ArcGIS `HighValueDataset`, layer 0 (55 points) | These are officially tolerated vending areas. Unlicensed vending and kerb activity are not in the data. Few points, so most cameras are far from any. |
| `dist_paid_parking_m` | Metres to the nearest paid on-street parking street. | BMA ArcGIS `HighValueDataset`, layer 3 (66 street lines) | Measured to the line's **vertices**, not the line, so it can overestimate by a vertex spacing. Only 66 listed streets: a large distance does **not** mean parking is free or allowed. Fee hours exist in the source but are not used. |
| `dist_traffic_site_m` | Metres to the nearest BMA traffic-survey junction. | BMA traffic-volume survey (`traffic_volume2568`) | Survey sites are few and clustered; the nearest one can be kilometres away. Read together with `traffic_vol`. |
| `traffic_vol` | Average vehicles counted at that nearest survey junction. One row is one approach on one survey day, summing all vehicle classes over the 07–09, 09–17 and 17–19 windows. | same | **One month only (Jan 2025)** used as a rough proxy for traffic level. It is the junction's level, not the camera's road. Not comparable to an hourly count. |

## What is not here

- **Time-dependent data** (weather, holidays, Traffy complaints): dropped because photos carry no reliable timestamp. Traffy is still downloaded into bronze/silver if credentials are set, but is not in gold.
- **Parking and stopping restrictions**: OSM has almost none in Thailand (for example `parking:both:restriction` has 0 elements) and no open BMA dataset with coordinates was found.
- **Labels**: gold has no violation label. That comes from the image side.

## Regenerate

```
cd src
uv run python main.py bronze           # resumes; add --refresh to re-download everything
uv run python main.py silver
uv run python main.py gold
```

Close any DuckDB shell on `data/lake.ducklake` first; only one process can write the lake at a time.
