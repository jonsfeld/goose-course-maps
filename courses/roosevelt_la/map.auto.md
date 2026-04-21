---
course: Roosevelt Municipal Golf Course
alt_names: [Roosevelt Municipal Golf Course, Roosevelt GC, Vermont Canyon]
slug: roosevelt_la
location:
  lat: 34.1204
  lon: -118.292
  address: "2650 N Vermont Ave, Los Angeles, CA 90027"
  region: "Griffith Park, Los Angeles, CA"
par: 33
holes: 9
architect: unknown (probable: John Ward with Billy Bell Jr., 1964; not primary-source verified)
opened: 1964
renovated: 2019
renovation_architect: Forrest Richardson (ASGCA)
grass:
  tee: unknown
  fairway: bermuda
  rough: unknown
  green: bentgrass
tee_sets:
  - name: black
    par: 33
    total_yards: 2496
    rating_mens: 63.8
    slope_mens: 106
    rating_womens: 68.8
    slope_womens: 114
  - name: blue
    par: 33
    total_yards: 2316
    rating_mens: 62.2
    slope_mens: 102
    rating_womens: 67.0
    slope_womens: 109
  - name: white
    par: 33
    total_yards: 1641
    rating_mens: 58.6
    slope_mens: 87
    rating_womens: 59.2
    slope_womens: 92
scorecard:
  - hole: 1
    par: 4
    handicap: 6
    yardages: { black: 275, blue: 256, white: 192 }
  - hole: 2
    par: 4
    handicap: 2
    yardages: { black: 391, blue: 376, white: 234 }
  - hole: 3
    par: 3
    handicap: 9
    yardages: { black: 155, blue: 132, white: 105 }
  - hole: 4
    par: 4
    handicap: 3
    yardages: { black: 335, blue: 308, white: 197 }
  - hole: 5
    par: 4
    handicap: 4
    yardages: { black: 344, blue: 323, white: 264 }
  - hole: 6
    par: 4
    handicap: 5
    yardages: { black: 315, blue: 295, white: 225 }
  - hole: 7
    par: 3
    handicap: 7
    yardages: { black: 163, blue: 149, white: 125 }
  - hole: 8
    par: 4
    handicap: 1
    yardages: { black: 351, blue: 330, white: 173 }
  - hole: 9
    par: 3
    handicap: 8
    yardages: { black: 167, blue: 147, white: 126 }
data_sources:
  dem:
    source: USGS_3DEP_1m
    dataset: CA_LosAngeles_B23
    vintage: "2025-08-11"
    lidar_collection: "2023-01 to 2024-01"
  point_cloud:
    source: USGS_LPC
    dataset: CA_LosAngeles_1_B23
    vintage: "2025-06-13"
    density_pts_per_m2: 18.8
  imagery:
    source: USGS_NAIP_ImageServer
    vintage: "2025-01-09"
  features_2d:
    source: OpenStreetMap (Overpass API)
    vintage: "2026-04-21"
    license: ODbL
  scorecard_source: "Greenskeeper.org + GolfPass (Wikipedia rejected as pre-2019 renovation)"
confidence_notes: >
  Terrain: ±10cm vertical / 1m horizontal. Green-slope magnitudes
  derived from 1m DEM are low-bound estimates (macro slope only);
  they do not capture micro-breaks that matter for putting reads.
  Grain and green speed are not modeled — runtime inputs only.
  2D geometry is community-sourced via OSM and may be up to several
  meters off true boundaries in places.
pipeline: auto
map_md_version: 0.1
---

# Roosevelt Municipal Golf Course — Overview

Roosevelt Municipal is a 9-hole par-33 municipal course in Griffith Park,
on the south end of the park near the Greek Theatre and Vermont Canyon
Tennis Courts. Opened in 1964, restored in 2019 by Forrest Richardson
(Better Billy Bunker renovation, new forward tees, recycled-water
irrigation). The course is hilly and tightly tree-lined — a canyon layout
with significant elevation changes between holes. Walking-only, no driving range.

# Data & Sources

Terrain layer derived from USGS 3DEP 1m LiDAR (CA_LosAngeles_B23, lidar
flown Jan 2023 – Jan 2024, published Aug 2025). Point-cloud density
18.8 pts/m² enables tree-level canopy detection. 2D geometry (greens,
fairways, bunkers, tees, hole lines with par) comes from OpenStreetMap
community mapping via the Overpass API. NAIP aerial imagery (Jan 2025,
USGS ImageServer) used for visual QC.

---
## Hole 1 — Par 4, 275 yd (handicap 6)

Par-4 running 256 yd from the back tee. The hole plays 9.6 m uphill tee-to-green. Narrowest fairway corridor is ~22.4 yd at 0.0 yd from tee.

### Scorecard
```yaml
par: 4
handicap: 6
yardages: { black: 275, blue: 256, white: 192 }
```

### Tee
```json
{
  "centroid": {
    "lat": 34.11828,
    "lng": -118.2926317
  },
  "tee_sets_detected": 1
}
```

### Green
```json
{
  "center": {
    "lat": 34.1203187,
    "lng": -118.2936956
  },
  "osm_id": 893595853,
  "area_m2": 472.1,
  "distance_from_tee_yd": 255.6
}
```

### Terrain
```yaml
tee_elevation_m: 228.65
green_elevation_m: 238.25
net_delta_m: 9.59
fairway_centerline_profile_yd5:
  - {yd_from_tee: 0.0, elev_m: 228.65}
  - {yd_from_tee: 5.0, elev_m: 228.7}
  - {yd_from_tee: 10.0, elev_m: 228.51}
  - {yd_from_tee: 15.0, elev_m: 228.54}
  - {yd_from_tee: 20.1, elev_m: 228.57}
  - {yd_from_tee: 25.1, elev_m: 228.56}
  - {yd_from_tee: 30.1, elev_m: 228.48}
  - {yd_from_tee: 35.1, elev_m: 228.54}
  - {yd_from_tee: 40.1, elev_m: 228.8}
  - {yd_from_tee: 45.1, elev_m: 229.24}
  - {yd_from_tee: 50.1, elev_m: 229.53}
  - {yd_from_tee: 55.1, elev_m: 229.77}
  - {yd_from_tee: 60.2, elev_m: 229.94}
  - {yd_from_tee: 65.2, elev_m: 230.12}
  - {yd_from_tee: 70.2, elev_m: 230.38}
  - {yd_from_tee: 75.2, elev_m: 230.58}
  - {yd_from_tee: 80.2, elev_m: 230.85}
  - {yd_from_tee: 85.2, elev_m: 231.07}
  - {yd_from_tee: 90.2, elev_m: 231.27}
  - {yd_from_tee: 95.2, elev_m: 231.51}
  - {yd_from_tee: 100.3, elev_m: 231.58}
  - {yd_from_tee: 105.3, elev_m: 231.7}
  - {yd_from_tee: 110.3, elev_m: 231.9}
  - {yd_from_tee: 115.3, elev_m: 232.13}
  - {yd_from_tee: 120.3, elev_m: 232.29}
  - {yd_from_tee: 125.3, elev_m: 232.43}
  - {yd_from_tee: 130.3, elev_m: 232.55}
  - {yd_from_tee: 135.3, elev_m: 232.63}
  - {yd_from_tee: 140.4, elev_m: 232.77}
  - {yd_from_tee: 145.4, elev_m: 232.89}
  - {yd_from_tee: 150.4, elev_m: 233.06}
  - {yd_from_tee: 155.4, elev_m: 233.21}
  - {yd_from_tee: 160.4, elev_m: 233.43}
  - {yd_from_tee: 165.4, elev_m: 233.67}
  - {yd_from_tee: 170.4, elev_m: 233.82}
  - {yd_from_tee: 175.4, elev_m: 234.01}
  - {yd_from_tee: 180.5, elev_m: 234.18}
  - {yd_from_tee: 185.5, elev_m: 234.42}
  - {yd_from_tee: 190.5, elev_m: 234.66}
  - {yd_from_tee: 195.5, elev_m: 234.87}
  - {yd_from_tee: 200.5, elev_m: 235.12}
  - {yd_from_tee: 205.5, elev_m: 235.34}
  - {yd_from_tee: 210.5, elev_m: 235.61}
  - {yd_from_tee: 215.5, elev_m: 235.96}
  - {yd_from_tee: 220.6, elev_m: 236.27}
  - {yd_from_tee: 225.6, elev_m: 236.63}
  - {yd_from_tee: 230.6, elev_m: 237.0}
  - {yd_from_tee: 235.6, elev_m: 237.71}
  - {yd_from_tee: 240.6, elev_m: 238.28}
  - {yd_from_tee: 245.6, elev_m: 238.15}
  - {yd_from_tee: 250.6, elev_m: 238.2}
  - {yd_from_tee: 255.6, elev_m: 238.25}
```

