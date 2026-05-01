"""Package everything into a single JSON payload matching Goose's
Supabase `courses` table shape so it can be inserted via the Supabase
dashboard / SQL editor / JS client.

Reads:
  courses/<slug>/derived/features_osm.geojson   (2D polygons, OSM-sourced)
  courses/<slug>/derived/hole_data.json          (per-hole terrain + slope + corridor)
  courses/<slug>/notes/scorecard.md              (tee sets, handicaps)
  courses/<slug>/notes/bbox.geojson              (course location / bounds)
  courses/<slug>/derived/canopy_polygons.geojson (tree canopy — optional)
  courses/<slug>/derived/individual_trees.geojson (tree points — optional)

Writes:
  courses/<slug>/goose_payload.json      (single JSON, ready for upsert)
  courses/<slug>/goose_upsert.sql         (SQL INSERT statement)

Goose Supabase `courses` table columns populated:
  - name              : course name (string)
  - holes             : hole count (int)
  - location          : {lat, lng, address, region}
  - hole_data         : array of per-hole objects with Goose-native keys
                        (tee, green_center, green_perimeter, hole_shape,
                         fairway_polygon, bunkers, water_hazards, out_of_bounds)
  - green_slope_data  : per-hole slope zones / direction / fall-line
  - terrain_data      : per-hole elevation profile + green 0.5m grid
  - vector_data       : raw OSM feature collection (for rendering / debugging)
  - course_intelligence: scorecard, tee sets, tee shot corridors, data sources,
                         confidence notes, tree canopy stats
  - mapping_source    : "manual:auto" (our pipeline tag)
  - igolf_id          : null (we're not using iGolf)

Unused for v0:
  - water_hazards[]   : empty (Roosevelt has none)
  - out_of_bounds[]   : empty (OSM didn't tag any for this course)
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import math

from shapely.geometry import LineString, mapping, shape
from shapely.ops import transform as shp_transform

from _common import course_dir


MAPPING_SOURCE = "manual:auto"

# When OSM has no fairway polygon for a hole (typical for par-3 — OSM
# convention is to omit fairway on holes that don't have one separate
# from tee→green), synthesize a buffered corridor from the hole_line so
# downstream `in_fairway` checks and landing-zone generators have
# something usable. Tagged with `synthesized: true` for provenance.
SYNTHETIC_FAIRWAY_BUFFER_M = 18.0   # ~20 yd each side of centerline


def _synthesize_fairway_corridor(hole_line_points: list[dict]) -> list[dict]:
    """Buffer the hole_line by SYNTHETIC_FAIRWAY_BUFFER_M to produce a
    fairway-shaped polygon. Returns Goose-native [{lat,lng}] ring."""
    if len(hole_line_points) < 2:
        return []
    coords = [(p["lng"], p["lat"]) for p in hole_line_points]
    line = LineString(coords)
    # Convert buffer from meters → degrees at this latitude
    lat_center = sum(p["lat"] for p in hole_line_points) / len(hole_line_points)
    deg_per_m_lat = 1 / 111_000
    deg_per_m_lon = 1 / (111_000 * math.cos(math.radians(lat_center)))
    # Use the average so the buffer is roughly isotropic in meters
    buffer_deg = SYNTHETIC_FAIRWAY_BUFFER_M * (deg_per_m_lat + deg_per_m_lon) / 2
    poly = line.buffer(buffer_deg, cap_style=2, join_style=2)  # flat caps, mitered joins
    if poly.is_empty:
        return []
    if poly.geom_type == "MultiPolygon":
        poly = max(poly.geoms, key=lambda p: p.area)
    ring = list(poly.exterior.coords)
    return [{"lat": round(y, 7), "lng": round(x, 7)} for x, y in ring]
PAYLOAD_VERSION = "0.1"


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _polygon_to_goose_ring(geom) -> list[dict]:
    """Convert a shapely Polygon/MultiPolygon exterior to Goose's [{lat,lng}]."""
    poly = shape(geom) if isinstance(geom, dict) else geom
    if poly.geom_type == "Polygon":
        ring = list(poly.exterior.coords)
    elif poly.geom_type == "MultiPolygon":
        # Pick the largest component
        biggest = max(poly.geoms, key=lambda p: p.area)
        ring = list(biggest.exterior.coords)
    else:
        return []
    return [{"lat": round(y, 7), "lng": round(x, 7)} for x, y in ring]


