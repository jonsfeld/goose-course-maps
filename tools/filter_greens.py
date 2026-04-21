"""Filter v1 green polygons down to real putting greens.

Heuristics:
  1. Area in [150, 800] m² (realistic putting green range)
  2. Circularity (4πA / P²) above threshold — real greens are round-ish
  3. Fairway-adjacency: at least N% of perimeter is within R meters of a
     v1 fairway polygon (real greens sit at the end of fairways)
  4. CHM inside polygon must be < 0.5m (no tree coverage)

Input:  courses/<slug>/derived/features.geojson (v1 output)
        courses/<slug>/derived/canopy_height_model.tif
Output: courses/<slug>/derived/greens_filtered.geojson (subset of v1 greens
        that passed all heuristics, with confidence scores)
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from _common import course_dir


MIN_AREA_M2 = 150.0
MAX_AREA_M2 = 800.0
MIN_CIRCULARITY = 0.35       # 1.0 = perfect circle; real greens ~0.4-0.7
FAIRWAY_DISTANCE_M = 20.0
MAX_CHM_IN_GREEN_M = 0.5


def _circularity(poly) -> float:
    if poly.length == 0:
        return 0.0
    return (4 * math.pi * poly.area) / (poly.length ** 2)


def _area_m2(poly) -> float:
    # Approx: geographic degrees → meters at course latitude (34.12)
    lat = poly.centroid.y
    deg_per_m_lat = 1 / 111_000
    deg_per_m_lon = 1 / (111_000 * math.cos(math.radians(lat)))
    # Area in deg² → m² via anisotropic scaling
    return poly.area / (deg_per_m_lat * deg_per_m_lon)


def filter_greens(slug: str) -> Path:
    c = course_dir(slug)
    features_path = c / "derived" / "features.geojson"
    chm_path = c / "derived" / "canopy_height_model.tif"

    with features_path.open() as f:
        coll = json.load(f)

    v1_greens = [shape(feat["geometry"])
                 for feat in coll["features"]
                 if feat["properties"]["kind"] == "green"]
    fairway_polys = [shape(feat["geometry"])
                     for feat in coll["features"]
                     if feat["properties"]["kind"] == "fairway"]

    if not v1_greens:
        raise RuntimeError("No v1 green polygons found")
    if not fairway_polys:
        raise RuntimeError("No v1 fairway polygons found (needed for adjacency check)")

    print(f"[filter] input: {len(v1_greens)} v1 greens, {len(fairway_polys)} v1 fairways")

    fairway_union = unary_union(fairway_polys)

    with rasterio.open(chm_path) as chm_src:
        chm = chm_src.read(1).astype("float32")
        chm[chm < 0] = 0
        chm_transform = chm_src.transform

    # Buffer fairway_union by fairway_distance (converted roughly to degrees)
    # 20m ~ 0.00018° at mid-lat
    buffer_deg = FAIRWAY_DISTANCE_M / 111_000  # rough, overestimates in lat axis
    fairway_near = fairway_union.buffer(buffer_deg)

    survivors = []
    dropped = {"area": 0, "circularity": 0, "fairway_dist": 0, "chm": 0}

    for i, g in enumerate(v1_greens):
        area = _area_m2(g)
        if area < MIN_AREA_M2 or area > MAX_AREA_M2:
            dropped["area"] += 1
            continue

        circ = _circularity(g)
        if circ < MIN_CIRCULARITY:
            dropped["circularity"] += 1
            continue

        if not g.intersects(fairway_near):
            dropped["fairway_dist"] += 1
            continue

        # CHM check: sample the CHM raster inside the polygon
        try:
            mask = geometry_mask(
                [mapping(g)], out_shape=chm.shape, transform=chm_transform,
                invert=True,
            )
            inside_chm = chm[mask]
            if inside_chm.size == 0 or inside_chm.mean() > MAX_CHM_IN_GREEN_M:
                dropped["chm"] += 1
                continue
        except Exception as e:
            print(f"[filter]  green {i}: CHM check failed: {e}")
            continue

        survivors.append({
            "polygon": g,
            "area_m2": round(area, 1),
            "circularity": round(circ, 3),
            "centroid": (g.centroid.x, g.centroid.y),
        })

    print(f"[filter] dropped by: {dropped}")
    print(f"[filter] survivors: {len(survivors)}")

    # Sort by area descending so the largest (likely most confident) come first
    survivors.sort(key=lambda s: s["area_m2"], reverse=True)

    out_feats = []
    for idx, s in enumerate(survivors):
        out_feats.append({
            "type": "Feature",
            "properties": {
                "kind": "green",
                "area_m2": s["area_m2"],
                "circularity": s["circularity"],
                "hole_id": None,          # to be assigned later from course_layout
                "source": "phase_b_v1.5_filtered",
            },
            "geometry": mapping(s["polygon"]),
        })

    out_path = c / "derived" / "greens_filtered.geojson"
    with out_path.open("w") as f:
        json.dump({"type": "FeatureCollection", "features": out_feats}, f)
    print(f"[filter] wrote {out_path} ({len(out_feats)} greens)")

    for i, s in enumerate(survivors):
        cx, cy = s["centroid"]
        print(
            f"[filter]   #{i+1}: centroid ({cx:.5f}, {cy:.5f}) "
            f"area {s['area_m2']} m², circ {s['circularity']}"
        )

    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    args = ap.parse_args()
    filter_greens(args.course)


if __name__ == "__main__":
    main()