### Green Slope Data
```json
{
  "mean_elevation_m": 238.29,
  "dominant_slope_deg": 0.5,
  "fall_line_azimuth_deg": 31.9,
  "fall_direction": "NE",
  "sample_count": 570,
  "note": "Slope magnitude derived from 1m DEM \u2014 macro only, not micro-break."
}
```

### Green Elevation Grid
```json
{"origin_latlon":[34.1202039,-118.2938413],"resolution_m":0.914,"rows":28,"cols":33,"null_value":null,"values":[[null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null],[null,null,null,null,null,null,null,null,null,null,null,null,null,238.551,238.534,238.514,238.497,238.487,238.481,238.479,null,null,null,null,null,null,null,null,null,null,null,null,null],[null,null,null,null,null,null,null,null,null,null,null,238.592,238.553,238.523,238.506,238.484,238.469,238.461,238.454,238.448,238.443,null,null,null,null,null,null,null,null,null,null,null,null],[null,null,null,null,null,null,null,null,null,null,238.642,238.585,238.54,238.504,238.474,238.454,238.446,238.443,238.437,238.428,238.419,238.411,null,null,null,null,null,null,null,null,null,null,null],[null,null,null,null,null,null,null,null,238.726,238.68,238.627,238.572,238.527,238.486,238.449,238.43,238.424,238.421,238.415,238.409,238.404,238.394,238.386,null,null,null,null,null,null,null,null,null,null],[null,null,null,null,null,null,null,238.689,238.665,238.629,238.585,238.527,238.477,238.442,238.419,238.408,238.402,238.399,
```
_(truncated for inline display; full grid in `hole_data.json`)_

### Tees (OSM-detected)
```json
[
  {
    "osm_id": 893595870,
    "centroid": {
      "lat": 34.1182968,
      "lng": -118.2926373
    },
    "area_m2": 212.1
  }
]
```

### Bunkers
```json
[
  {
    "osm_id": 893595854,
    "centroid": {
      "lat": 34.120161,
      "lng": -118.2937174
    },
    "area_m2": 61.5
  }
]
```

### Tee Shot Corridor
```yaml
length_yd: 255.6
narrowest_clear_yd: 22.4
median_clear_yd: 58.0
pinch_at_yd: 0.0
max_overhead_m: 0.0
p90_overhead_m: 0.0
```

### Strategy
```yaml
landing_zones: []   # Phase D — not yet authored
approach_zones: []
miss_zones: []
course_memory_rules: []
```

---

## Hole 2 — Par 4, 391 yd (handicap 2)

Par-4 running 407 yd from the back tee. The hole plays 12.9 m uphill tee-to-green. Narrowest fairway corridor is ~24.6 yd at 0.0 yd from tee.

### Scorecard
```yaml
par: 4
handicap: 2
yardages: { black: 391, blue: 376, white: 234 }
```

### Tee
```json
{
  "centroid": {
    "lat": 34.1203977,
    "lng": -118.2932219
  },
  "tee_sets_detected": 1
}
```

### Green
```json
{
  "center": {
    "lat": 34.1210225,
    "lng": -118.289695
  },
  "osm_id": 893595847,
  "area_m2": 497.8,
  "distance_from_tee_yd": 407.1
}
```

### Terrain
```yaml
tee_elevation_m: 240.25
green_elevation_m: 253.17
net_delta_m: 12.92
fairway_centerline_profile_yd5:
  - {yd_from_tee: 0.0, elev_m: 240.25}
  - {yd_from_tee: 5.0, elev_m: 240.26}
  - {yd_from_tee: 9.9, elev_m: 240.27}
  - {yd_from_tee: 14.9, elev_m: 240.28}
  - {yd_from_tee: 19.9, elev_m: 240.39}
  - {yd_from_tee: 24.8, elev_m: 240.53}
  - {yd_from_tee: 29.8, elev_m: 240.82}
  - {yd_from_tee: 34.8, elev_m: 241.14}
  - {yd_from_tee: 39.7, elev_m: 241.44}
  - {yd_from_tee: 44.7, elev_m: 241.75}
  - {yd_from_tee: 49.6, elev_m: 242.05}
  - {yd_from_tee: 54.6, elev_m: 242.31}
  - {yd_from_tee: 59.6, elev_m: 242.57}
  - {yd_from_tee: 64.5, elev_m: 242.88}
  - {yd_from_tee: 69.5, elev_m: 243.16}
  - {yd_from_tee: 74.5, elev_m: 243.42}
  - {yd_from_tee: 79.4, elev_m: 243.68}
  - {yd_from_tee: 84.4, elev_m: 243.95}
  - {yd_from_tee: 89.4, elev_m: 244.25}
  - {yd_from_tee: 94.3, elev_m: 244.52}
  - {yd_from_tee: 99.3, elev_m: 244.78}
  - {yd_from_tee: 104.3, elev_m: 245.02}
  - {yd_from_tee: 109.2, elev_m: 245.28}
  - {yd_from_tee: 114.2, elev_m: 245.39}
  - {yd_from_tee: 119.1, elev_m: 245.57}
  - {yd_from_tee: 124.1, elev_m: 245.79}
  - {yd_from_tee: 129.1, elev_m: 245.96}
  - {yd_from_tee: 134.0, elev_m: 246.15}
  - {yd_from_tee: 139.0, elev_m: 246.34}
  - {yd_from_tee: 144.0, elev_m: 246.53}
  - {yd_from_tee: 148.9, elev_m: 246.72}
  - {yd_from_tee: 153.9, elev_m: 246.93}
  - {yd_from_tee: 158.9, elev_m: 247.14}
  - {yd_from_tee: 163.8, elev_m: 247.36}
  - {yd_from_tee: 168.8, elev_m: 247.57}
  - {yd_from_tee: 173.8, elev_m: 247.81}
  - {yd_from_tee: 178.7, elev_m: 248.03}
  - {yd_from_tee: 183.7, elev_m: 248.22}
  - {yd_from_tee: 188.6, elev_m: 248.43}
  - {yd_from_tee: 193.6, elev_m: 248.68}
  - {yd_from_tee: 198.6, elev_m: 248.96}
  - {yd_from_tee: 203.5, elev_m: 249.17}
  - {yd_from_tee: 208.5, elev_m: 249.34}
  - {yd_from_tee: 213.5, elev_m: 249.49}
  - {yd_from_tee: 218.4, elev_m: 249.58}
  - {yd_from_tee: 223.4, elev_m: 249.67}
  - {yd_from_tee: 228.4, elev_m: 249.71}
  - {yd_from_tee: 233.3, elev_m: 249.76}
  - {yd_from_tee: 238.3, elev_m: 249.83}
  - {yd_from_tee: 243.3, elev_m: 249.9}
  - {yd_from_tee: 248.2, elev_m: 249.94}
  - {yd_from_tee: 253.2, elev_m: 249.99}
  - {yd_from_tee: 258.2, elev_m: 249.99}
  - {yd_from_tee: 263.1, elev_m: 250.06}
  - {yd_from_tee: 268.1, elev_m: 250.06}
  - {yd_from_tee: 273.0, elev_m: 250.07}
  - {yd_from_tee: 278.0, elev_m: 250.11}
  - {yd_from_tee: 283.0, elev_m: 250.1}
  - {yd_from_tee: 287.9, elev_m: 250.07}
  - {yd_from_tee: 292.9, elev_m: 249.86}
  - {yd_from_tee: 297.9, elev_m: 249.68}
  - {yd_from_tee: 302.8, elev_m: 249.52}
  - {yd_from_tee: 307.8, elev_m: 249.45}
  - {yd_from_tee: 312.8, elev_m: 249.39}
  - {yd_from_tee: 317.7, elev_m: 249.37}
  - {yd_from_tee: 322.7, elev_m: 249.32}
  - {yd_from_tee: 327.7, elev_m: 249.31}
  - {yd_from_tee: 332.6, elev_m: 249.22}
  - {yd_from_tee: 337.6, elev_m: 249.23}
  - {yd_from_tee: 342.5, elev_m: 249.32}
  - {yd_from_tee: 347.5, elev_m: 249.45}
  - {yd_from_tee: 352.5, elev_m: 249.7}
  - {yd_from_tee: 357.4, elev_m: 250.12}
  - {yd_from_tee: 362.4, elev_m: 250.57}
  - {yd_from_tee: 367.4, elev_m: 250.91}
  - {yd_from_tee: 372.3, elev_m: 251.2}
  - {yd_from_tee: 377.3, elev_m: 251.58}
  - {yd_from_tee: 382.3, elev_m: 251.96}
  - {yd_from_tee: 387.2, elev_m: 252.42}
  - {yd_from_tee: 392.2, elev_m: 252.86}
  - {yd_from_tee: 397.2, elev_m: 252.97}
  - {yd_from_tee: 402.1, elev_m: 253.02}
  - {yd_from_tee: 407.1, elev_m: 253.17}
```

