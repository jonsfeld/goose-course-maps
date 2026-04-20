# MAP.md Schema — v0.1 (draft)

A `MAP.md` file is the complete, self-contained specification of a single golf course for Goose. It is human-readable markdown, machine-parseable at every structured block, and designed so the Goose runtime can load a course without any adapter logic.

**Design principles**
1. **Goose-compatible shape.** Field names mirror the existing Goose Supabase `courses` / `hole_data` schema so MAP.md deserializes directly.
2. **Additive only.** New enrichment fields are always optional. Old courses without them continue to work; Goose engines read `undefined` and fall through.
3. **WGS-84 everywhere.** All coordinates are decimal degrees (lat, lon). No projection math at runtime.
4. **Only include certain data.** Dynamic inputs (daily pin, wind, stimp reading, firmness) are runtime inputs, not map data. If it changes round-to-round, it does not belong in MAP.md.
5. **Provenance + confidence baked in.** Every MAP.md declares its sources, vintage, and accuracy notes so downstream consumers know what they can trust.

---

## 1. Course-level YAML frontmatter

```yaml
---
course: Roosevelt Golf Course
alt_names: [Roosevelt Municipal Golf Course, Roosevelt GC]
slug: roosevelt_la
location:
  lat: 34.1265               # course centroid
  lon: -118.2967
  address: "2650 N Vermont Ave, Los Angeles, CA 90027"
  region: "Griffith Park, Los Angeles, CA"
par: 33
holes: 9

# Architectural history (lookup from course site / golf DBs; omit if not certain)
architect: <string | null>
opened: <YYYY | null>
renovated: <YYYY | null>

# Turf — omit any field we cannot confirm
grass:
  tee: <string | null>       # e.g. "bermuda"
  fairway: <string | null>
  rough: <string | null>
  green: <string | null>     # e.g. "poa annua"

# Multiple tee sets — each row is a pro/championship/member/forward option
tee_sets:
  - name: blue
    color: "#1e4fd8"
    rating: 70.2
    slope: 124
    total_yards: 3150
  - name: white
    ...
  - name: red
    ...

# Scorecard — yardages per tee set + handicap index per hole
scorecard:
  - hole: 1
    par: 4
    handicap: 5              # USGA-style handicap/difficulty index (1=hardest)
    yardages: { blue: 380, white: 360, red: 320 }
  - hole: 2
    ...

# Provenance of every data source used to build this file
data_sources:
  dem:
    source: USGS_3DEP_1m
    dataset: <identifier>
    vintage: <YYYY-MM-DD>
  point_cloud:
    source: USGS_LPC
    dataset: <identifier>
    vintage: <YYYY-MM-DD>
  imagery:
    source: <NAIP|Mapbox|ESRI>
    vintage: <YYYY-MM-DD>
  course_site: <URL>
  scorecard_source: <URL>

# What to trust, what to ignore
confidence_notes: >
  Terrain ±10cm vertical, 1m horizontal. Green contours at 1m grid —
  macro slope only, not micro-break. No grain, green speed, pin position,
  or wind data in this document (those are runtime inputs).

# Pipeline identity — allows paired auto/human MAP.md for variance comparison
pipeline: auto                # "auto" | "human"
map_md_version: 0.1
---
```

---

## 2. Per-hole section

Each hole is a top-level `## Hole N` section containing prose + structured blocks. The blocks marked **[Goose-native]** map directly to existing Goose fields; blocks marked **[Enrichment]** are new additive fields Goose does not yet consume but can be extended to.

### 2.1 Narrative (prose)

A 2-3 sentence human-readable description: dogleg direction, defining hazard, strategic character, tee-shot requirement. For Pass-1 auto pipelines, this may be auto-generated from geometry + terrain or left as a placeholder.

### 2.2 Scorecard block

```yaml
### Scorecard
par: 4
handicap: 5
yardages: { blue: 380, white: 360, red: 320 }
```

### 2.3 Tee positions — **[Goose-native]**

```json
### Tee
{
  "blue":  {"lat": 34.12651, "lng": -118.29672},
  "white": {"lat": 34.12648, "lng": -118.29668},
  "red":   {"lat": 34.12645, "lng": -118.29664}
}
```

The default `tee` field Goose reads is the rearmost tee. A `tee_sets_positions` sub-field carries all tees for per-player selection.

### 2.4 Green — **[Goose-native]**