def _linestring_to_goose_points(geom) -> list[dict]:
    line = shape(geom)
    return [{"lat": round(y, 7), "lng": round(x, 7)} for x, y in line.coords]


def _parse_scorecard(path: Path) -> dict:
    """Replicate the parser from assemble_map_md.py."""
    out = {"tee_sets": [], "holes": []}
    if not path.exists():
        return out
    lines = path.read_text().splitlines()
    in_tees = False
    in_holes = False
    for line in lines:
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
                out["tee_sets"].append({
                    "name": parts[0].lower(),
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
# Feature collection helpers
# --------------------------------------------------------------------------

def _features_by_hole(osm_feats: list, hole_refs: dict) -> dict:
    """Map OSM features to their closest hole (by nearest-line in degrees).
    Returns {hole_ref: {"greens": [...], "tees": [...], "bunkers": [...], "fairways": [...]}}.
    """
    assigned = {ref: {"greens": [], "tees": [], "bunkers": [], "fairways": []} for ref in hole_refs}
    for feat in osm_feats:
        kind = feat["properties"]["kind"]
        if kind in ("hole_line", "course_boundary"):
            continue
        if "geometry" not in feat:
            continue
        poly = shape(feat["geometry"])
        best_ref, best_dist = None, float("inf")
        for ref, hole_line in hole_refs.items():
            d = poly.distance(hole_line)
            if d < best_dist:
                best_dist, best_ref = d, ref
        if best_ref is None:
            continue
        bucket = {"green": "greens", "tee_box": "tees", "bunker": "bunkers",
                  "fairway": "fairways"}.get(kind)
        if bucket:
            assigned[best_ref][bucket].append(feat)
    return assigned


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------

def build(slug: str, name_suffix: str = "", upsert: bool = False) -> tuple[Path, Path]:
    c = course_dir(slug)
    osm_path = c / "derived" / "features_osm.geojson"
    hole_data_path = c / "derived" / "hole_data.json"
    sc_path = c / "notes" / "scorecard.md"
    bbox_path = c / "notes" / "bbox.geojson"

    with osm_path.open() as f:
        osm = json.load(f)
    osm_feats = osm["features"]

    with hole_data_path.open() as f:
        hd = json.load(f)

    scorecard = _parse_scorecard(sc_path)

    with bbox_path.open() as f:
        bbox = json.load(f)
    ring = bbox["features"][0]["geometry"]["coordinates"][0]
    xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
    c_lat = sum(ys) / len(ys); c_lon = sum(xs) / len(xs)

    # Hole_lines indexed by ref
    hole_refs = {}
    for feat in osm_feats:
        if feat["properties"]["kind"] == "hole_line":
            ref = feat["properties"].get("hole_ref")
            if ref:
                hole_refs[str(ref)] = shape(feat["geometry"])

    assigned = _features_by_hole(osm_feats, hole_refs)

    sc_by_hole = {h["hole"]: h for h in scorecard.get("holes", [])}
    hd_by_hole = {h["hole"]: h for h in hd["holes"]}

    # --------------- hole_data array ---------------
    hole_data_list = []
    green_slope_by_hole = {}
    terrain_by_hole = {}

    for ref_str, hole_line in sorted(hole_refs.items(), key=lambda x: int(x[0])):
        hole_num = int(ref_str)
        hr = hd_by_hole.get(hole_num, {})
        sc = sc_by_hole.get(hole_num, {})
        group = assigned.get(ref_str, {"greens": [], "tees": [], "bunkers": [], "fairways": []})

        # Greens → use largest as the hole's green
        green_feat = None
        if group["greens"]:
            green_feat = max(group["greens"], key=lambda f: shape(f["geometry"]).area)

        # Bunkers → centroid + polygon
        bunkers = []
        for b in group["bunkers"]:
            poly = shape(b["geometry"])
            bunkers.append({
                "osm_id": b["properties"]["osm_id"],
                "centroid": {"lat": round(poly.centroid.y, 7), "lng": round(poly.centroid.x, 7)},
                "perimeter": _polygon_to_goose_ring(poly),
                "context": "unknown",   # greenside vs fairway — not resolved yet
            })

        # Fairway → take largest polygon. If OSM has none (typical for par-3),
        # synthesize from hole_line as a fallback corridor for runtime checks.
        fairway_ring: list = []
        fairway_synthesized = False
        if group["fairways"]:
            biggest_fw = max(group["fairways"], key=lambda f: shape(f["geometry"]).area)
            fairway_ring = _polygon_to_goose_ring(biggest_fw["geometry"])
        if not fairway_ring:
            hole_line_pts = _linestring_to_goose_points(hole_line)
            fairway_ring = _synthesize_fairway_corridor(hole_line_pts)
            fairway_synthesized = bool(fairway_ring)

        # Tee positions (OSM polygons → centroid)
        tee_centroid = hr.get("hole_line", {}).get("tee") or {}
        tee_positions_per_set = []
        for tp in group["tees"]:
            tp_poly = shape(tp["geometry"])
            tee_positions_per_set.append({
                "osm_id": tp["properties"]["osm_id"],
                "centroid": {"lat": round(tp_poly.centroid.y, 7), "lng": round(tp_poly.centroid.x, 7)},
            })

        hole_obj = {
            "hole": hole_num,
            "par": hr.get("par") or sc.get("par"),
            "handicap": sc.get("handicap"),
            "yardages": sc.get("yardages", {}),
            "tee": tee_centroid,                                   # default (= back) tee position
            "green_center": hr.get("hole_line", {}).get("green_center") or {},
            "green_perimeter": _polygon_to_goose_ring(green_feat["geometry"]) if green_feat else [],
            "hole_shape": _linestring_to_goose_points(hole_line),
            "fairway_polygon": fairway_ring,
            "fairway_polygon_provenance": (
                "synthesized_from_hole_line" if fairway_synthesized else "osm"
            ),
            "bunkers": bunkers,
            "water_hazards": [],
            "out_of_bounds": [],
            "tee_positions_detected": tee_positions_per_set,
        }
        hole_data_list.append(hole_obj)

        # green_slope_data per hole
        slope = (hr.get("green") or {}).get("slope_analysis") or {}
        if slope.get("ok"):
            green_slope_by_hole[str(hole_num)] = {
                "dominant_slope_deg": slope.get("dominant_slope_deg"),
                "fall_line_azimuth_deg": slope.get("fall_line_azimuth_deg"),
                "fall_direction": slope.get("fall_direction"),
                "mean_elevation_m": slope.get("mean_elevation_m"),
                "sample_count": slope.get("sample_count"),
                "zones": {},                    # not yet modeled
                "best_miss": None,              # future Phase D
                "false_front": None,
                "note": "Macro slope from 1m DEM; no micro-break model.",
            }

        # terrain_data per hole
        terr = hr.get("terrain") or {}
        terrain_by_hole[str(hole_num)] = {
            "tee_elevation_m": terr.get("tee_elevation_m"),
            "green_elevation_m": terr.get("green_elevation_m"),
            "net_delta_m": terr.get("net_delta_m"),
            "fairway_centerline_profile": terr.get("fairway_centerline_profile"),
            "green_elevation_grid": slope.get("grid"),
        }

    # --------------- course-level blocks ---------------
    course_intelligence = {
        "scorecard": scorecard,
        "tee_shot_corridors": {str(h["hole"]): h.get("tee_shot_corridor") for h in hd["holes"]},
        "data_sources": {
            "dem": {"source": "USGS_3DEP_1m", "dataset": "CA_LosAngeles_B23",
                    "vintage": "2025-08-11", "collection": "2023-01 to 2024-01"},
            "point_cloud": {"source": "USGS_LPC", "dataset": "CA_LosAngeles_1_B23",
                            "vintage": "2025-06-13", "density_pts_per_m2": 18.8},
            "imagery": {"source": "USGS_NAIP_ImageServer", "vintage": "2025-01-09"},
            "features_2d": {"source": "OpenStreetMap", "api": "Overpass",
                            "vintage": "2026-04-21", "license": "ODbL"},
        },
        "confidence_notes": {
            "terrain_vertical_m": 0.10,
            "terrain_horizontal_m": 1.0,
            "green_slope_resolution": "macro only (1m DEM); no micro-break",
            "geometry_source_accuracy_m": "OSM community; may be several meters off true boundary",
        },
        "pipeline": "manual:auto",
        "payload_version": PAYLOAD_VERSION,
    }

    vector_data = {
        "feature_collection": osm,
        "source": "OpenStreetMap (Overpass API)",
        "vintage": "2026-04-21",
    }

    base_name = (next((f["properties"].get("course_name") for f in osm_feats
                       if f["properties"]["kind"] == "course_boundary"), None)
                 or "Roosevelt Golf Course")
    full_name = f"{base_name}{(' ' + name_suffix) if name_suffix else ''}"
    payload = {
        "name": full_name,
        "slug": slug,
        "holes": len(hole_data_list),
        "location": {
            "lat": round(c_lat, 5), "lng": round(c_lon, 5),
            "address": "2650 N Vermont Ave, Los Angeles, CA 90027",
            "region": "Griffith Park, Los Angeles, CA",
        },
        "mapping_source": MAPPING_SOURCE,
        "igolf_id": None,
        "hole_data": hole_data_list,
        "green_slope_data": green_slope_by_hole,
        "terrain_data": terrain_by_hole,
        "vector_data": vector_data,
        "course_intelligence": course_intelligence,
    }

    out_json = c / "goose_payload.json"
    out_json.write_text(json.dumps(payload, indent=2, allow_nan=False))

    # SQL — plain INSERT by default (matches Goose's current courses schema:
    # no `updated_at` column and no UNIQUE constraint on `name`).
    # Pass --upsert to emit ON CONFLICT (name) DO UPDATE if your schema later
    # adds those affordances. Default is plain INSERT to avoid round-trips
    # with Lovable / Supabase about missing schema features.
    def _esc(s: str) -> str:
        return s.replace("'", "''")

    base_values = f"""INSERT INTO courses (
  name, holes, location, hole_data, green_slope_data, terrain_data,
  vector_data, course_intelligence, mapping_source, igolf_id
)
VALUES (
  '{_esc(payload['name'])}',
  {payload['holes']},
  '{_esc(json.dumps(payload['location']))}'::jsonb,
  '{_esc(json.dumps(payload['hole_data']))}'::jsonb,
  '{_esc(json.dumps(payload['green_slope_data']))}'::jsonb,
  '{_esc(json.dumps(payload['terrain_data']))}'::jsonb,
  '{_esc(json.dumps(payload['vector_data']))}'::jsonb,
  '{_esc(json.dumps(payload['course_intelligence']))}'::jsonb,
  '{_esc(payload['mapping_source'])}',
  NULL
)"""

    if upsert:
        sql = f"""-- Goose course upsert — {payload['name']}
-- Generated {PAYLOAD_VERSION} by build_goose_payload.py (--upsert mode)
-- Requires UNIQUE(name) constraint and updated_at column on courses table.

{base_values}
ON CONFLICT (name) DO UPDATE SET
  holes = EXCLUDED.holes,
  location = EXCLUDED.location,
  hole_data = EXCLUDED.hole_data,
  green_slope_data = EXCLUDED.green_slope_data,
  terrain_data = EXCLUDED.terrain_data,
  vector_data = EXCLUDED.vector_data,
  course_intelligence = EXCLUDED.course_intelligence,
  mapping_source = EXCLUDED.mapping_source,
  updated_at = now();
"""
    else:
        sql = f"""-- Goose course insert — {payload['name']}
-- Generated {PAYLOAD_VERSION} by build_goose_payload.py (plain INSERT mode)
-- Use --upsert flag to emit ON CONFLICT clause if your schema has UNIQUE(name).

{base_values};
"""

    out_sql = c / "goose_upsert.sql"
    out_sql.write_text(sql)

    size_json_kb = out_json.stat().st_size / 1024
    size_sql_kb = out_sql.stat().st_size / 1024
    print(f"[goose-payload] wrote {out_json} ({size_json_kb:.1f} KB)")
    print(f"[goose-payload] wrote {out_sql}  ({size_sql_kb:.1f} KB)")

    return out_json, out_sql


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    ap.add_argument(
        "--name-suffix", default="",
        help='Appended to course name, e.g. "(LiDAR-OSM)" for side-by-side variance test',
    )
    ap.add_argument(
        "--upsert", action="store_true",
        help="Emit ON CONFLICT (name) DO UPDATE clause (requires UNIQUE(name) + updated_at).",
    )
    args = ap.parse_args()
    build(args.course, args.name_suffix, args.upsert)


if __name__ == "__main__":
    main()