### Green Slope Data
```json
{
  "mean_elevation_m": 253.14,
  "dominant_slope_deg": 0.75,
  "fall_line_azimuth_deg": 304.1,
  "fall_direction": "NW",
  "sample_count": 601,
  "note": "Slope magnitude derived from 1m DEM \u2014 macro only, not micro-break."
}
```

### Green Elevation Grid
```json
{"origin_latlon":[34.1208886,-118.2898413],"resolution_m":0.914,"rows":29,"cols":30,"null_value":null,"values":[[null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null],[null,null,null,null,null,null,null,null,null,null,null,253.162,253.168,253.178,253.192,253.207,253.227,253.245,253.261,253.279,null,null,null,null,null,null,null,null,null,null],[null,null,null,null,null,null,null,null,253.151,253.134,253.133,253.141,253.154,253.169,253.184,253.199,253.218,253.235,253.254,253.276,253.296,253.312,253.332,null,null,null,null,null,null,null],[null,null,null,null,null,null,253.172,253.133,253.107,253.104,253.112,253.127,253.145,253.16,253.175,253.19,253.207,253.227,253.248,253.268,253.292,253.313,253.331,253.348,null,null,null,null,null,null],[null,null,null,null,null,253.164,253.129,253.095,253.081,253.087,253.101,253.117,253.134,253.152,253.168,253.182,253.201,253.219,253.24,253.264,253.289,253.31,253.331,253.348,253.361,253.373,null,null,null,null],[null,null,null,null,253.139,253.123,253.092,253.069,253.069,253.077,253.089,253.105,253.125,253.145,253.159,253.172,253.193,253.211,253.232,25
```
_(truncated for inline display; full grid in `hole_data.json`)_

### Tees (OSM-detected)
```json
[
  {
    "osm_id": 1151691383,
    "centroid": {
      "lat": 34.1204009,
      "lng": -118.2932472
    },
    "area_m2": 432.8
  }
]
```

### Bunkers
```json
[]
```

### Tee Shot Corridor
```yaml
length_yd: 407.1
narrowest_clear_yd: 24.6
median_clear_yd: 50.9
pinch_at_yd: 0.0
max_overhead_m: 0.0
p90_overhead_m: 0.0
```

### Strategy
```yaml
landing_zones: []   # Phase D — not yet authored
approach_zones: []
miss_zones: []
course_memory_rules: []
```

---

## Hole 3 — Par 3, 155 yd (handicap 9)

Par-3 running 110 yd from the back tee. The hole relatively level tee-to-green. Narrowest fairway corridor is ~19.7 yd at 0.0 yd from tee.

### Scorecard
```yaml
par: 3
handicap: 9
yardages: { black: 155, blue: 132, white: 105 }
```

### Tee
```json
{
  "centroid": {
    "lat": 34.1213926,
    "lng": -118.2898574
  },
  "tee_sets_detected": 1
}
```

### Green
```json
{
  "center": {
    "lat": 34.1219431,
    "lng": -118.2890339
  },
  "osm_id": 893595848,
  "area_m2": 427.2,
  "distance_from_tee_yd": 109.9
}
```

### Terrain
```yaml
tee_elevation_m: 254.29
green_elevation_m: 254.41
net_delta_m: 0.12
fairway_centerline_profile_yd5:
  - {yd_from_tee: 0.0, elev_m: 254.29}
  - {yd_from_tee: 5.0, elev_m: 254.31}
  - {yd_from_tee: 10.0, elev_m: 254.25}
  - {yd_from_tee: 15.0, elev_m: 253.94}
  - {yd_from_tee: 20.0, elev_m: 253.97}
  - {yd_from_tee: 25.0, elev_m: 253.88}
  - {yd_from_tee: 30.0, elev_m: 253.78}
  - {yd_from_tee: 35.0, elev_m: 253.66}
  - {yd_from_tee: 40.0, elev_m: 253.54}
  - {yd_from_tee: 45.0, elev_m: 253.39}
  - {yd_from_tee: 50.0, elev_m: 253.41}
  - {yd_from_tee: 54.9, elev_m: 253.47}
  - {yd_from_tee: 59.9, elev_m: 253.38}
  - {yd_from_tee: 64.9, elev_m: 253.34}
  - {yd_from_tee: 69.9, elev_m: 253.25}
  - {yd_from_tee: 74.9, elev_m: 253.21}
  - {yd_from_tee: 79.9, elev_m: 253.29}
  - {yd_from_tee: 84.9, elev_m: 253.42}
  - {yd_from_tee: 89.9, elev_m: 253.71}
  - {yd_from_tee: 94.9, elev_m: 254.27}
  - {yd_from_tee: 99.9, elev_m: 254.28}
  - {yd_from_tee: 104.9, elev_m: 254.3}
  - {yd_from_tee: 109.9, elev_m: 254.41}
```

### Green Slope Data
```json
{
  "mean_elevation_m": 254.4,
  "dominant_slope_deg": 0.61,
  "fall_line_azimuth_deg": 14.7,
  "fall_direction": "N",
  "sample_count": 515,
  "note": "Slope magnitude derived from 1m DEM \u2014 macro only, not micro-break."
}
```

### Green Elevation Grid
```json
{"origin_latlon":[34.1218346,-118.2891656],"resolution_m":0.914,"rows":26,"cols":29,"null_value":null,"values":[[null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null],[null,null,null,null,null,null,null,null,254.668,254.658,254.644,254.631,254.621,254.621,254.627,254.632,254.636,null,null,null,null,null,null,null,null,null,null,null,null],[null,null,null,null,null,null,null,254.638,254.62,254.608,254.599,254.593,254.591,254.598,254.602,254.603,254.603,254.603,254.61,null,null,null,null,null,null,null,null,null,null],[null,null,null,null,null,254.647,254.622,254.597,254.582,254.578,254.578,254.576,254.577,254.584,254.586,254.585,254.583,254.583,254.586,254.59,null,null,null,null,null,null,null,null,null],[null,null,null,null,254.639,254.617,254.581,254.563,254.558,254.56,254.562,254.563,254.567,254.571,254.57,254.567,254.567,254.572,254.576,254.581,254.589,null,null,null,null,null,null,null,null],[null,null,null,254.612,254.598,254.572,254.544,254.539,254.541,254.544,254.545,254.545,254.55,254.553,254.557,254.56,254.563,254.566,254.569,254.574,254.578,254.582,null,null,null,null,null,null,nul
```
_(truncated for inline display; full grid in `hole_data.json`)_

### Tees (OSM-detected)
```json
[
  {
    "osm_id": 893595872,
    "centroid": {
      "lat": 34.1212775,
      "lng": -118.2900138
    },
    "area_m2": 738.8
  }
]
```

### Bunkers
```json
[
  {
    "osm_id": 893595857,
    "centroid": {
      "lat": 34.1219119,
      "lng": -118.289223
    },
    "area_m2": 77.1
  }
]
```

### Tee Shot Corridor
```yaml
length_yd: 109.9
narrowest_clear_yd: 19.7
median_clear_yd: 41.0
pinch_at_yd: 0.0
max_overhead_m: 0.0
p90_overhead_m: 0.0
```

### Strategy
```yaml
landing_zones: []   # Phase D — not yet authored
approach_zones: []
miss_zones: []
course_memory_rules: []
```

---

## Hole 4 — Par 4, 335 yd (handicap 3)

Par-4 running 335 yd from the back tee. The hole plays 1.2 m uphill tee-to-green. Narrowest fairway corridor is ~1.1 yd at 139.6 yd from tee.