```json
### Green
{
  "center": {"lat": 34.12430, "lng": -118.29120},
  "perimeter": [
    {"lat": ..., "lng": ...},
    ...
  ],
  "distance_to_front_yd": 372,
  "distance_to_center_yd": 380,
  "distance_to_back_yd":  388
}
```

`perimeter` is the outer edge of the putting surface. Must be a closed polygon (first point == last point).

### 2.5 Geometry — **[Goose-native + Enrichment]**

A single GeoJSON FeatureCollection holding every playable-surface polygon. Each feature has a `properties.kind` discriminator.

```geojson
### Geometry
{ "type": "FeatureCollection", "features": [
  { "properties": {"kind": "tee_box", "name": "blue"},            "geometry": {...} },
  { "properties": {"kind": "tee_box", "name": "white"},           "geometry": {...} },
  { "properties": {"kind": "tee_box", "name": "red"},             "geometry": {...} },
  { "properties": {"kind": "hole_shape"},                         "geometry": {...} },
  { "properties": {"kind": "fairway"},                            "geometry": {...} },
  { "properties": {"kind": "first_cut"},                          "geometry": {...} },    // ENRICHMENT
  { "properties": {"kind": "rough"},                              "geometry": {...} },    // ENRICHMENT
  { "properties": {"kind": "fringe"},                             "geometry": {...} },    // ENRICHMENT
  { "properties": {"kind": "green"},                              "geometry": {...} },
  { "properties": {"kind": "green_perimeter_offset", "offset_ft": 1.0 }, "geometry": {...} }, // ENRICHMENT — safe pin zone
  { "properties": {"kind": "bunker", "label": "h1_right_gs", "severity": "deep", "context": "greenside"}, "geometry": {...} },
  { "properties": {"kind": "water", "penalty_type": "lateral"},   "geometry": {...} },
  { "properties": {"kind": "out_of_bounds", "side": "left"},      "geometry": {...} },
  { "properties": {
      "kind": "tree_canopy",
      "min_height_m": 4.2,
      "p50_height_m": 12.8,
      "p90_height_m": 21.5,
      "max_height_m": 24.1,
      "area_m2": 340
    }, "geometry": {...} }     // ENRICHMENT — height distribution per disjoint canopy polygon
]}
```

**Accepted `kind` values:**
- Goose-native: `tee_box`, `hole_shape`, `fairway`, `green`, `green_perimeter_offset`, `bunker`, `water`, `out_of_bounds`
- Enrichment: `first_cut`, `rough`, `fringe`, `tree_canopy`

**Bunker `severity`:** `shallow | moderate | deep | pot`
**Bunker `context`:** `greenside | fairway | waste | cross`

### 2.6 Terrain — **[Goose-native + Enrichment]**

```yaml
### Terrain
tee_elevation_m: 18.2
green_elevation_m: 14.6
net_delta_m: -3.6                   # negative = downhill from tee to green
fairway_centerline_profile_yd5:     # ENRICHMENT — 5yd sampling instead of 10
  - {yd_from_tee: 0,   elev_m: 18.20}
  - {yd_from_tee: 5,   elev_m: 18.15}
  - {yd_from_tee: 10,  elev_m: 18.08}
  - ...
```

The full-course elevation raster lives as a GeoTIFF in `sources/dem/` and is not embedded in MAP.md (too large, not useful to LLMs).

### 2.7 Green slope data — **[Goose-native]**

Maps 1:1 to Goose's `green_slope_data` column. Drives the existing `greenReadingEngine.ts`.

```json
### Green Slope Data
{
  "overall_slope": "back-to-front",
  "dominant_slope_deg": 2.8,
  "secondary_tilt": "right-to-left",
  "secondary_slope_deg": 0.9,
  "fall_line_azimuth_deg": 185,
  "zones": {
    "front":  {"severity": "mild",     "direction": "back-to-front", "notes": "..."},
    "middle": {"severity": "moderate", "direction": "back-to-front", "notes": "..."},
    "back":   {"severity": "steep",    "direction": "right-to-left", "notes": "..."}
  },
  "steep_runoffs": [
    {"side": "short_right", "max_slope_pct": 8.2, "notes": "apron feeds to bunker"}
  ],
  "best_miss": "left of hole above pin",
  "false_front": null
}
```

**Severity scale:** `flat | mild | moderate | steep | severe`
**Direction vocabulary:** `back-to-front | front-to-back | left-to-right | right-to-left | [compound e.g. back-left-to-front-right]`

### 2.8 Green elevation grid — **[Enrichment]**

The prescriptive-putting enabler. A 2D array of elevation samples clipped to the green polygon.

