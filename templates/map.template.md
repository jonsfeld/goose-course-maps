---
course: <Course Name>
alt_names: []
slug: <course_slug>
location:
  lat: 0.0
  lon: 0.0
  address: ""
  region: ""
par: 0
holes: 0
architect: null
opened: null
renovated: null
grass:
  tee: null
  fairway: null
  rough: null
  green: null
tee_sets: []
scorecard: []
data_sources:
  dem:
    source: USGS_3DEP_1m
    dataset: null
    vintage: null
  point_cloud:
    source: USGS_LPC
    dataset: null
    vintage: null
  imagery:
    source: null
    vintage: null
  course_site: null
  scorecard_source: null
confidence_notes: ""
pipeline: auto
map_md_version: 0.1
---

# <Course Name> — Overview

[Narrative: designer intent, character, defining features, typical conditions.]

# Data & Sources

[Provenance paragraph: what LiDAR vintage, what imagery, what was derived vs. authored.]

---

## Hole 1 — Par X, YYY yd (handicap Z)

[narrative]

### Scorecard
par: 0
handicap: 0
yardages: {}

### Tee
```json
{}
```

### Green
```json
{
  "center": {"lat": 0, "lng": 0},
  "perimeter": [],
  "distance_to_front_yd": 0,
  "distance_to_center_yd": 0,
  "distance_to_back_yd": 0
}
```

### Geometry
```geojson
{ "type": "FeatureCollection", "features": [] }
```

### Terrain
tee_elevation_m: 0
green_elevation_m: 0
net_delta_m: 0
fairway_centerline_profile_yd5: []

### Green Slope Data
```json
{
  "overall_slope": null,
  "dominant_slope_deg": 0,
  "secondary_tilt": null,
  "secondary_slope_deg": 0,
  "fall_line_azimuth_deg": 0,
  "zones": {},
  "steep_runoffs": [],
  "best_miss": null,
  "false_front": null
}
```

### Green Elevation Grid
```json
{
  "origin_latlon": [0, 0],
  "resolution_m": 0.5,
  "rows": 0,
  "cols": 0,
  "units": "meters",
  "null_value": -9999,
  "grid": []
}
```

### Trees
obstructive_clusters: []
tee_shot_corridor: []

### Strategy
landing_zones: []
approach_zones: []
miss_zones: []
course_memory_rules: []

---

## Hole 2 — Par X, YYY yd (handicap Z)

[repeat per hole]