### Scorecard
```yaml
par: 4
handicap: 3
yardages: { black: 335, blue: 308, white: 197 }
```

### Tee
```json
{
  "centroid": {
    "lat": 34.121452,
    "lng": -118.2886129
  },
  "tee_sets_detected": 1
}
```

### Green
```json
{
  "center": {
    "lat": 34.119644,
    "lng": -118.2909985
  },
  "osm_id": 893595850,
  "area_m2": 506.9,
  "distance_from_tee_yd": 334.9
}
```

### Terrain
```yaml
tee_elevation_m: 251.86
green_elevation_m: 253.07
net_delta_m: 1.21
fairway_centerline_profile_yd5:
  - {yd_from_tee: 0.0, elev_m: 251.86}
  - {yd_from_tee: 4.9, elev_m: 251.64}
  - {yd_from_tee: 9.9, elev_m: 250.51}
  - {yd_from_tee: 14.8, elev_m: 250.18}
  - {yd_from_tee: 19.7, elev_m: 250.07}
  - {yd_from_tee: 24.6, elev_m: 249.92}
  - {yd_from_tee: 29.6, elev_m: 249.81}
  - {yd_from_tee: 34.5, elev_m: 249.55}
  - {yd_from_tee: 39.4, elev_m: 249.04}
  - {yd_from_tee: 44.3, elev_m: 248.55}
  - {yd_from_tee: 49.3, elev_m: 248.34}
  - {yd_from_tee: 54.2, elev_m: 248.13}
  - {yd_from_tee: 59.1, elev_m: 247.94}
  - {yd_from_tee: 64.0, elev_m: 247.74}
  - {yd_from_tee: 69.0, elev_m: 247.64}
  - {yd_from_tee: 73.9, elev_m: 247.54}
  - {yd_from_tee: 78.8, elev_m: 247.46}
  - {yd_from_tee: 83.7, elev_m: 247.35}
  - {yd_from_tee: 88.7, elev_m: 247.2}
  - {yd_from_tee: 93.6, elev_m: 247.14}
  - {yd_from_tee: 98.5, elev_m: 247.21}
  - {yd_from_tee: 103.4, elev_m: 247.19}
  - {yd_from_tee: 108.4, elev_m: 247.07}
  - {yd_from_tee: 113.3, elev_m: 247.02}
  - {yd_from_tee: 118.2, elev_m: 247.05}
  - {yd_from_tee: 123.1, elev_m: 246.93}
  - {yd_from_tee: 128.1, elev_m: 246.79}
  - {yd_from_tee: 133.0, elev_m: 246.3}
  - {yd_from_tee: 137.9, elev_m: 245.8}
  - {yd_from_tee: 142.8, elev_m: 245.65}
  - {yd_from_tee: 147.8, elev_m: 245.37}
  - {yd_from_tee: 152.7, elev_m: 245.32}
  - {yd_from_tee: 157.6, elev_m: 245.31}
  - {yd_from_tee: 162.5, elev_m: 245.31}
  - {yd_from_tee: 167.5, elev_m: 245.29}
  - {yd_from_tee: 172.4, elev_m: 245.3}
  - {yd_from_tee: 177.3, elev_m: 245.31}
  - {yd_from_tee: 182.2, elev_m: 245.5}
  - {yd_from_tee: 187.2, elev_m: 245.64}
  - {yd_from_tee: 192.1, elev_m: 245.78}
  - {yd_from_tee: 197.0, elev_m: 245.99}
  - {yd_from_tee: 201.9, elev_m: 246.13}
  - {yd_from_tee: 206.9, elev_m: 246.3}
  - {yd_from_tee: 211.8, elev_m: 246.42}
  - {yd_from_tee: 216.7, elev_m: 246.66}
  - {yd_from_tee: 221.6, elev_m: 246.86}
  - {yd_from_tee: 226.6, elev_m: 247.07}
  - {yd_from_tee: 231.5, elev_m: 247.31}
  - {yd_from_tee: 236.4, elev_m: 247.36}
  - {yd_from_tee: 241.3, elev_m: 247.2}
  - {yd_from_tee: 246.3, elev_m: 248.06}
  - {yd_from_tee: 251.2, elev_m: 248.37}
  - {yd_from_tee: 256.1, elev_m: 248.18}
  - {yd_from_tee: 261.0, elev_m: 248.36}
  - {yd_from_tee: 266.0, elev_m: 248.71}
  - {yd_from_tee: 270.9, elev_m: 248.99}
  - {yd_from_tee: 275.8, elev_m: 249.26}
  - {yd_from_tee: 280.7, elev_m: 249.64}
  - {yd_from_tee: 285.7, elev_m: 249.89}
  - {yd_from_tee: 290.6, elev_m: 250.14}
  - {yd_from_tee: 295.5, elev_m: 250.52}
  - {yd_from_tee: 300.4, elev_m: 250.86}
  - {yd_from_tee: 305.4, elev_m: 251.27}
  - {yd_from_tee: 310.3, elev_m: 251.67}
  - {yd_from_tee: 315.2, elev_m: 252.24}
  - {yd_from_tee: 320.1, elev_m: 252.73}
  - {yd_from_tee: 325.1, elev_m: 252.93}
  - {yd_from_tee: 330.0, elev_m: 253.01}
  - {yd_from_tee: 334.9, elev_m: 253.07}
```

### Green Slope Data
```json
{
  "mean_elevation_m": 253.11,
  "dominant_slope_deg": 0.41,
  "fall_line_azimuth_deg": 93.6,
  "fall_direction": "E",
  "sample_count": 615,
  "note": "Slope magnitude derived from 1m DEM \u2014 macro only, not micro-break."
}
```

### Green Elevation Grid
```json
{"origin_latlon":[34.1195102,-118.2911296],"resolution_m":0.914,"rows":32,"cols":26,"null_value":null,"values":[[null,null,null,null,null,null,null,null,253.215,253.185,253.157,253.132,253.109,253.087,253.073,null,null,null,null,null,null,null,null,null,null,null],[null,null,null,null,null,null,253.248,253.218,253.181,253.145,253.117,253.098,253.078,253.06,253.048,253.043,null,null,null,null,null,null,null,null,null,null],[null,null,null,null,253.278,253.252,253.221,253.184,253.148,253.116,253.095,253.082,253.067,253.056,253.048,253.041,253.037,null,null,null,null,null,null,null,null,null],[null,null,253.285,253.277,253.265,253.233,253.195,253.16,253.132,253.11,253.092,253.08,253.069,253.062,253.055,253.048,253.043,253.039,null,null,null,null,null,null,null,null],[null,null,253.276,253.268,253.245,253.207,253.175,253.152,253.134,253.117,253.099,253.083,253.072,253.064,253.057,253.051,253.045,253.038,253.029,253.02,null,null,null,null,null,null],[null,null,253.275,253.262,253.232,253.19,253.167,253.153,253.142,253.126,253.107,253.091,253.077,253.066,253.057,253.049,253.041,253.034,253.022,253.009,253.001,null,null,null,null,null],[null,null,253.277,253.256,253.218,253.183,253.166,25
```
_(truncated for inline display; full grid in `hole_data.json`)_

### Tees (OSM-detected)
```json
[
  {
    "osm_id": 893595873,
    "centroid": {
      "lat": 34.1214457,
      "lng": -118.288623
    },
    "area_m2": 184.3
  }
]
```

### Bunkers
```json
[
  {
    "osm_id": 893595856,
    "centroid": {
      "lat": 34.1200823,
      "lng": -118.2903098
    },
    "area_m2": 127.2
  }
]
```

### Tee Shot Corridor
```yaml
length_yd: 334.9
narrowest_clear_yd: 1.1
median_clear_yd: 52.5
pinch_at_yd: 139.6
max_overhead_m: 17.5
p90_overhead_m: 0.0
```

### Strategy
```yaml
landing_zones: []   # Phase D — not yet authored
approach_zones: []
miss_zones: []
course_memory_rules: []
```

---

## Hole 5 — Par 4, 344 yd (handicap 4)

Par-4 running 246 yd from the back tee. The hole plays 5.1 m uphill tee-to-green. Narrowest fairway corridor is ~36.1 yd at 240.5 yd from tee.

### Scorecard
```yaml
par: 4
handicap: 4
yardages: { black: 344, blue: 323, white: 264 }
```

### Tee
```json
{
  "centroid": {
    "lat": 34.1194087,
    "lng": -118.2897276
  },
  "tee_sets_detected": 2
}
```