```json
### Green Elevation Grid
{
  "origin_latlon": [34.12408, -118.29140],   // SW corner of bounding box
  "resolution_m": 0.5,
  "rows": 40,
  "cols": 60,
  "units": "meters",
  "null_value": -9999,                       // cells outside the green polygon
  "grid": [
    [14.60, 14.59, 14.58, ...],
    [14.58, 14.57, 14.55, ...],
    ...
  ]
}
```

At runtime Goose can compute elevation-along-path for any ball→hole line by bilinear-interpolating this grid. Combined with the overall slope data, it enables break-integration reads.

### 2.9 Trees — **[Enrichment]**

Trees only appear here if they **constrain play**. Ornamental trees and out-of-corridor canopy stay as ambient `tree_canopy` polygons in the Geometry block but are not enumerated individually.

```yaml
### Trees
obstructive_clusters:
  - id: h1_left_pines
    side: left
    dist_from_tee_yd: [180, 260]     # yardage range along hole centerline
    p90_height_m: 21.5               # 90th-percentile canopy height in this cluster
    max_height_m: 24.1               # tallest canopy in this cluster
    effect: "inside-corner cluster cutting aggressive draw line"

tee_shot_corridor:                   # computed per tee set by raycast over the CHM raster
  - tee: blue
    clear_lateral_yd: 42             # narrowest canopy-free fairway width along shot line
    overhead_clear_m: 33             # lowest overhead clearance along the shot line (sampled from CHM)
    forced_shape: none               # none | fade_preferred | draw_preferred | fade_required | draw_required
    pinch_at_yd: 215                 # distance from tee where corridor is narrowest
  - tee: white
    ...

# Optional: individual trees detected from CHM via local-maxima detection.
# Only populated for strategy-relevant clusters (those in obstructive_clusters above).
# Enables per-tree queries and future glasses rendering.
individual_trees:
  - {lat: 34.12651, lng: -118.29692, height_m: 22.0, canopy_radius_m: 5.4, cluster_id: h1_left_pines}
  - {lat: 34.12658, lng: -118.29687, height_m: 18.3, canopy_radius_m: 4.1, cluster_id: h1_left_pines}
```

**Three-layer tree model recap:**
- **CHM raster** (`derived/canopy_height_model.tif`) = ground truth, 1m per-pixel heights. Used by the corridor raycast and runtime queries that need precision.
- **`tree_canopy` polygons** (in the Geometry block) = fast runtime lookup with height distribution per polygon (`min / p50 / p90 / max_height_m`).
- **`individual_trees`** (optional, here) = per-tree points with height + canopy radius. Detected from the CHM for strategy-relevant clusters. Enables glasses-era rendering and tree-level voice calls ("pine at 190, you're clear by 15 feet").

**Promotion rule (for `obstructive_clusters`):**
- Pinches the shot corridor below ~45 yd at a likely landing zone, **or**
- Overhead canopy <30 m clear along a shot line, **or**
- Inside-corner of a dogleg forcing carry / cut decision, **or**
- Near-green shape-forcer on approach

### 2.10 Strategy — **[Goose-native, Phase D]**

Deferred for Pass-1 auto pipelines. Empty arrays until human-in-loop authoring or LLM-assisted generation.

```yaml
### Strategy
landing_zones: []                    # see Landing Zone schema below
approach_zones: []
miss_zones: []
course_memory_rules: []              # → goes to Goose's course_memory_rules table
```

**Landing Zone schema** (populated in Pass 2):
```yaml
- hole: 1
  club: driver                       # default play
  priority: default                  # default | safe | aggressive
  center_latlon: [..., ...]
  width_yd: 35
  min_dist_yd: 240
  max_dist_yd: 275
  left_penalty: high                 # low | medium | high
  right_penalty: medium
  rollout: firm                      # soft | standard | firm
  hazard_pressure: 0.6               # 0-1
  leaves_distance_yd: 110
  approach_zone_id: h1_ap_1          # links to approach_zones
  rationale: "Fairway opens after the left cluster; stay center-right for best angle."
```

**Approach Zone schema:**
```yaml
- id: h1_ap_1
  hole: 1
  target_side: center                # left | center | right
  distance_in_yd: 110
  miss_left_penalty: medium
  miss_right_penalty: high
  green_slope: back-to-front
  rationale: "Pin left is guarded by bunker; play to center-right of green."
```

**Miss Zone schema:**
```yaml
- hole: 1
  side: long_right
  penalty: severe
  shot_difficulty: hard
  rationale: "Downhill lie into runoff, green is running away."
```

