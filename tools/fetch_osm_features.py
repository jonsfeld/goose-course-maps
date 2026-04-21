"""Fetch golf course features from OpenStreetMap via Overpass API.

OSM uses a well-established taxonomy for golf features:
  - leisure=golf_course        → course boundary
  - golf=green                 → putting green (polygon)
  - golf=fairway               → fairway (polygon)
  - golf=bunker                → sand trap (polygon)
  - golf=tee                   → tee box (polygon)
  - golf=hole                  → hole line with ref=<N>, par=<int>
  - golf=rough                 → rough (polygon)
  - golf=water_hazard          → water (polygon)
  - golf=out_of_bounds         → OB (polygon/line)

For courses present in OSM, this is the fastest + most accurate source of
2D geometry. LiDAR-derived rasters (slope, CHM, etc.) overlay on top for
the terrain-intelligence layer.

Usage:
    python3 fetch_osm_features.py --course roosevelt_la

Reads bbox from courses/<slug>/notes/bbox.geojson.
Writes:
    courses/<slug>/sources/osm_features.json    (raw Overpass response)
    courses/<slug>/derived/features_osm.geojson (our schema-compatible output)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests

from _common import bbox_from_course, course_dir, ensure_dir


OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Mapping OSM tag → our schema kind
OSM_TAG_TO_KIND = {
    "green":        "green",
    "fairway":      "fairway",
    "bunker":       "bunker",
    "tee":          "tee_box",
    "rough":        "rough",
    "water_hazard": "water",
    "out_of_bounds": "out_of_bounds",
    "hole":         "hole_line",
    "cartpath":     "cart_path",
    "path":         "cart_path",
    "driving_range": "driving_range",
    "clubhouse":    "clubhouse",
}


def _ring_from_way(way_geometry):
    """OSM way 'geometry' is list of {lat, lon} dicts → [[lon,lat], ...]."""
    return [[float(n["lon"]), float(n["lat"])] for n in way_geometry]


def _polygon_from_way(way) -> list:
    ring = _ring_from_way(way["geometry"])
    if ring and ring[0] != ring[-1]:
        ring.append(ring[0])
    return [ring]


def _polygon_from_relation(rel) -> list:
    """Combine relation member ways into a single outer ring where possible.
    Real OSM multipolygon relations can have multiple outer/inner rings; this
    simplification keeps the largest outer ring.
    """
    outers = [m for m in rel.get("members", []) if m.get("role") in ("outer", "") and "geometry" in m]
    if not outers:
        return []
    # Pick the biggest member by node count as the primary outer
    biggest = max(outers, key=lambda m: len(m["geometry"]))
    ring = _ring_from_way(biggest["geometry"])
    if ring and ring[0] != ring[-1]:
        ring.append(ring[0])
    return [ring]


def convert(slug: str) -> Path:
    c = course_dir(slug)
    bbox = bbox_from_course(slug)
    minx, miny, maxx, maxy = bbox

    query = f"""
[out:json][timeout:30];
(
  way["golf"]({miny},{minx},{maxy},{maxx});
  relation["golf"]({miny},{minx},{maxy},{maxx});
  way["leisure"="golf_course"]({miny},{minx},{maxy},{maxx});
  relation["leisure"="golf_course"]({miny},{minx},{maxy},{maxx});
);
out geom;
"""
    print(f"[osm] querying Overpass for bbox ({minx:.5f},{miny:.5f})-({maxx:.5f},{maxy:.5f})")
    r = requests.get(
        OVERPASS_URL,
        params={"data": query},
        timeout=60,
        headers={"User-Agent": "goose-course-maps/0.1"},
    )
    r.raise_for_status()
    raw = r.json()
    print(f"[osm] got {len(raw.get('elements', []))} elements")

    src_dir = ensure_dir(c / "sources")
    raw_path = src_dir / "osm_features.json"
    with raw_path.open("w") as f:
        json.dump(raw, f)

    feats = []
    hole_meta = []   # holes are polylines with par + ref
    for el in raw["elements"]:
        tags = el.get("tags", {})
        golf_tag = tags.get("golf")
        leisure_tag = tags.get("leisure")

        if golf_tag == "hole":
            # Line geometry — tee-to-green route. Preserve metadata.
            if el["type"] == "way" and "geometry" in el:
                line = _ring_from_way(el["geometry"])
                hole_meta.append({
                    "type": "Feature",
                    "properties": {
                        "kind": "hole_line",
                        "hole_ref": tags.get("ref"),
                        "par": int(tags["par"]) if tags.get("par", "").isdigit() else None,
                        "distance": tags.get("distance"),
                        "handicap": tags.get("handicap"),
                    },
                    "geometry": {"type": "LineString", "coordinates": line},
                })
            continue

        if leisure_tag == "golf_course":
            kind = "course_boundary"
        elif golf_tag in OSM_TAG_TO_KIND:
            kind = OSM_TAG_TO_KIND[golf_tag]
        else:
            continue  # skip anything else

        # Build geometry
        if el["type"] == "way" and "geometry" in el:
            coords = _polygon_from_way(el)
            geom = {"type": "Polygon", "coordinates": coords}
        elif el["type"] == "relation":
            coords = _polygon_from_relation(el)
            if not coords:
                continue
            geom = {"type": "Polygon", "coordinates": coords}
        else:
            continue

        props = {
            "kind": kind,
            "osm_id": el["id"],
            "osm_type": el["type"],
            "name": tags.get("name"),
        }
        # Bunker severity / surface
        if golf_tag == "bunker":
            props["surface"] = tags.get("surface")
        # Course-level name
        if kind == "course_boundary":
            props["course_name"] = tags.get("name")

        feats.append({
            "type": "Feature",
            "properties": props,
            "geometry": geom,
        })

    feats.extend(hole_meta)

    out_path = ensure_dir(c / "derived") / "features_osm.geojson"
    with out_path.open("w") as f:
        json.dump({"type": "FeatureCollection", "features": feats}, f)

    # Quick summary
    counts = {}
    for ft in feats:
        k = ft["properties"]["kind"]
        counts[k] = counts.get(k, 0) + 1
    print(f"[osm] feature counts: {counts}")
    print(f"[osm] wrote {out_path} ({len(feats)} features)")
    print(f"[osm] raw OSM saved to {raw_path}")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    args = ap.parse_args()
    convert(args.course)


if __name__ == "__main__":
    main()