### Green
```json
{
  "center": {
    "lat": 34.1209439,
    "lng": -118.2884784
  },
  "osm_id": 893595849,
  "area_m2": 379.9,
  "distance_from_tee_yd": 246.1
}
```

### Terrain
```yaml
tee_elevation_m: 245.83
green_elevation_m: 250.98
net_delta_m: 5.14
fairway_centerline_profile_yd5:
  - {yd_from_tee: 0.0, elev_m: 245.83}
  - {yd_from_tee: 4.9, elev_m: 244.87}
  - {yd_from_tee: 9.8, elev_m: 244.38}
  - {yd_from_tee: 14.8, elev_m: 243.78}
  - {yd_from_tee: 19.7, elev_m: 243.36}
  - {yd_from_tee: 24.6, elev_m: 242.97}
  - {yd_from_tee: 29.5, elev_m: 242.59}
  - {yd_from_tee: 34.5, elev_m: 242.32}
  - {yd_from_tee: 39.4, elev_m: 242.11}
  - {yd_from_tee: 44.3, elev_m: 241.91}
  - {yd_from_tee: 49.2, elev_m: 242.02}
  - {yd_from_tee: 54.2, elev_m: 242.21}
  - {yd_from_tee: 59.1, elev_m: 242.59}
  - {yd_from_tee: 64.0, elev_m: 242.98}
  - {yd_from_tee: 68.9, elev_m: 243.43}
  - {yd_from_tee: 73.8, elev_m: 243.99}
  - {yd_from_tee: 78.8, elev_m: 244.31}
  - {yd_from_tee: 83.7, elev_m: 244.59}
  - {yd_from_tee: 88.6, elev_m: 244.84}
  - {yd_from_tee: 93.5, elev_m: 245.0}
  - {yd_from_tee: 98.5, elev_m: 245.24}
  - {yd_from_tee: 103.4, elev_m: 245.57}
  - {yd_from_tee: 108.3, elev_m: 245.97}
  - {yd_from_tee: 113.2, elev_m: 246.43}
  - {yd_from_tee: 118.1, elev_m: 246.73}
  - {yd_from_tee: 123.1, elev_m: 246.96}
  - {yd_from_tee: 128.0, elev_m: 247.12}
  - {yd_from_tee: 132.9, elev_m: 247.36}
  - {yd_from_tee: 137.8, elev_m: 247.68}
  - {yd_from_tee: 142.8, elev_m: 248.06}
  - {yd_from_tee: 147.7, elev_m: 248.38}
  - {yd_from_tee: 152.6, elev_m: 248.56}
  - {yd_from_tee: 157.5, elev_m: 248.67}
  - {yd_from_tee: 162.5, elev_m: 248.81}
  - {yd_from_tee: 167.4, elev_m: 248.79}
  - {yd_from_tee: 172.3, elev_m: 248.8}
  - {yd_from_tee: 177.2, elev_m: 248.85}
  - {yd_from_tee: 182.1, elev_m: 248.91}
  - {yd_from_tee: 187.1, elev_m: 249.01}
  - {yd_from_tee: 192.0, elev_m: 249.02}
  - {yd_from_tee: 196.9, elev_m: 249.13}
  - {yd_from_tee: 201.8, elev_m: 249.29}
  - {yd_from_tee: 206.8, elev_m: 249.38}
  - {yd_from_tee: 211.7, elev_m: 249.57}
  - {yd_from_tee: 216.6, elev_m: 249.79}
  - {yd_from_tee: 221.5, elev_m: 249.94}
  - {yd_from_tee: 226.4, elev_m: 250.21}
  - {yd_from_tee: 231.4, elev_m: 250.63}
  - {yd_from_tee: 236.3, elev_m: 250.82}
  - {yd_from_tee: 241.2, elev_m: 250.91}
  - {yd_from_tee: 246.1, elev_m: 250.98}
```

### Green Slope Data
```json
{
  "mean_elevation_m": 251.0,
  "dominant_slope_deg": 0.66,
  "fall_line_azimuth_deg": 338.2,
  "fall_direction": "N",
  "sample_count": 457,
  "note": "Slope magnitude derived from 1m DEM \u2014 macro only, not micro-break."
}
```

### Green Elevation Grid
```json
{"origin_latlon":[34.1208346,-118.28858],"resolution_m":0.914,"rows":30,"cols":25,"null_value":null,"values":[[null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null],[null,null,null,null,251.258,251.254,251.259,251.269,251.282,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null],[null,null,null,251.239,251.225,251.215,251.218,251.229,251.245,251.262,251.279,251.294,251.304,null,null,null,null,null,null,null,null,null,null,null,null],[null,null,null,251.213,251.192,251.184,251.191,251.206,251.224,251.241,251.258,251.268,251.274,251.271,null,null,null,null,null,null,null,null,null,null,null],[null,null,251.194,251.184,251.161,251.162,251.174,251.192,251.21,251.227,251.24,251.25,251.253,251.246,251.232,null,null,null,null,null,null,null,null,null,null],[null,251.16,251.159,251.143,251.136,251.146,251.157,251.171,251.187,251.204,251.216,251.226,251.229,251.224,251.21,251.192,null,null,null,null,null,null,null,null,null],[251.135,251.135,251.125,251.109,251.115,251.128,251.138,251.148,251.159,251.173,251.187,251.197,251.201,251.198,251.186,251.171,251.157,null,null,null,null,null,null,null
```
_(truncated for inline display; full grid in `hole_data.json`)_

### Tees (OSM-detected)
```json
[
  {
    "osm_id": 893595875,
    "centroid": {
      "lat": 34.1194156,
      "lng": -118.289763
    },
    "area_m2": 200.4
  },
  {
    "osm_id": 1211066549,
    "centroid": {
      "lat": 34.1192752,
      "lng": -118.2902024
    },
    "area_m2": 222.5
  }
]
```

### Bunkers
```json
[
  {
    "osm_id": 893595858,
    "centroid": {
      "lat": 34.120188,
      "lng": -118.2886999
    },
    "area_m2": 39.6
  },
  {
    "osm_id": 1211066556,
    "centroid": {
      "lat": 34.1200021,
      "lng": -118.2886167
    },
    "area_m2": 121.2
  }
]
```

### Tee Shot Corridor
```yaml
length_yd: 246.1
narrowest_clear_yd: 36.1
median_clear_yd: 59.3
pinch_at_yd: 240.5
max_overhead_m: 0.0
p90_overhead_m: 0.0
```

### Strategy
```yaml
landing_zones: []   # Phase D — not yet authored
approach_zones: []
miss_zones: []
course_memory_rules: []
```

---

## Hole 6 — Par 4, 315 yd (handicap 5)

Par-4 running 259 yd from the back tee. The hole plays 20.8 m downhill tee-to-green. Narrowest fairway corridor is ~22.4 yd at 33.7 yd from tee.

### Scorecard
```yaml
par: 4
handicap: 5
yardages: { black: 315, blue: 295, white: 225 }
```

### Tee
```json
{
  "centroid": {
    "lat": 34.1209737,
    "lng": -118.288035
  },
  "tee_sets_detected": 2
}
```

### Green
```json
{
  "center": {
    "lat": 34.1190069,
    "lng": -118.2867828
  },
  "osm_id": 893595865,
  "area_m2": 302.6,
  "distance_from_tee_yd": 258.7
}
```