---

## 3. Ordering of sections

A single hole's section in its recommended order:

```
## Hole N — Par X, YYY yd (handicap Z)
[narrative]
### Scorecard
### Tee
### Green
### Geometry
### Terrain
### Green Slope Data
### Green Elevation Grid
### Trees
### Strategy
```

---

## 4. File companion assets

Some data is too large or binary for MAP.md. Each course folder holds them separately:

```
courses/<slug>/
├── map.auto.md                 # full Pass-1 MAP.md
├── map.human.md                # full Pass-2 MAP.md (when produced)
├── sources/
│   ├── dem/<tile>.tif          # 1m DEM GeoTIFF
│   ├── point_cloud/*.laz       # raw LiDAR point cloud tiles
│   └── imagery/*.tif           # NAIP or equivalent aerial
├── derived/
│   ├── slope.tif               # QGIS/GDAL-derived slope raster
│   ├── hillshade.tif
│   ├── aspect.tif
│   └── canopy_height_model.tif # DSM - DEM
└── notes/
    ├── scorecard.md            # raw scorecard + handicap verification
    └── architect_lookup.md     # provenance for metadata fields
```

MAP.md references these by relative path when useful (e.g., in `data_sources.dem.local_path`), but they are not embedded.

---

## 5. Goose compatibility mapping

Quick reference — how MAP.md fields deserialize into Goose's existing Supabase schema.

| MAP.md field | Goose `courses` column | Goose `hole_data[n]` key |
|---|---|---|
| `course`, `slug`, `par`, `holes` | `name`, `id` (derived), `holes` | — |
| `location.{lat,lon,address}` | `location` (JSON) | — |
| `### Tee` (default = first entry) | — | `tee` |
| `### Green.center` | — | `green_center` |
| `### Green.perimeter` | — | `green_perimeter` |
| `### Geometry` feature w/ `kind: hole_shape` | — | `hole_shape` |
| `### Geometry` feature w/ `kind: fairway` | — | `fairway_polygon` |
| `### Geometry` features w/ `kind: water` | — | `water_hazards[]` |
| `### Geometry` features w/ `kind: bunker` | — | `bunkers[]` |
| `### Geometry` features w/ `kind: out_of_bounds` | — | `out_of_bounds[]` |
| `### Green Slope Data` | `green_slope_data` (JSON) | — |
| `### Terrain` + elevation grids | `terrain_data` (GooseTerrainGrid) | — |
| `### Geometry` enrichment kinds (`first_cut`, `fringe`, `rough`, `tree_canopy`) | `vector_data` (JSON) | — |
| `### Trees`, `### Green Elevation Grid`, `### Strategy` | `course_intelligence` (JSON) | — |
| `data_sources` | `mapping_source` (string) + full object under `course_intelligence.provenance` | — |
| `pipeline` | `mapping_source` suffix: `"manual:auto"` vs `"manual:human"` | — |

Loading a MAP.md = parse frontmatter + section blocks → build `courses` row + `hole_data` array. One pass, deterministic, no AI.

---

## 6. Versioning

`map_md_version` is a semver-ish string on every MAP.md. Breaking changes bump the major (e.g. `0.x → 1.0`). Additive enrichments bump the minor. Bug-fix regenerations bump patch.

Goose's course loader reads `map_md_version` and falls back gracefully on unknown fields.

---

## 7. Locked decisions (v0.1)

- **Tree storage:** three-layer model — CHM raster as ground truth, `tree_canopy` polygons with height-distribution stats (`min / p50 / p90 / max`) for fast lookup, optional `individual_trees` points for strategy-relevant clusters (enables glasses rendering).
- **`course_memory_rules`:** strictly empty in v0.1. Populated later from real player shot data or course-pro interviews. No LLM-seeded guesses — violates the "only certain data" principle.
- **Green elevation grid resolution:** 0.5m. Source DEM is 1m; LAZ point cloud supports honest 0.5m. Anything finer is fake precision until drone photogrammetry is added.
- **Fairway centerline sampling:** adaptive 10yd default, densify to 5yd where local slope between samples exceeds 5%. Lean on flats, precise on rolling terrain.

## 8. Future v0.2+ considerations

- Drone-photogrammetry green overlay for sub-cm putting contours (not in current pipeline).
- Per-hole wind exposure modeling from course orientation + surrounding terrain.
- Bunker lip-height correction (bare-earth DEM flattens sand; needs point-cloud return classification).
- Pin-position history / common pin zones, once round-level data accumulates.
