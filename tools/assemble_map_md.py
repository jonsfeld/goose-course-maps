"""Assemble map.auto.md for a course.

Inputs:
  courses/<slug>/notes/scorecard.md          (human-readable; parsed for tee sets)
  courses/<slug>/notes/architect_lookup.md   (optional metadata)
  courses/<slug>/notes/data_sources.md       (optional provenance)
  courses/<slug>/notes/bbox.geojson          (location)
  courses/<slug>/derived/features_osm.geojson (polygons)
  courses/<slug>/derived/hole_data.json       (per-hole intelligence)

Output:
  courses/<slug>/map.auto.md
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from _common import course_dir


# --------------------------------------------------------------------------
# Scorecard parser — lightweight; just extract what we need
# --------------------------------------------------------------------------

def _parse_scorecard(path: Path) -> dict:
    """Parse scorecard.md for tee sets + per-hole handicap + yardages."""
    out = {"tee_sets": [], "holes": []}
    if not path.exists():
        return out
    text = path.read_text()

    # Find tee set table (| Tee | Par | Total yards | ... |)
    lines = text.splitlines()
    in_tees = False
    in_holes = False
    for i, line in enumerate(lines):
        ls = line.strip()
        if ls.startswith("| Tee") and "Total yards" in ls:
            in_tees = True; continue
        if in_tees:
            if ls.startswith("|---"):
                continue
            if not ls.startswith("|") or ls.startswith("|**") or ls == "":
                in_tees = False
                continue
            parts = [p.strip() for p in ls.strip("|").split("|")]
            if len(parts) < 7:
                in_tees = False
                continue
            try:
                name = parts[0].lower()
                out["tee_sets"].append({
                    "name": name,
                    "par": int(parts[1]),
                    "total_yards": int(parts[2].replace(",", "")),
                    "rating_mens": float(parts[3]),
                    "slope_mens": int(parts[4]),
                    "rating_womens": float(parts[5]),
                    "slope_womens": int(parts[6]),
                })
            except (ValueError, IndexError):
                in_tees = False

        if ls.startswith("| Hole") and "HCP" in ls:
            in_holes = True; continue
        if in_holes:
            if ls.startswith("|---"):
                continue
            if not ls.startswith("|") or ls.startswith("| **Total"):
                in_holes = False; continue
            parts = [p.strip() for p in ls.strip("|").split("|")]
            if len(parts) < 6:
                in_holes = False; continue
            try:
                out["holes"].append({
                    "hole": int(parts[0]),
                    "par": int(parts[1]),
                    "handicap": int(parts[2]),
                    "yardages": {
                        "black": int(parts[3]),
                        "blue": int(parts[4]),
                        "white": int(parts[5]),
                    },
                })
            except (ValueError, IndexError):
                in_holes = False
    return out


# --------------------------------------------------------------------------
# Assembler
# --------------------------------------------------------------------------

def assemble(slug: str) -> Path:
    c = course_dir(slug)
    scorecard = _parse_scorecard(c / "notes" / "scorecard.md")
    with (c / "derived" / "hole_data.json").open() as f:
        hole_data = json.load(f)
    with (c / "derived" / "features_osm.geojson").open() as f:
        osm_feats = json.load(f)["features"]
    with (c / "notes" / "bbox.geojson").open() as f:
        bbox_geo = json.load(f)

    course_name_feat = next((f for f in osm_feats if f["properties"]["kind"] == "course_boundary"), None)
    course_name = (course_name_feat or {}).get("properties", {}).get("course_name") or "Roosevelt Golf Course"

    # Compute course centroid from bbox
    ring = bbox_geo["features"][0]["geometry"]["coordinates"][0]
    xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
    c_lat = sum(ys) / len(ys); c_lon = sum(xs) / len(xs)

    total_par = sum(h["par"] for h in hole_data["holes"])

    # ------------------ frontmatter ------------------
    tee_sets_yaml = ""
    for ts in scorecard.get("tee_sets", []):
        tee_sets_yaml += (
            f"\n  - name: {ts['name']}\n"
            f"    par: {ts['par']}\n"
            f"    total_yards: {ts['total_yards']}\n"
            f"    rating_mens: {ts['rating_mens']}\n"
            f"    slope_mens: {ts['slope_mens']}\n"
            f"    rating_womens: {ts['rating_womens']}\n"
            f"    slope_womens: {ts['slope_womens']}"
        )

    scorecard_yaml = ""
    for h in scorecard.get("holes", []):
        scorecard_yaml += (
            f"\n  - hole: {h['hole']}\n"
            f"    par: {h['par']}\n"
            f"    handicap: {h['handicap']}\n"
            f"    yardages: {{ black: {h['yardages']['black']}, "
            f"blue: {h['yardages']['blue']}, white: {h['yardages']['white']} }}"
        )

    fm = f"""---
