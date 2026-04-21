# tools/

Phase C (terrain derivation) + helper scripts. Pure Python, headless, scriptable.

Phase B (polygon tracing with SAM / vision models) lives in a later iteration — not included here yet.

## Setup

Mac prerequisites: Python 3.11+ (check with `python3 --version`).

```bash
cd tools/
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

All deps ship binary wheels on macOS, no GDAL or PDAL system install needed.

## Scripts

Run each from the repo root unless noted. Every script is idempotent — re-running overwrites prior output.

| Script | Input | Output | Purpose |
|---|---|---|---|
| `fetch_naip_clip.py` | course bbox | `courses/<slug>/sources/imagery/naip_clip.tif` | Pull NAIP aerial clip from USGS ImageServer |
| `merge_clip_dem.py` | DEM tiles + bbox | `courses/<slug>/derived/dem_clipped.tif` | Merge adjacent 1m DEM tiles, clip to course bbox, reproject to WGS-84 |
| `derive_terrain.py` | clipped DEM | `courses/<slug>/derived/{slope,hillshade,aspect}.tif` | Slope / hillshade / aspect rasters for authoring + voice-caddie lookups |
| `build_chm.py` | LAZ tiles + clipped DEM | `courses/<slug>/derived/canopy_height_model.tif` | Rasterize point cloud → DSM, subtract bare-earth DEM → CHM |
| `detect_trees.py` | CHM | `courses/<slug>/derived/{individual_trees,canopy_polygons}.geojson` | Local-maxima tree detection + canopy polygons with height distribution |

## Typical pipeline

```bash
# 1. Get aerial imagery (fast, ~30s)
python3 tools/fetch_naip_clip.py --course roosevelt_la

# 2. Process DEM (requires 2 DEM tiles already downloaded to sources/dem/)
python3 tools/merge_clip_dem.py --course roosevelt_la
python3 tools/derive_terrain.py --course roosevelt_la

# 3. Process point cloud (requires 6 LAZ tiles already downloaded to sources/point_cloud/)
python3 tools/build_chm.py --course roosevelt_la
python3 tools/detect_trees.py --course roosevelt_la
```

## Course config

Each course has a `courses/<slug>/notes/bbox.geojson` defining its footprint. Scripts read that file via `--course <slug>` and derive the bbox from it.

## What's not here yet

- **Phase B tracing** (SAM/segmentation on NAIP → fairway/green/bunker polygons). Planned next.
- **Green elevation grid extractor** (clip DEM to green polygon → 0.5m grid JSON). Runs after Phase B produces green polygons.
- **Tee shot corridor raycast** (sample CHM along tee→green line, measure pinch widths and overhead clearance). Runs after Phase B produces fairway polygon and tee positions.
- **MAP.md assembler** (Phase E: stitch all derived artifacts into a single `map.auto.md`). Runs last.