### Terrain
```yaml
tee_elevation_m: 248.16
green_elevation_m: 227.36
net_delta_m: -20.8
fairway_centerline_profile_yd5:
  - {yd_from_tee: 0.0, elev_m: 248.16}
  - {yd_from_tee: 5.0, elev_m: 247.99}
  - {yd_from_tee: 9.9, elev_m: 247.31}
  - {yd_from_tee: 14.9, elev_m: 246.58}
  - {yd_from_tee: 19.9, elev_m: 245.98}
  - {yd_from_tee: 24.9, elev_m: 245.49}
  - {yd_from_tee: 29.8, elev_m: 244.84}
  - {yd_from_tee: 34.8, elev_m: 244.2}
  - {yd_from_tee: 39.8, elev_m: 243.54}
  - {yd_from_tee: 44.8, elev_m: 243.2}
  - {yd_from_tee: 49.7, elev_m: 243.12}
  - {yd_from_tee: 54.7, elev_m: 242.75}
  - {yd_from_tee: 59.7, elev_m: 241.64}
  - {yd_from_tee: 64.7, elev_m: 240.98}
  - {yd_from_tee: 69.6, elev_m: 240.59}
  - {yd_from_tee: 74.6, elev_m: 240.16}
  - {yd_from_tee: 79.6, elev_m: 239.69}
  - {yd_from_tee: 84.6, elev_m: 239.29}
  - {yd_from_tee: 89.5, elev_m: 238.75}
  - {yd_from_tee: 94.5, elev_m: 238.25}
  - {yd_from_tee: 99.5, elev_m: 237.84}
  - {yd_from_tee: 104.5, elev_m: 237.27}
  - {yd_from_tee: 109.4, elev_m: 236.73}
  - {yd_from_tee: 114.4, elev_m: 236.2}
  - {yd_from_tee: 119.4, elev_m: 235.71}
  - {yd_from_tee: 124.4, elev_m: 235.3}
  - {yd_from_tee: 129.3, elev_m: 234.94}
  - {yd_from_tee: 134.3, elev_m: 234.49}
  - {yd_from_tee: 139.3, elev_m: 233.95}
  - {yd_from_tee: 144.3, elev_m: 233.51}
  - {yd_from_tee: 149.2, elev_m: 233.12}
  - {yd_from_tee: 154.2, elev_m: 232.68}
  - {yd_from_tee: 159.2, elev_m: 232.23}
  - {yd_from_tee: 164.2, elev_m: 231.83}
  - {yd_from_tee: 169.1, elev_m: 231.4}
  - {yd_from_tee: 174.1, elev_m: 231.08}
  - {yd_from_tee: 179.1, elev_m: 230.92}
  - {yd_from_tee: 184.1, elev_m: 230.59}
  - {yd_from_tee: 189.0, elev_m: 230.21}
  - {yd_from_tee: 194.0, elev_m: 230.04}
  - {yd_from_tee: 199.0, elev_m: 229.83}
  - {yd_from_tee: 204.0, elev_m: 229.59}
  - {yd_from_tee: 208.9, elev_m: 229.43}
  - {yd_from_tee: 213.9, elev_m: 229.17}
  - {yd_from_tee: 218.9, elev_m: 228.88}
  - {yd_from_tee: 223.9, elev_m: 228.7}
  - {yd_from_tee: 228.8, elev_m: 228.45}
  - {yd_from_tee: 233.8, elev_m: 228.18}
  - {yd_from_tee: 238.8, elev_m: 227.94}
  - {yd_from_tee: 243.7, elev_m: 227.69}
  - {yd_from_tee: 248.7, elev_m: 227.58}
  - {yd_from_tee: 253.7, elev_m: 227.44}
  - {yd_from_tee: 258.7, elev_m: 227.36}
```

### Green Slope Data
```json
{
  "mean_elevation_m": 227.37,
  "dominant_slope_deg": 0.36,
  "fall_line_azimuth_deg": 64.0,
  "fall_direction": "NE",
  "sample_count": 363,
  "note": "Slope magnitude derived from 1m DEM \u2014 macro only, not micro-break."
}
```

### Green Elevation Grid
```json
{"origin_latlon":[34.1188886,-118.2868593],"resolution_m":0.914,"rows":24,"cols":23,"null_value":null,"values":[[null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null],[null,null,null,227.629,227.598,227.562,227.523,227.489,227.463,227.448,227.438,227.426,227.418,227.414,227.411,null,null,null,null,null,null,null,null],[null,null,227.62,227.58,227.532,227.495,227.469,227.45,227.434,227.424,227.414,227.405,227.397,227.389,227.382,227.382,227.387,null,null,null,null,null,null],[null,227.618,227.578,227.53,227.486,227.463,227.448,227.437,227.426,227.416,227.408,227.4,227.391,227.383,227.374,227.369,227.364,227.372,null,null,null,null,null],[null,227.598,227.545,227.495,227.464,227.451,227.44,227.429,227.417,227.408,227.397,227.39,227.383,227.376,227.368,227.36,227.357,227.361,227.368,null,null,null,null],[null,227.58,227.522,227.475,227.456,227.444,227.43,227.416,227.403,227.393,227.384,227.379,227.373,227.366,227.359,227.353,227.352,227.353,227.354,227.356,227.362,null,null],[null,227.565,227.509,227.467,227.45,227.435,227.419,227.404,227.391,227.38,227.373,227.368,227.362,227.356,227.349,227.344,227.341,227.34,227.34,227.3
```
_(truncated for inline display; full grid in `hole_data.json`)_

### Tees (OSM-detected)
```json
[
  {
    "osm_id": 893595878,
    "centroid": {
      "lat": 34.1209849,
      "lng": -118.2880279
    },
    "area_m2": 198.0
  },
  {
    "osm_id": 893595879,
    "centroid": {
      "lat": 34.1205931,
      "lng": -118.287799
    },
    "area_m2": 155.6
  }
]
```

### Bunkers
```json
[]
```

### Tee Shot Corridor
```yaml
length_yd: 258.7
narrowest_clear_yd: 22.4
median_clear_yd: 42.7
pinch_at_yd: 33.7
max_overhead_m: 0.0
p90_overhead_m: 0.0
```

### Strategy
```yaml
landing_zones: []   # Phase D — not yet authored
approach_zones: []
miss_zones: []
course_memory_rules: []
```

---

## Hole 7 — Par 3, 163 yd (handicap 7)

Par-3 running 191 yd from the back tee. The hole plays 6.6 m uphill tee-to-green. Narrowest fairway corridor is ~1.6 yd at 5.8 yd from tee.

### Scorecard
```yaml
par: 3
handicap: 7
yardages: { black: 163, blue: 149, white: 125 }
```

### Tee
```json
{
  "centroid": {
    "lat": 34.1190047,
    "lng": -118.287042
  },
  "tee_sets_detected": 1
}
```

### Green
```json
{
  "center": {
    "lat": 34.1191105,
    "lng": -118.2887607
  },
  "osm_id": 893595867,
  "area_m2": 305.4,
  "distance_from_tee_yd": 191.0
}
```

### Terrain
```yaml
tee_elevation_m: 231.33
green_elevation_m: 237.93
net_delta_m: 6.6
fairway_centerline_profile_yd5:
  - {yd_from_tee: 0.0, elev_m: 231.33}
  - {yd_from_tee: 5.0, elev_m: 232.21}
  - {yd_from_tee: 10.1, elev_m: 233.23}
  - {yd_from_tee: 15.1, elev_m: 233.39}
  - {yd_from_tee: 20.1, elev_m: 233.38}
  - {yd_from_tee: 25.1, elev_m: 233.37}
  - {yd_from_tee: 30.2, elev_m: 233.3}
  - {yd_from_tee: 35.2, elev_m: 233.46}
  - {yd_from_tee: 40.2, elev_m: 233.65}
  - {yd_from_tee: 45.2, elev_m: 233.86}
  - {yd_from_tee: 50.3, elev_m: 234.01}
  - {yd_from_tee: 55.3, elev_m: 234.37}
  - {yd_from_tee: 60.3, elev_m: 234.55}
  - {yd_from_tee: 65.4, elev_m: 234.76}
  - {yd_from_tee: 70.4, elev_m: 235.2}
  - {yd_from_tee: 75.4, elev_m: 235.35}
  - {yd_from_tee: 80.4, elev_m: 235.54}
  - {yd_from_tee: 85.5, elev_m: 235.95}
  - {yd_from_tee: 90.5, elev_m: 235.89}
  - {yd_from_tee: 95.5, elev_m: 235.81}
  - {yd_from_tee: 100.5, elev_m: 236.0}
  - {yd_from_tee: 105.6, elev_m: 235.93}
  - {yd_from_tee: 110.6, elev_m: 235.9}
  - {yd_from_tee: 115.6, elev_m: 235.96}
  - {yd_from_tee: 120.7, elev_m: 236.14}
  - {yd_from_tee: 125.7, elev_m: 236.23}
  - {yd_from_tee: 130.7, elev_m: 236.32}
  - {yd_from_tee: 135.7, elev_m: 236.44}
  - {yd_from_tee: 140.8, elev_m: 236.47}
  - {yd_from_tee: 145.8, elev_m: 236.53}
  - {yd_from_tee: 150.8, elev_m: 236.7}
  - {yd_from_tee: 155.8, elev_m: 237.06}
  - {yd_from_tee: 160.9, elev_m: 237.46}
  - {yd_from_tee: 165.9, elev_m: 237.65}
  - {yd_from_tee: 170.9, elev_m: 237.72}
  - {yd_from_tee: 176.0, elev_m: 237.76}
  - {yd_from_tee: 181.0, elev_m: 237.83}
  - {yd_from_tee: 186.0, elev_m: 237.9}
  - {yd_from_tee: 191.0, elev_m: 237.93}
```

