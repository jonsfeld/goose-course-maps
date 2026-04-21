"""Pick 9 greens from v1 classifier output using user seed centroids.

For each seed:
  1. If seed falls inside a v1 `green` or `fairway` polygon, that's the candidate
  2. Otherwise, find the nearest green/fairway polygon within SEARCH_RADIUS_M
  3. Keep polygons that plausibly look like greens:
     - area in [80, 1500] m² (loose — v1 greens can be irregular)
     - prefer 'green' classification over 'fairway'
  4. Deduplicate — if two seeds hit the same polygon, split or keep the bigger half

Output: courses/<slug>/derived/greens_picked.geojson  (exactly 9 green polygons,
        each tagged with centroid_id from seed)
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from shapely.geometry import Point, mapping, shape
from shapely.strtree import STRtree

from _common import course_dir


SEARCH_RADIUS_M = 120.0     # generous — user seeds were approximate
MIN_AREA_M2 = 60
MAX_AREA_M2 = 2500


def _area_m2(poly) -> float:
    lat = poly.centroid.y
    deg_per_m_lat = 1 / 111_000
    deg_per_m_lon = 1 / (111_000 * math.cos(math.radians(lat)))
    return poly.area / (deg_per_m_lat * deg_per_m_lon)


def _dist_m(a: Point, b) -> float:
    """Approximate distance in meters between a point and a shapely geom."""
    lat = (a.y + b.centroid.y) / 2
    deg_per_m_lat = 1 / 111_000
    deg_per_m_lon = 1 / (111_000 * math.cos(math.radians(lat)))
    d = a.distance(b)  # in degrees
    # Rough mean degrees-per-meter
    return d / ((deg_per_m_lat + deg_per_m_lon) / 2)


def pick(slug: str) -> Path:
    c = course_dir(slug)
    v1_path = c / "derived" / "features.geojson"
    seeds_path = c / "notes" / "green_centroids_draft.geojson"

    with v1_path.open() as f:
        v1 = json.load(f)["features"]
    with seeds_path.open() as f:
        seeds = json.load(f)["features"]

    # Candidate pool: all v1 greens + fairways within area bounds
    candidates = []
    for feat in v1:
        kind = feat["properties"]["kind"]
        if kind not in ("green", "fairway"):
            continue
        poly = shape(feat["geometry"])
        area = _area_m2(poly)
        if area < MIN_AREA_M2 or area > MAX_AREA_M2:
            continue
        candidates.append({
            "poly": poly,
            "kind": kind,
            "area_m2": area,
        })
    print(f"[pick] {len(candidates)} candidate polygons (v1 green + fairway in area range)")

    # Build STRtree for fast spatial lookups
    polys = [c_["poly"] for c_ in candidates]
    tree = STRtree(polys)

    used_ids = set()  # dedupe if two seeds hit same polygon (by id(poly))
    picked = []
    for seed in seeds:
        cid = seed["properties"].get("centroid_id") or seed["properties"].get("hole")
        lon, lat = seed["geometry"]["coordinates"]
        pt = Point(lon, lat)

        # Find candidates within search radius. Use the longer axis
        # (longitude at 34° needs cos(34) correction) to be safe.
        buffer_deg = SEARCH_RADIUS_M / (111_000 * math.cos(math.radians(lat)))
        query_area = pt.buffer(buffer_deg)
        nearby_idx = tree.query(query_area)
        nearby = [(i, candidates[i]) for i in nearby_idx.tolist()]

        if not nearby:
            print(f"[pick] seed #{cid}: no candidate within {SEARCH_RADIUS_M}m")
            continue

        # Score: prefer polygons containing the seed, then kind=green, then closest
        def score(item):
            idx, cand = item
            contains = cand["poly"].contains(pt)
            kind_bonus = 1 if cand["kind"] == "green" else 0
            dist_m = _dist_m(pt, cand["poly"])
            return (-int(contains), -kind_bonus, dist_m)

        nearby.sort(key=score)
        chosen_idx, chosen = nearby[0]
        if chosen_idx in used_ids:
            # Find next best unused
            found = False
            for idx, cand in nearby[1:]:
                if idx not in used_ids:
                    chosen_idx, chosen = idx, cand
                    found = True
                    break
            if not found:
                print(f"[pick] seed #{cid}: all nearby already used — skipping")
                continue

        used_ids.add(chosen_idx)
        picked.append({
            "centroid_id": cid,
            "poly": chosen["poly"],
            "kind_source": chosen["kind"],      # green or fairway
            "area_m2": chosen["area_m2"],
            "contains_seed": chosen["poly"].contains(pt),
            "dist_to_seed_m": _dist_m(pt, chosen["poly"]) if not chosen["poly"].contains(pt) else 0,
        })
        if chosen["poly"].contains(pt):
            where = "contains seed"
        else:
            where = f"{_dist_m(pt, chosen['poly']):.0f}m from seed"
        print(
            f"[pick] seed #{cid}: {chosen['kind']} polygon "
            f"area {chosen['area_m2']:.0f} m², {where}"
        )

    out_feats = []
    for p in picked:
        out_feats.append({
            "type": "Feature",
            "properties": {
                "centroid_id": p["centroid_id"],
                "provisional_hole": None,
                "kind": "green",
                "kind_source": p["kind_source"],
                "area_m2": round(p["area_m2"], 1),
                "dist_to_seed_m": round(p["dist_to_seed_m"], 1),
                "contains_seed": p["contains_seed"],
                "source": "phase_b_v1.5_picked_from_v1",
            },
            "geometry": mapping(p["poly"]),
        })

    out_path = c / "derived" / "greens_picked.geojson"
    with out_path.open("w") as f:
        json.dump({"type": "FeatureCollection", "features": out_feats}, f)
    print(f"[pick] wrote {out_path} with {len(out_feats)} greens")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    args = ap.parse_args()
    pick(args.course)


if __name__ == "__main__":
    main()