course: {course_name}
alt_names: [Roosevelt Municipal Golf Course, Roosevelt GC, Vermont Canyon]
slug: {slug}
location:
  lat: {round(c_lat, 5)}
  lon: {round(c_lon, 5)}
  address: "2650 N Vermont Ave, Los Angeles, CA 90027"
  region: "Griffith Park, Los Angeles, CA"
par: {total_par}
holes: {len(hole_data['holes'])}
architect: unknown (probable: John Ward with Billy Bell Jr., 1964; not primary-source verified)
opened: 1964
renovated: 2019
renovation_architect: Forrest Richardson (ASGCA)
grass:
  tee: unknown
  fairway: bermuda
  rough: unknown
  green: bentgrass
tee_sets:{tee_sets_yaml}
scorecard:{scorecard_yaml}
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

# {course_name} — Overview

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
"""

    # ------------------ per-hole sections ------------------
    per_hole_md = ""
    sc_by_hole = {h["hole"]: h for h in scorecard.get("holes", [])}

    for h in hole_data["holes"]:
        hn = h["hole"]
        par = h["par"]
        sc = sc_by_hole.get(hn, {})
        yds = sc.get("yardages", {})
        default_yds = yds.get("black") or yds.get("blue") or yds.get("white") or "?"

        line = h["hole_line"]
        terrain = h["terrain"]
        green = h["green"]
        slope = green.get("slope_analysis") or {}
        corridor = h["tee_shot_corridor"]

        # Narrative: plain summary from the data (no LLM prose)
        net = terrain["net_delta_m"]
        elev_phrase = (
            f"plays {abs(net):.1f} m downhill tee-to-green"
            if net is not None and net < -1
            else f"plays {abs(net):.1f} m uphill tee-to-green"
            if net is not None and net > 1
            else "relatively level tee-to-green"
        )
        shape_phrase = ""
        if corridor.get("narrowest_clear_yd") is not None:
            shape_phrase = (
                f" Narrowest fairway corridor is ~{corridor['narrowest_clear_yd']} yd "
                f"at {corridor.get('pinch_at_yd', '?')} yd from tee."
            )

        per_hole_md += f"""## Hole {hn} — Par {par}, {default_yds} yd (handicap {sc.get('handicap', '?')})

Par-{par} running {corridor['length_yd']:.0f} yd from the back tee. The hole {elev_phrase}.{shape_phrase}

### Scorecard
```yaml
par: {par}
handicap: {sc.get('handicap', 'null')}
yardages: {{ black: {yds.get('black', 'null')}, blue: {yds.get('blue', 'null')}, white: {yds.get('white', 'null')} }}
```

### Tee
```json
{json.dumps({"centroid": line["tee"], "tee_sets_detected": len(h["tees"])}, indent=2)}
```

### Green
```json
{json.dumps({
    "center": line["green_center"],
    "osm_id": green.get("osm_id"),
    "area_m2": green.get("area_m2"),
    "distance_from_tee_yd": corridor["length_yd"],
}, indent=2)}
```

### Terrain
```yaml
tee_elevation_m: {terrain["tee_elevation_m"]}
green_elevation_m: {terrain["green_elevation_m"]}
net_delta_m: {terrain["net_delta_m"]}
fairway_centerline_profile_yd5:
{chr(10).join(f"  - {{yd_from_tee: {p['yd_from_tee']}, elev_m: {p['elev_m']}}}" for p in terrain["fairway_centerline_profile"])}
```

### Green Slope Data
```json
{json.dumps({
    "mean_elevation_m": slope.get("mean_elevation_m"),
    "dominant_slope_deg": slope.get("dominant_slope_deg"),
    "fall_line_azimuth_deg": slope.get("fall_line_azimuth_deg"),
    "fall_direction": slope.get("fall_direction"),
    "sample_count": slope.get("sample_count"),
    "note": "Slope magnitude derived from 1m DEM — macro only, not micro-break.",
}, indent=2)}
```

### Green Elevation Grid
```json
{json.dumps(slope.get("grid", {}), separators=(",", ":"))[:1200]}
```
_(truncated for inline display; full grid in `hole_data.json`)_

### Tees (OSM-detected)
```json
{json.dumps(h["tees"], indent=2)}
```

### Bunkers
```json
{json.dumps(h["bunkers"], indent=2)}
```

### Tee Shot Corridor
```yaml
length_yd: {corridor["length_yd"]}
narrowest_clear_yd: {corridor.get("narrowest_clear_yd")}
median_clear_yd: {corridor.get("median_clear_yd")}
pinch_at_yd: {corridor.get("pinch_at_yd")}
max_overhead_m: {corridor["max_overhead_m"]}
p90_overhead_m: {corridor.get("p90_overhead_m")}
```

### Strategy
```yaml
landing_zones: []   # Phase D — not yet authored
approach_zones: []
miss_zones: []
course_memory_rules: []
```

---

"""

    out = c / "map.auto.md"
    out.write_text(fm + per_hole_md)
    print(f"[assemble] wrote {out} ({out.stat().st_size/1024:.1f} KB)")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    args = ap.parse_args()
    assemble(args.course)


if __name__ == "__main__":
    main()