### Green Slope Data
```json
{
  "mean_elevation_m": 237.93,
  "dominant_slope_deg": 0.44,
  "fall_line_azimuth_deg": 63.2,
  "fall_direction": "NE",
  "sample_count": 371,
  "note": "Slope magnitude derived from 1m DEM \u2014 macro only, not micro-break."
}
```

### Green Elevation Grid
```json
{"origin_latlon":[34.1190328,-118.2888953],"resolution_m":0.914,"rows":18,"cols":31,"null_value":null,"values":[[null,null,null,null,null,null,null,null,null,null,null,238.041,238.031,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null],[null,null,null,null,null,null,null,null,238.039,238.04,238.035,238.025,238.005,237.988,237.977,237.966,237.955,237.945,null,null,null,null,null,null,null,null,null,null,null,null,null],[null,null,null,null,238.03,238.022,238.017,238.019,238.018,238.014,238.007,237.996,237.979,237.969,237.959,237.95,237.94,237.928,237.916,237.904,237.9,237.899,null,null,null,null,null,null,null,null,null],[null,238.079,238.059,238.039,238.024,238.015,238.008,238.008,238.006,238.002,237.996,237.985,237.973,237.963,237.953,237.944,237.934,237.925,237.912,237.902,237.896,237.89,237.885,237.887,237.892,null,null,null,null,null,null],[238.12,238.087,238.058,238.037,238.025,238.019,238.013,238.01,238.003,237.997,237.99,237.978,237.968,237.957,237.949,237.941,237.933,237.925,237.914,237.907,237.903,237.899,237.895,237.89,237.885,237.88,null,null,null,null,null],[238.118,238.08,238.054,238.04,238.033,238.028,238.018,238.007,237.997,237.
```
_(truncated for inline display; full grid in `hole_data.json`)_

### Tees (OSM-detected)
```json
[
  {
    "osm_id": 893595877,
    "centroid": {
      "lat": 34.1190012,
      "lng": -118.2870507
    },
    "area_m2": 177.2
  }
]
```

### Bunkers
```json
[
  {
    "osm_id": 1211066551,
    "centroid": {
      "lat": 34.1191781,
      "lng": -118.2882814
    },
    "area_m2": 133.1
  },
  {
    "osm_id": 1211066552,
    "centroid": {
      "lat": 34.1190499,
      "lng": -118.2885121
    },
    "area_m2": 116.7
  }
]
```

### Tee Shot Corridor
```yaml
length_yd: 191.0
narrowest_clear_yd: 1.6
median_clear_yd: 47.6
pinch_at_yd: 5.8
max_overhead_m: 20.4
p90_overhead_m: 0.0
```

### Strategy
```yaml
landing_zones: []   # Phase D — not yet authored
approach_zones: []
miss_zones: []
course_memory_rules: []
```

---

## Hole 8 — Par 4, 351 yd (handicap 1)

Par-4 running 330 yd from the back tee. The hole plays 2.6 m uphill tee-to-green. Narrowest fairway corridor is ~17.5 yd at 33.6 yd from tee.

### Scorecard
```yaml
par: 4
handicap: 1
yardages: { black: 351, blue: 330, white: 173 }
```

### Tee
```json
{
  "centroid": {
    "lat": 34.118883,
    "lng": -118.2890832
  },
  "tee_sets_detected": 1
}
```

### Green
```json
{
  "center": {
    "lat": 34.1194745,
    "lng": -118.2917331
  },
  "osm_id": 893595851,
  "area_m2": 352.9,
  "distance_from_tee_yd": 330.0
}
```

### Terrain
```yaml
tee_elevation_m: 238.89
green_elevation_m: 241.47
net_delta_m: 2.58
fairway_centerline_profile_yd5:
  - {yd_from_tee: 0.0, elev_m: 238.89}
  - {yd_from_tee: 4.9, elev_m: 238.86}
  - {yd_from_tee: 9.9, elev_m: 238.85}
  - {yd_from_tee: 14.8, elev_m: 238.84}
  - {yd_from_tee: 19.7, elev_m: 238.82}
  - {yd_from_tee: 24.6, elev_m: 238.87}
  - {yd_from_tee: 29.6, elev_m: 238.89}
  - {yd_from_tee: 34.5, elev_m: 238.89}
  - {yd_from_tee: 39.4, elev_m: 238.91}
  - {yd_from_tee: 44.3, elev_m: 238.92}
  - {yd_from_tee: 49.3, elev_m: 238.94}
  - {yd_from_tee: 54.2, elev_m: 239.0}
  - {yd_from_tee: 59.1, elev_m: 239.05}
  - {yd_from_tee: 64.0, elev_m: 238.98}
  - {yd_from_tee: 69.0, elev_m: 238.89}
  - {yd_from_tee: 73.9, elev_m: 238.91}
  - {yd_from_tee: 78.8, elev_m: 239.05}
  - {yd_from_tee: 83.7, elev_m: 239.15}
  - {yd_from_tee: 88.7, elev_m: 239.31}
  - {yd_from_tee: 93.6, elev_m: 239.46}
  - {yd_from_tee: 98.5, elev_m: 239.59}
  - {yd_from_tee: 103.4, elev_m: 239.72}
  - {yd_from_tee: 108.4, elev_m: 239.92}
  - {yd_from_tee: 113.3, elev_m: 240.06}
  - {yd_from_tee: 118.2, elev_m: 240.37}
  - {yd_from_tee: 123.1, elev_m: 240.76}
  - {yd_from_tee: 128.1, elev_m: 241.21}
  - {yd_from_tee: 133.0, elev_m: 241.57}
  - {yd_from_tee: 137.9, elev_m: 241.95}
  - {yd_from_tee: 142.9, elev_m: 242.41}
  - {yd_from_tee: 147.8, elev_m: 242.91}
  - {yd_from_tee: 152.7, elev_m: 243.29}
  - {yd_from_tee: 157.6, elev_m: 243.55}
  - {yd_from_tee: 162.6, elev_m: 243.71}
  - {yd_from_tee: 167.5, elev_m: 243.82}
  - {yd_from_tee: 172.4, elev_m: 243.71}
  - {yd_from_tee: 177.3, elev_m: 243.61}
  - {yd_from_tee: 182.3, elev_m: 243.54}
  - {yd_from_tee: 187.2, elev_m: 243.51}
  - {yd_from_tee: 192.1, elev_m: 243.58}
  - {yd_from_tee: 197.0, elev_m: 243.64}
  - {yd_from_tee: 202.0, elev_m: 243.73}
  - {yd_from_tee: 206.9, elev_m: 243.81}
  - {yd_from_tee: 211.8, elev_m: 244.03}
  - {yd_from_tee: 216.7, elev_m: 244.14}
  - {yd_from_tee: 221.7, elev_m: 244.31}
  - {yd_from_tee: 226.6, elev_m: 244.37}
  - {yd_from_tee: 231.5, elev_m: 244.38}
  - {yd_from_tee: 236.4, elev_m: 244.29}
  - {yd_from_tee: 241.4, elev_m: 244.3}
  - {yd_from_tee: 246.3, elev_m: 244.22}
  - {yd_from_tee: 251.2, elev_m: 244.06}
  - {yd_from_tee: 256.2, elev_m: 243.87}
  - {yd_from_tee: 261.1, elev_m: 243.62}
  - {yd_from_tee: 266.0, elev_m: 243.4}
  - {yd_from_tee: 270.9, elev_m: 242.96}
  - {yd_from_tee: 275.9, elev_m: 242.39}
  - {yd_from_tee: 280.8, elev_m: 241.75}
  - {yd_from_tee: 285.7, elev_m: 241.29}
  - {yd_from_tee: 290.6, elev_m: 241.05}
  - {yd_from_tee: 295.6, elev_m: 240.92}
  - {yd_from_tee: 300.5, elev_m: 240.94}
  - {yd_from_tee: 305.4, elev_m: 241.08}
  - {yd_from_tee: 310.3, elev_m: 241.22}
  - {yd_from_tee: 315.3, elev_m: 241.31}
  - {yd_from_tee: 320.2, elev_m: 241.38}
  - {yd_from_tee: 325.1, elev_m: 241.42}
  - {yd_from_tee: 330.0, elev_m: 241.47}
```

