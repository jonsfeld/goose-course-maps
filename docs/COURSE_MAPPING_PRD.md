# Goose Course Mapping — PRD + Runbook
### Single source of truth for the LiDAR/OSM course-mapping pipeline

**Version:** 0.1
**Reference course:** Roosevelt Municipal Golf Course, Los Angeles (9 holes, par 33) — complete pipeline run on 2026-04-20.
**Repo:** [github.com/jonsfeld/goose-course-maps](https://github.com/jonsfeld/goose-course-maps)
**Schema spec:** [`SCHEMA.md`](../SCHEMA.md) (authoritative MAP.md format)

---

## 1. Executive Summary

### What this is
A scripted pipeline that converts free, public geospatial data sources into Goose-ready course data files. Each course produces a rich `map.auto.md` + `goose_payload.json` matching Goose's existing Supabase `courses` table schema.

### Why it exists
Goose's differentiation is **decision quality powered by terrain intelligence** — not data that iGolf also has. Every competing golf app uses the same licensed geometry from a small set of providers. This pipeline generates something structurally different:

- 2D geometry from **OpenStreetMap** (free, community-maintained, globally scalable)
- Terrain intelligence from **USGS LiDAR** (1m DEM, 18+ pts/m² point clouds, sub-meter tree canopy)
- Per-hole derived intelligence (green slope + fall-line azimuth, tee-shot corridor, fairway centerline profile, per-green elevation grid) that iGolf does not provide

The output is everything Goose needs to give accurate terrain-aware caddie calls, at zero marginal data-licensing cost per course.

### What it produces per course

| File | Contents | Consumers |
|---|---|---|
| `map.auto.md` | Human-readable course document with frontmatter, per-hole sections, embedded GeoJSON | Audit / review / LLM context |
| `hole_data.json` | Per-hole terrain + slope + corridor + geometry | Internal pipeline |
| `features_osm.geojson` | 48+ OSM features (greens, fairways, bunkers, tees, hole lines with par) | Rendering + vector_data column |
| `goose_payload.json` | Single JSON matching Supabase `courses` table shape | Goose app upsert |
| `goose_upsert.sql` | Ready-to-run SQL `INSERT ... ON CONFLICT DO UPDATE` | Supabase SQL editor |
| Derived rasters (DEM, slope, hillshade, aspect, CHM) | GeoTIFFs for inspection | QGIS / visual audit |

### Scale target
~**15 minutes per course** in pure scripted work after the first pass. First pass on a new course adds ~15 min for Phase A human verification (scorecard lookup, bbox drawing). Realistic throughput: ~20 courses / day for one operator.

---

## 2. Goals & Non-Goals

### Goals
1. Produce course mappings that are **more detailed than iGolf** on the terrain dimension
2. Use **only free public data** — no per-course licensing cost
3. **Reproducible** — any course can be regenerated from committed scripts + notes
4. **Schema-compatible with existing Goose** — same column names, zero new columns needed
5. **Scalable** — no bespoke per-course code; all logic lives in shared tools
6. **Honest about limits** — no synthesized data passed off as ground truth

### Non-Goals
- Compete with iGolf on legacy-course geometry alone (their edge)
- Provide strategy / narrative layers automatically (Phase D, human or LLM work)
- Model dynamic conditions: pin, wind, green speed, grain (always runtime inputs)
- Provide tour-level putting micro-break (1m DEM isn't fine enough; drone photogrammetry would be the upgrade)

---

## 3. Data Sources (Free, Public)

| Source | Provides | License | Access | Roosevelt specifics |
|---|---|---|---|---|
| **USGS 3DEP 1m DEM** | Bare-earth elevation, ±10 cm vertical / 1 m horizontal | Public domain | S3 at `prd-tnm.s3.amazonaws.com` | `CA_LosAngeles_B23`, published 2025-08-11, flown Jan 2023 – Jan 2024 |
| **USGS LPC (LAZ point clouds)** | Raw LiDAR returns for canopy model + tree detection | Public domain | `rockyweb.usgs.gov/vdelivery/...` | `CA_LosAngeles_1_B23`, 18.8 pts/m² density |
| **USGS NAIP aerial** | 4-band (R/G/B/NIR) imagery for QC + visual audit | Public domain | ImageServer `exportImage` endpoint | 2025-01-09 update, ~0.3 m native |
| **OpenStreetMap** | 2D geometry — greens, fairways, bunkers, tees, holes with par | ODbL | Overpass API (`overpass-api.de`) | 48 features for Roosevelt (9 greens, 10 bunkers, 11 tees, 8 fairways, 9 hole lines) |
| **Course site / golf databases** | Scorecard (yardages per tee, handicaps, par), architect, grass | Varies (attribution required) | Web scraping or human lookup | Greenskeeper.org + GolfPass (Wikipedia rejected as pre-2019-renovation stale) |

### Coverage caveats
- **3DEP 1m DEM**: covers most of US, 50-state at 10m minimum. Check at [apps.nationalmap.gov/tnmaccess](https://apps.nationalmap.gov/tnmaccess).
- **OSM golf tagging**: well-trafficked courses excellent; rural/private courses may be sparse. Fall back to SAM2 or hand-tracing.
- **NAIP**: US-only, flown on 2-3 year cycle. International courses need alternate imagery.

---

## 4. Pipeline Architecture

```
┌────────────────────────────────────────────────────────────┐
│  INPUT: course name + bbox                                 │
└──────────────────────┬─────────────────────────────────────┘
                       │
      ┌────────────────┴────────────────┐
      │                                  │
┌─────▼──────┐                    ┌──────▼─────────┐
│  Phase B   │                    │  Phase C       │
│  (OSM)     │                    │  (LiDAR)       │
├────────────┤                    ├────────────────┤
│ Overpass   │                    │ USGS 3DEP DEM  │
│ API → free │                    │ USGS LPC LAZ   │
│ polygons:  │                    │ NAIP (QC)      │
│ • greens   │                    │ → slope        │
│ • fairways │                    │ → hillshade    │
│ • bunkers  │                    │ → aspect       │
│ • tees     │                    │ → CHM          │
│ • holes    │                    │ → tree detect  │
│   + par    │                    │                │
└─────┬──────┘                    └────────┬───────┘
      │                                    │
      └────────────────┬───────────────────┘
                       │
               ┌───────▼────────────────┐
               │  Phase C.5             │
               │  build_hole_data.py    │
               │                        │
               │  • spatial-join OSM    │
               │    features to holes   │
               │  • per-hole terrain    │
               │  • per-green slope     │
               │    (fall-line azimuth) │
               │  • per-green 0.5m grid │
               │  • tee-shot corridor   │
               │    (CHM raycast)       │
               └───────┬────────────────┘
                       │
               ┌───────▼────────────────┐
               │  Phase E               │
               │                        │
               │  assemble_map_md.py    │
               │    → map.auto.md       │
               │                        │
               │  build_goose_payload.py│
               │    → goose_payload.json│
               │    → goose_upsert.sql  │
               └────────────────────────┘
```

### Phase naming (for consistency across sessions)

- **Phase A** — Discovery (scorecard + metadata lookup, bbox selection, source-tile identification)
- **Phase A2** — Download (pull DEMs, LAZ, NAIP from identified sources)
- **Phase B v2** — 2D Feature Extraction (OSM via Overpass API). *v1 (classical CV) deprecated; see Lessons Learned.*
- **Phase C** — Terrain Derivation (DEM merge/clip, slope/hillshade/aspect, CHM, tree detection)
- **Phase C.5** — Per-Hole Intelligence (spatial join + green slope + corridor + elevation profiles)
- **Phase D** — Strategy Layers (*future* — landing zones, approach zones, miss zones; requires human or LLM)
- **Phase E** — Assembly (map.auto.md + goose_payload.json)

---

## 5. Tools & Dependencies

### Python 3.9+ environment
```txt
rasterio>=1.4.0      # DEM + raster I/O
laspy[lazrs]>=2.5.0  # LAZ point cloud reader
shapely>=2.0.0       # Polygon ops, spatial joins
pyproj>=3.6.0        # CRS reprojection
scipy>=1.11.0        # Morphology, local maxima
numpy>=1.26.0        # Array math
requests>=2.31.0     # HTTP (Overpass, NAIP ImageServer)
matplotlib>=3.8.0    # QC rendering
```

Install once per repo: `python3 -m venv tools/.venv && tools/.venv/bin/pip install -r tools/requirements.txt`

### System tools
- `git` + `gh` CLI — version control + GitHub (private repos)
- `curl` — direct S3 downloads
- **Homebrew** (macOS) for installing `gh`

### External services (all free)
- [USGS TNM Access API](https://apps.nationalmap.gov/tnmaccess/) — query DEM/LPC coverage
- [USGS S3 bucket](https://prd-tnm.s3.amazonaws.com/) — direct DEM downloads
- [Rocky Web USGS](https://rockyweb.usgs.gov/vdelivery/) — LAZ point cloud downloads
- [Overpass API](https://overpass-api.de/api/interpreter) — OSM queries
- [USGS NAIP ImageServer](https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer) — NAIP clip export

---

## 6. Repository Layout

```
goose-course-maps/
├── README.md                          # Repo purpose + quick start
├── SCHEMA.md                          # MAP.md format spec (authoritative)
├── docs/
│   └── COURSE_MAPPING_PRD.md          # This file
├── templates/
│   └── map.template.md                # Blank MAP.md
├── tools/                             # All pipeline scripts
│   ├── _common.py                     # Shared helpers
│   ├── requirements.txt
│   ├── fetch_osm_features.py          # Phase B v2
│   ├── fetch_naip_clip.py             # Phase A2 (NAIP)
│   ├── merge_clip_dem.py              # Phase C
│   ├── derive_terrain.py              # Phase C
│   ├── build_chm.py                   # Phase C
│   ├── detect_trees.py                # Phase C
│   ├── build_hole_data.py             # Phase C.5
│   ├── assemble_map_md.py             # Phase E
│   ├── build_goose_payload.py         # Phase E
│   └── render_*.py                    # QC renderers
└── courses/
    └── <slug>/                        # One directory per course
        ├── notes/
        │   ├── scorecard.md           # Hand-verified scorecard
        │   ├── architect_lookup.md    # Metadata + provenance
        │   ├── data_sources.md        # USGS dataset IDs + URLs
        │   ├── bbox.geojson           # Course footprint
        │   └── course_layout.md       # Optional: operator diagram notes
        ├── sources/                   # (gitignored)
        │   ├── dem/*.tif              # ~350 MB/tile
        │   ├── point_cloud/*.laz      # ~100-180 MB/tile
        │   ├── imagery/naip_clip.tif  # ~15 MB
        │   └── osm_features.json      # Raw Overpass response
        ├── derived/                   # Pipeline outputs
        │   ├── dem_clipped.tif
        │   ├── slope.tif / hillshade.tif / aspect.tif
        │   ├── canopy_height_model.tif
        │   ├── canopy_polygons.geojson
        │   ├── individual_trees.geojson
        │   ├── features_osm.geojson
        │   ├── hole_data.json
        │   └── *.png                  # QC renders
        ├── map.auto.md                # Goose-ready course doc
        ├── goose_payload.json         # Supabase-ready JSON
        └── goose_upsert.sql           # SQL upsert statement
```

---

## 7. Runbook — Mapping a New Course

### Preflight checks (before you invest time)

```
[ ] Course is in USA (3DEP 1m LiDAR coverage)
[ ] Course is in OpenStreetMap with golf tags
    → Quick check: query Overpass for bbox, confirm green/fairway/bunker count
[ ] You have the course name + rough lat/lon centroid
```

If any fail, fall back to: drone photogrammetry (LiDAR alt), hand-trace in Google My Maps or QGIS (OSM alt), international DEM sources (Copernicus 30m, NASA SRTM — lower quality).

### Phase A — Discovery & setup (~15 min, human)

1. **Scorecard lookup**: Greenskeeper.org, GolfPass, or course operator site.
   - Avoid Wikipedia — may be stale (pre-renovation figures).
   - Cross-reference two sources; disagreement = flag explicitly.
   - Record: par per hole, handicap index, yardages per tee set, ratings + slope.
2. **Architect + grass lookup**: Wikipedia, golf database sites, golfcoursearchitecture.net.
   - Mark anything unconfirmed as `unknown (probable: ...)` rather than guessing.
3. **Bbox drawing**: visually locate course on Google Maps.
   - **Critical lesson (Roosevelt): do not trust Wikipedia centroid** — verify visually.
   - Draw rectangle with ~50–100 m buffer beyond course edges.
   - Save as `courses/<slug>/notes/bbox.geojson`.
4. **Source discovery**: query USGS TNM Access API for DEM + LPC tiles over bbox.
   - Use the query pattern in `courses/roosevelt_la/notes/data_sources.md` as template.
   - Verify tile vintages; prefer newest B-collection (e.g., `*_B23`).

**Deliverables per course**:
```
notes/scorecard.md
notes/architect_lookup.md
notes/data_sources.md
notes/bbox.geojson
```

### Phase A2 — Download sources (~5 min, scripted)

Use the URL list from `data_sources.md`. Example pattern:

```bash
cd "courses/<slug>/sources"

# DEM tiles (each ~350 MB)
curl -fL -o dem/<tile>.tif "https://prd-tnm.s3.amazonaws.com/.../<tile>.tif"

# LAZ tiles (each ~100-180 MB, typically 4-6 for a course)
for tile in ...; do
  curl -fL -o "point_cloud/USGS_LPC_${tile}.laz" "https://rockyweb.usgs.gov/.../LAZ/${tile}.laz"
done
```

Consider running in background (`curl -#` with `run_in_background: true`) since downloads take several minutes.

**Total per course: ~1.5 GB in `sources/` (gitignored — regenerable from URLs in notes).**

### Phase B v2 — OSM features (~10 sec, scripted)

```bash
python3 tools/fetch_osm_features.py --course <slug>
```

**Expect**: `derived/features_osm.geojson` with greens, fairways, bunkers, tees, hole lines.
**Validate**: feature count should approximately match hole count × feature type.
  Roosevelt sanity: 9 greens exactly, 8-11 fairways, 10-20 bunkers, 9 hole lines.
**If low/zero features**: course isn't well-mapped in OSM — fallback path needed.

### Phase A2 — NAIP (alongside Phase B, ~30 sec)

```bash
python3 tools/fetch_naip_clip.py --course <slug>
```

Produces `sources/imagery/naip_clip.tif` (~15 MB, 2048×2048 default).
This is QC only — NAIP isn't used downstream in the current pipeline but is essential for visual audit.

### Phase C — Terrain derivation (~5 min, scripted)

```bash
python3 tools/merge_clip_dem.py     --course <slug>
python3 tools/derive_terrain.py     --course <slug>
python3 tools/build_chm.py          --course <slug>
python3 tools/detect_trees.py       --course <slug>
```

**Deliverables**:
- `derived/dem_clipped.tif` — 1m DEM merged + reprojected + clipped
- `derived/{slope, hillshade, aspect}.tif` — terrain rasters
- `derived/canopy_height_model.tif` — DSM − DEM
- `derived/{canopy_polygons, individual_trees}.geojson`

**Sanity checks**:
- DEM slope mean: 5-25° for a typical hilly course. If >30°, your bbox may contain too much non-course hillside.
- CHM max: 10-40 m plausible for LA/mid-latitude trees. If >60 m, nodata leak — check code.

### Phase C.5 — Per-hole intelligence (~30 sec, scripted)

```bash
python3 tools/build_hole_data.py --course <slug>
```

Deliverable: `derived/hole_data.json` — per-hole object with terrain + slope + corridor.

**Sanity checks**:
- Every hole has tee + green_center + par
- `net_delta_m` is plausible (Roosevelt: H6 = −20.8 m, H9 = −11.2 m, others ±10 m)
- `sample_count` for green slope: should be 200-1000 pixels per green

### Phase E — Assemble outputs (~10 sec, scripted)

```bash
python3 tools/assemble_map_md.py    --course <slug>
python3 tools/build_goose_payload.py --course <slug> --name-suffix "(LiDAR-OSM)"
```

Deliverables at repo root per course:
- `map.auto.md` (40-60 KB, 1500+ lines)
- `goose_payload.json` (~300-500 KB)
- `goose_upsert.sql` (~100-200 KB)

### Phase F — Load into Goose (1 min, manual)

1. Open Supabase → SQL Editor
2. Paste `goose_upsert.sql` contents
3. Run
4. New row appears in `courses` table tagged `mapping_source = "manual:auto"`

Name suffix `(LiDAR-OSM)` lets this course coexist with any existing same-named row for variance testing.

---

## 8. Honest Limitations

| Dimension | Limit | Why |
|---|---|---|
| Green micro-break for putting | **±0.5-1 m** horizontal over multi-meter runs; **no sub-inch** contours | 1m DEM is the data ceiling; drone photogrammetry (~cm) would upgrade |
| OSM coverage | Variable by course — excellent for well-trafficked, sparse for rural/private | Community-maintained; no SLA |
| Strategy layers (landing / approach / miss zones) | **Empty in Pass 1** | Phase D — requires human or LLM authoring |
| Course_strategy / green_intelligence narrative | **Not produced** | Manual authoring layer; exists in Goose's existing manual data, complementary to ours |
| Dynamic conditions | **Not modeled** | Pin, wind, green speed, grain are runtime inputs — schema excludes by design |
| Course renovations | Data reflects flight date | Cross-check LiDAR vintage against course renovation history |

---

## 9. Lessons Learned (from the Roosevelt first-run)

### The bbox iteration

Four bbox revisions were needed before the final tight, correct footprint:
- v1 (Phase A research): 1.52 km², centered on Wikipedia centroid → **~220 m north of actual course**, captured park hills
- v2: corrected centroid + buffer → contained course but also Greek Theatre + residential
- v3: tight around visible course on NAIP → cut off eastern half when cross-checked against Google Maps
- v4: final, covers full course with margin

**Takeaway**: always visually verify bbox against Google Maps *before* running the pipeline. Cheap to verify, expensive to redo.

### Classical CV on NAIP was a dead end for greens

Two hours spent tuning a color/NDVI/slope/morphology classifier produced:
- 15-22 "green" polygons when 9 were needed (over-segmented)
- 4-5 "fairway" polygons when 9 were needed (over-merged)
- Bunker false positives on hillside chaparral

OSM produced **exactly 9 greens** in **one API call of ~10 seconds**.

**Takeaway**: for any 2D golf layer OSM covers, use OSM first. Classical CV is for falling back, not starting.

### User-annotated seed points couldn't beat OSM either

Even with user-drawn seed circles plus region-grow, region-grow hit the same spectral ambiguity. Only 6 of 9 greens usable, and 2 of those were fairway polygons mis-grown.

**Takeaway**: the limiting factor isn't seed precision; it's that greens and fairways don't have sharp enough spectral separation on NAIP. This is a model-class problem, not a tuning problem.

### Data vintages matter

- Wikipedia scorecard for Roosevelt was pre-2019 renovation → wrong
- Always confirm against **two sources**, prefer post-renovation vintage
- LiDAR flight date (Roosevelt: Jan 2023-24) determines which renovation state is captured

### What iGolf doesn't have and we do

Per the comparison vs. existing Goose Roosevelt (documented in `phase_b_v1_limits.md`):
- Full 9-hole coverage vs. their 6-hole fixture
- 30-point green perimeters vs. just lat/lng centers
- Per-hole tee → green elevation delta
- Per-hole fairway centerline elevation profile (5-yd samples)
- Green elevation grid (1m DEM clipped per green)
- Tee shot corridor (overhead clearance + narrowest clear yards)
- Multiple tee set scorecards with ratings + slope
- Explicit data provenance per field

### What they have and we don't (yet)

- `course_strategy` per hole — hole type, miss hierarchy, preferred miss
- `green_intelligence` per hole — shape, size, firmness, pin tendency

These are orthogonal strategic layers, not geometric. **Phase D work** — either hand-authored by a golf-literate person or LLM-generated from our geometry + terrain.

---

## 10. Quality Checklist Per Course

Before declaring a course "mapped":

```
Phase A
[ ] Scorecard validated against 2+ sources
[ ] Bbox visually confirmed on Google Maps
[ ] USGS tiles + URLs recorded in data_sources.md

Phase B
[ ] OSM feature count matches expected (greens ≈ hole count, etc.)
[ ] If low: investigate before proceeding (may need hand-trace fallback)

Phase C
[ ] DEM slope mean in 5-25° range (hilly course) or <10° (flat)
[ ] CHM max < 50 m (no nodata leak)
[ ] Tree detection count is plausible (not 10× overcount)

Phase C.5
[ ] Every hole has tee, green_center, par populated
[ ] net_delta_m values are plausible (abs ≤ 30 m)
[ ] Green slope sample_count > 100 for every green

Phase E
[ ] map.auto.md renders cleanly (no "unknown" where data exists)
[ ] goose_payload.json passes jq validation
[ ] Column names match Supabase schema

Phase F
[ ] Loaded into Goose without SQL errors
[ ] Appears in course picker
[ ] Tee/green positions visible in UI
[ ] Par matches scorecard
```

---

## 11. Loading into Goose (Reference)

The `goose_upsert.sql` assumes the existing Goose `courses` table schema:

| Column | Our payload populates |
|---|---|
| `name` | Course name + optional "(LiDAR-OSM)" suffix for variance tests |
| `holes` | Integer hole count |
| `location` | `{lat, lng, address, region}` |
| `hole_data` | Array of hole objects matching Goose's existing shape |
| `green_slope_data` | Per-hole slope analysis (dominant deg, fall azimuth, direction) |
| `terrain_data` | Per-hole tee/green elevation + net delta + centerline + elevation grid |
| `vector_data` | Raw OSM FeatureCollection |
| `course_intelligence` | Scorecard + tee shot corridors + data sources + confidence notes |
| `mapping_source` | `"manual:auto"` (distinguishes from `"igolf"`) |
| `igolf_id` | `NULL` |

**Sibling row pattern** (recommended for variance testing against an existing iGolf course):
```bash
python3 tools/build_goose_payload.py --course <slug> --name-suffix "(LiDAR-OSM)"
```
This generates `courses/<slug>/goose_upsert.sql` with the suffixed name, so it sits as a new row alongside any existing course of the same base name.

### Scaling path: Lovable-built ingestion function

For multi-course loading, the right pattern (per Encinitas precedent) is a Supabase Edge Function that:
1. Accepts a course slug
2. Fetches `goose_payload.json` from the public GitHub repo at `github.com/jonsfeld/goose-course-maps/courses/<slug>/`
3. Runs the same `enrichHoles()` + validation + runtime-wiring as the iGolf path
4. Writes to `courses` with `mapping_source = "manual:auto"`
5. Returns validation report

This is a Lovable task once direct-SQL loading has proven the payload shape.

---

## 12. Future Work

### Phase D — Strategy layers
Fill the empty `landing_zones`, `approach_zones`, `miss_zones`, `course_memory_rules` blocks. Two paths:
- **Human-authored**: golf-literate author writes strategy per hole based on our geometry + terrain
- **LLM-generated**: prompt a reasoning model with hole geometry, terrain data, tee shot corridor → produce strategy zones

Should be its own tool: `tools/author_strategy.py`. Outputs can be committed per-course as `notes/strategy.yaml` and merged into `map.auto.md` by the assembler.

### Phase B v3 — SAM2 fallback
For courses with poor OSM coverage, prompted segmentation on NAIP using Meta's SAM 2 model is the fallback. Install `ultralytics`, use user-provided seed points, extract polygons, tag provenance as `sam2_segmented` vs. `osm_sourced`. Not needed for US muni courses — needed for private / rural / international.

### Drone photogrammetry upgrade
For tour-quality putting reads, replace the 1m DEM green clip with sub-cm drone photogrammetry per green. One drone flight per course = ~1 hour + $300-1500. Upgrades the `green_elevation_grid` resolution from 0.5 m to 0.01 m. Tag provenance as `drone_photogrammetry`.

### Tree corridor refinement
Current tree detection catches 500-1500 trees per course. Most are ambient canopy; only ~20-50 are strategy-relevant ("obstructive_clusters" in SCHEMA.md). Add `tools/promote_obstructive_trees.py` that raycasts the fairway corridor against CHM and promotes only trees that pinch shot corridors below 45 yards or overhang below 30 m.

---

## 13. Appendix A — Roosevelt Actual Pipeline Results

Final commit: `2c9799f` (the one containing goose_upsert.sql).

| Metric | Value |
|---|---|
| Total pipeline runtime (after sources cached) | ~7 minutes |
| `map.auto.md` size | 48 KB, 1,599 lines |
| `goose_payload.json` size | 336 KB |
| OSM features ingested | 48 (9 greens, 10 bunkers, 11 tees, 8 fairways, 9 hole lines with par, 1 boundary) |
| Holes with complete data | 9 of 9 |
| Green slope dominant range | 0.16° – 0.75° |
| Max tee→green delta | −20.8 m (Hole 6 downhill) |
| Min tee→green delta | +12.9 m (Hole 2 uphill) |
| Canopy polygons | 3,008 (bbox includes some park canopy) |
| Individual trees (unfiltered) | 16,673 (includes park trees outside course — filtering in Phase D) |
| Commits in repo | 11 |

### Per-hole terrain snapshot

| Hole | Par | HCP | Yd (Black) | Net Δ elevation | Green fall |
|---|---|---|---|---|---|
| 1 | 4 | 6 | 275 | +9.6 m uphill | 0.5° NE |
| 2 | 4 | 2 | 391 | +12.9 m uphill | 0.8° NW |
| 3 | 3 | 9 | 155 | +0.1 m flat | 0.6° N |
| 4 | 4 | 3 | 335 | +1.2 m | 0.4° E |
| 5 | 4 | 4 | 344 | +5.1 m uphill | 0.7° N |
| 6 | 4 | 5 | 315 | −20.8 m downhill | 0.4° NE |
| 7 | 3 | 7 | 163 | +6.6 m uphill | 0.4° NE |
| 8 | 4 | 1 | 351 | +2.6 m | 0.4° NW |
| 9 | 3 | 8 | 167 | −11.2 m downhill | 0.2° NE |
| **Total** | **33** | — | **2,496** | — | — |

---

## 14. Appendix B — Command Quick Reference

For operator running through a new course `<slug>`:

```bash
# Phase A manual work — scorecard, architect, bbox.geojson in courses/<slug>/notes/

# Phase A2 — download (paste URLs from notes/data_sources.md)
cd "courses/<slug>/sources"
curl -fL -o dem/<tile>.tif "<usgs_url>"
# ... repeat for all DEM + LAZ tiles

# Pipeline — all from repo root
python3 tools/fetch_osm_features.py --course <slug>
python3 tools/fetch_naip_clip.py --course <slug>
python3 tools/merge_clip_dem.py --course <slug>
python3 tools/derive_terrain.py --course <slug>
python3 tools/build_chm.py --course <slug>
python3 tools/detect_trees.py --course <slug>
python3 tools/build_hole_data.py --course <slug>
python3 tools/assemble_map_md.py --course <slug>
python3 tools/build_goose_payload.py --course <slug> --name-suffix "(LiDAR-OSM)"

# Commit + push
git add -A
git commit -m "Map <course name>"
git push

# Load into Goose
# → Copy courses/<slug>/goose_upsert.sql into Supabase SQL editor, run
```

---

## 15. Appendix C — Variance Test Findings (Roosevelt, 2026-05-01)

After loading Roosevelt LiDAR-OSM into Goose as a sibling row alongside the existing iGolf and Manual rows, Lovable produced a deterministic-engine variance report ([`courses/roosevelt_la/notes/variance_report.md`](../courses/roosevelt_la/notes/variance_report.md)) showing exactly which fields each engine consumes vs. ignores. Summary of findings:

### What's working today

- ✅ Sibling-row pattern works: `mapping_source = "manual:auto"` falls into Goose's iGolf-shape consumer pipeline via the `!== "manual"` branch in `courseSourceResolver.ts`. Geometry, bunkers, hole shapes consume cleanly.
- ✅ Bunker richness is **higher** than iGolf on H5 (1→2), H7 (0→2), H8 (1→3) — and all extras are read by `findNearestHazard`.
- ✅ Hazard accuracy: water + OB correctly empty (matches reality).
- ✅ Pre-existing iGolf and Manual rows untouched.

### Gaps where our data exists but the runtime can't read it

| # | Gap | Engine consumer | Our payload location | Adapter needed |
|---|---|---|---|---|
| 1 | **Per-hole elevation completely ignored** (H6 -73 ft, H9 -50 ft, H1 +40 ft, H2 +42 ft) | `strategyEngine.ts:989`, `shotDecisionEngine.ts:343` read `holeInfo.terrain.tee_to_green_delta_ft` | `terrain_data['<hole>'].net_delta_m` (per-hole, metric) | New `terrainAdapterLidarOsm.ts` mirroring `terrainAdapterIgolf.ts` |
| 2 | **Per-tee yardages dropped** | `SimulatedRound.tsx`, `GooseSimulationRunner.tsx` read `holeInfo.yards` | `hole_data[i].yardages.{black,blue,white}` | Yardage selector — pick active tee's yardage as `holeInfo.yards` |
| 3 | **Putt break direction missing** | `greenIntelligenceEngine.ts` reads `green_slope_model.dominantBreakDirection` | `green_slope_data['<hole>'].fall_direction` + `fall_line_azimuth_deg` | Green-slope adapter |
| 4 | **Pin-zone strategy missing** | `caddieDecisionEngine.ts` reads `greenSlope.pin_strategy[zone]` | Synthesizable from `zones` + `dominant_slope_deg` | Same green-slope adapter |
| 5 | **Authored `course_strategy` absent** | `strategyEngine.ts:754`, `shotDecisionEngine.ts:905, 1040` | n/a — Phase D not done | Phase D — separate authoring task |
| 6 | **Tee shot corridors unused** | No consumer found in `src/` | `course_intelligence.tee_shot_corridors` | New consumer — would surface tree-corridor calls |
| 7 | **Centerline elevation profile** in wrong place | iGolf path uses `terrain.centerline_profile_ft` per hole | `terrain_data['<hole>'].fairway_centerline_profile` | Part of terrain adapter |

### Geometry-density tradeoff (real but mild)

OSM polygons are sparser than iGolf's:

| Hole | iGolf fairway pts | LiDAR-OSM (post-fix) | Δ |
|---|---|---|---|
| H1 | 67 | 46 | -21 |
| H4 | 96 | 38 | -58 |
| H5 | 99 | 27 | -72 |
| H8 | 102 | 53 | -49 |

This degrades `in_fairway` precision marginally. Not a bug, an OSM-quality cost. **H3 par-3 had 0 fairway points** in OSM (par-3 fairway tagging is conventionally absent); fixed in `build_goose_payload.py` (commit `5ab9d10` onwards) by synthesizing a buffered corridor from `hole_shape` and tagging `fairway_polygon_provenance: "synthesized_from_hole_line"`.

### Adapter plan — Lovable Phase 2 brief

In priority order (impact × effort):

1. **Terrain adapter** (gap #1, #7) — biggest single product impact, restores H6/H9/H1/H2 elevation effects. ~1–2 hrs.
2. **Yardage selector** (gap #2) — accurate base yardage per tee set. ~30 min.
3. **Green-slope adapter** (gap #3, #4) — fixes putt commentary on every hole. ~1 hr.
4. **Resolver explicit branch** for `manual:auto` — replaces the implicit `!== "manual"` fallback with a typed branch. Future-proofing. ~30 min.
5. **Tee shot corridor consumer** (gap #6) — net-new caddie capability, no iGolf equivalent. Larger scope.
6. **Phase D authoring** (gap #5) — different effort class, in `notes/strategy_draft.yaml` already drafted.

### Acceptance criteria for adapters

After Lovable ships fixes 1–3:

- Re-run the same 5 scenarios from the variance report (H1 tee, H4 approach, H6 tee, H8 approach, H3 putt) on the LiDAR-OSM row
- H6 tee shot must reflect the −73 ft downhill (club down, "ball will fly")
- H1, H2 tee shots must reflect uphill (extra club)
- Putt commentary on H3 must include break direction
- iGolf and Manual rows must produce **identical** ShotDecision fingerprints before/after
- Generate `variance_report_after_fixes.md` for the comparison

### What this means for future courses

Every course we map after the adapters ship benefits automatically. The variance test isn't a Roosevelt-specific finding — it's a one-time architectural fix. Once `terrainAdapterLidarOsm.ts` exists, all future LiDAR-OSM courses get the elevation benefit for free.

This is the scalable win the pipeline was designed for: **build the data once, fix the runtime adapter once, infinite-N courses follow**.

---

## 16. Appendix D — Reference URLs

- USGS 3DEP overview: https://www.usgs.gov/3d-elevation-program
- USGS TNM Access API: https://apps.nationalmap.gov/tnmaccess/
- USGS DEM S3 bucket: https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/Projects/
- USGS LPC download root: https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/
- USGS NAIP ImageServer: https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer
- OSM Overpass API: https://overpass-api.de/api/interpreter
- OSM Golf tagging reference: https://wiki.openstreetmap.org/wiki/Sport%3Dgolf
- OpenTopography (alt LiDAR host): https://portal.opentopography.org/

---

**End of PRD**. For schema details see [`SCHEMA.md`](../SCHEMA.md). For repo overview see [`README.md`](../README.md). For Roosevelt-specific notes see [`courses/roosevelt_la/notes/`](../courses/roosevelt_la/notes/).