### Green Slope Data
```json
{
  "mean_elevation_m": 241.45,
  "dominant_slope_deg": 0.35,
  "fall_line_azimuth_deg": 325.0,
  "fall_direction": "NW",
  "sample_count": 425,
  "note": "Slope magnitude derived from 1m DEM \u2014 macro only, not micro-break."
}
```

### Green Elevation Grid
```json
{"origin_latlon":[34.1193571,-118.2918593],"resolution_m":0.914,"rows":29,"cols":26,"null_value":null,"values":[[null,null,null,null,null,null,null,null,241.569,241.579,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null],[null,null,null,null,null,241.492,241.512,241.523,241.53,241.535,241.545,241.561,241.58,null,null,null,null,null,null,null,null,null,null,null,null,null],[null,null,null,241.43,241.458,241.471,241.477,241.485,241.495,241.508,241.521,241.536,241.553,241.57,null,null,null,null,null,null,null,null,null,null,null,null],[null,null,241.385,241.424,241.441,241.445,241.449,241.463,241.481,241.498,241.511,241.522,241.535,241.549,241.564,null,null,null,null,null,null,null,null,null,null,null],[null,null,241.384,241.41,241.418,241.424,241.437,241.454,241.474,241.491,241.502,241.507,241.51,241.524,241.544,241.561,null,null,null,null,null,null,null,null,null,null],[null,241.326,241.376,241.396,241.404,241.414,241.431,241.45,241.468,241.485,241.495,241.494,241.487,241.509,241.533,241.549,null,null,null,null,null,null,null,null,null,null],[null,241.318,241.365,241.387,241.401,241.414,241.429,241.448,241.465,241.482,241.494,241.497,241.495,241.518,241.
```
_(truncated for inline display; full grid in `hole_data.json`)_

### Tees (OSM-detected)
```json
[
  {
    "osm_id": 1151695800,
    "centroid": {
      "lat": 34.1188866,
      "lng": -118.2890739
    },
    "area_m2": 526.0
  }
]
```

### Bunkers
```json
[
  {
    "osm_id": 893595855,
    "centroid": {
      "lat": 34.1193049,
      "lng": -118.2916631
    },
    "area_m2": 72.9
  },
  {
    "osm_id": 1211066554,
    "centroid": {
      "lat": 34.1187471,
      "lng": -118.2914311
    },
    "area_m2": 107.8
  },
  {
    "osm_id": 1211066555,
    "centroid": {
      "lat": 34.1194276,
      "lng": -118.2915391
    },
    "area_m2": 97.2
  }
]
```

### Tee Shot Corridor
```yaml
length_yd: 330.0
narrowest_clear_yd: 17.5
median_clear_yd: 44.3
pinch_at_yd: 33.6
max_overhead_m: 0.0
p90_overhead_m: 0.0
```

### Strategy
```yaml
landing_zones: []   # Phase D — not yet authored
approach_zones: []
miss_zones: []
course_memory_rules: []
```

---

## Hole 9 — Par 3, 167 yd (handicap 8)

Par-3 running 151 yd from the back tee. The hole plays 11.2 m downhill tee-to-green. Narrowest fairway corridor is ~25.2 yd at 63.9 yd from tee.

### Scorecard
```yaml
par: 3
handicap: 8
yardages: { black: 167, blue: 147, white: 126 }
```

### Tee
```json
{
  "centroid": {
    "lat": 34.1196341,
    "lng": -118.2921444
  },
  "tee_sets_detected": 1
}
```

### Green
```json
{
  "center": {
    "lat": 34.1182734,
    "lng": -118.2921256
  },
  "osm_id": 893595852,
  "area_m2": 365.2,
  "distance_from_tee_yd": 151.0
}
```

### Terrain
```yaml
tee_elevation_m: 238.47
green_elevation_m: 227.29
net_delta_m: -11.18
fairway_centerline_profile_yd5:
  - {yd_from_tee: 0.0, elev_m: 238.47}
  - {yd_from_tee: 5.0, elev_m: 238.43}
  - {yd_from_tee: 10.1, elev_m: 238.2}
  - {yd_from_tee: 15.1, elev_m: 238.24}
  - {yd_from_tee: 20.1, elev_m: 238.2}
  - {yd_from_tee: 25.2, elev_m: 237.56}
  - {yd_from_tee: 30.2, elev_m: 236.61}
  - {yd_from_tee: 35.2, elev_m: 236.26}
  - {yd_from_tee: 40.3, elev_m: 235.81}
  - {yd_from_tee: 45.3, elev_m: 234.5}
  - {yd_from_tee: 50.3, elev_m: 233.91}
  - {yd_from_tee: 55.4, elev_m: 233.52}
  - {yd_from_tee: 60.4, elev_m: 233.17}
  - {yd_from_tee: 65.4, elev_m: 232.83}
  - {yd_from_tee: 70.5, elev_m: 232.46}
  - {yd_from_tee: 75.5, elev_m: 232.06}
  - {yd_from_tee: 80.5, elev_m: 231.64}
  - {yd_from_tee: 85.6, elev_m: 231.23}
  - {yd_from_tee: 90.6, elev_m: 230.84}
  - {yd_from_tee: 95.6, elev_m: 230.43}
  - {yd_from_tee: 100.7, elev_m: 230.01}
  - {yd_from_tee: 105.7, elev_m: 229.6}
  - {yd_from_tee: 110.7, elev_m: 229.11}
  - {yd_from_tee: 115.7, elev_m: 228.73}
  - {yd_from_tee: 120.8, elev_m: 228.53}
  - {yd_from_tee: 125.8, elev_m: 227.93}
  - {yd_from_tee: 130.8, elev_m: 227.44}
  - {yd_from_tee: 135.9, elev_m: 227.44}
  - {yd_from_tee: 140.9, elev_m: 227.32}
  - {yd_from_tee: 145.9, elev_m: 227.31}
  - {yd_from_tee: 151.0, elev_m: 227.29}
```

### Green Slope Data
```json
{
  "mean_elevation_m": 227.29,
  "dominant_slope_deg": 0.16,
  "fall_line_azimuth_deg": 27.8,
  "fall_direction": "NE",
  "sample_count": 440,
  "note": "Slope magnitude derived from 1m DEM \u2014 macro only, not micro-break."
}
```

### Green Elevation Grid
```json
{"origin_latlon":[34.1181679,-118.2922467],"resolution_m":0.914,"rows":24,"cols":27,"null_value":null,"values":[[null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null],[null,null,null,null,null,null,null,null,null,null,227.37,227.349,227.335,227.33,227.327,227.324,227.318,null,null,null,null,null,null,null,null,null,null],[null,null,null,null,null,null,null,227.386,227.353,227.335,227.325,227.322,227.32,227.32,227.321,227.321,227.321,227.32,227.315,null,null,null,null,null,null,null,null],[null,null,null,null,null,227.39,227.354,227.332,227.322,227.32,227.32,227.32,227.322,227.323,227.324,227.325,227.325,227.325,227.32,227.317,null,null,null,null,null,null,null],[null,null,null,null,227.363,227.331,227.317,227.315,227.319,227.322,227.322,227.322,227.323,227.322,227.322,227.324,227.326,227.327,227.323,227.318,227.312,null,null,null,null,null,null],[null,null,null,227.354,227.315,227.305,227.305,227.312,227.318,227.32,227.318,227.318,227.318,227.318,227.317,227.319,227.321,227.323,227.322,227.316,227.308,227.3,null,null,null,null,null],[null,null,227.348,227.311,227.292,227.296,227.302,227.309,227.314,22
```
_(truncated for inline display; full grid in `hole_data.json`)_

### Tees (OSM-detected)
```json
[
  {
    "osm_id": 893595874,
    "centroid": {
      "lat": 34.1194825,
      "lng": -118.292157
    },
    "area_m2": 653.2
  }
]
```

### Bunkers
```json
[]
```

### Tee Shot Corridor
```yaml
length_yd: 151.0
narrowest_clear_yd: 25.2
median_clear_yd: 35.3
pinch_at_yd: 63.9
max_overhead_m: 0.0
p90_overhead_m: 0.0
```

### Strategy
```yaml
landing_zones: []   # Phase D — not yet authored
approach_zones: []
miss_zones: []
course_memory_rules: []
```

---

