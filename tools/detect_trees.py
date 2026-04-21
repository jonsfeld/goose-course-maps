"""Detect individual trees + build canopy polygons from a Canopy Height Model.

Inputs:  courses/<slug>/derived/canopy_height_model.tif
Outputs:
  courses/<slug>/derived/individual_trees.geojson  (per-tree points with height + canopy radius)
  courses/<slug>/derived/canopy_polygons.geojson   (disjoint canopy polygons with height distribution)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio import features
from scipy.ndimage import label, maximum_filter
from shapely.geometry import mapping, shape

from _common import course_dir, ensure_dir


CANOPY_MIN_HEIGHT_M = 2.0          # cells below this are non-canopy
LOCAL_MAX_WINDOW_M = 4.0           # min separation between trunk peaks
MIN_POLYGON_AREA_M2 = 15.0         # drop tiny canopy blobs (noise)


def detect(slug: str) -> tuple[Path, Path]:
    derived = ensure_dir(course_dir(slug) / "derived")
    chm_path = derived / "canopy_height_model.tif"
    if not chm_path.exists():
        raise FileNotFoundError(f"{chm_path} not found; run build_chm.py first")

    with rasterio.open(chm_path) as src:
        chm = src.read(1).astype("float32")
        transform = src.transform
        cellsize_m = _cellsize_m(src)

    print(f"[trees] CHM {chm.shape}, cellsize ~{cellsize_m:.3f} m")

    # --- Canopy polygons with height distribution stats ---
    canopy_mask = (chm >= CANOPY_MIN_HEIGHT_M).astype("uint8")
    shapes = features.shapes(canopy_mask, mask=canopy_mask.astype(bool), transform=transform)

    canopy_features = []
    for geom, _val in shapes:
        poly = shape(geom)
        area_m2 = poly.area * (111_000 ** 2)  # degrees^2 → m^2 approx
        if area_m2 < MIN_POLYGON_AREA_M2:
            continue

        # Sample CHM cells inside this polygon for height stats.
        poly_mask = features.geometry_mask(
            [geom], out_shape=chm.shape, transform=transform, invert=True
        )
        heights = chm[poly_mask & (chm >= CANOPY_MIN_HEIGHT_M)]
        if heights.size == 0:
            continue

        canopy_features.append({
            "type": "Feature",
            "properties": {
                "kind": "tree_canopy",
                "min_height_m": float(np.min(heights)),
                "p50_height_m": float(np.percentile(heights, 50)),
                "p90_height_m": float(np.percentile(heights, 90)),
                "max_height_m": float(np.max(heights)),
                "area_m2": round(area_m2, 1),
            },
            "geometry": mapping(poly),
        })

    canopy_path = derived / "canopy_polygons.geojson"
    with canopy_path.open("w") as f:
        json.dump({"type": "FeatureCollection", "features": canopy_features}, f)
    print(f"[trees] wrote {canopy_path} ({len(canopy_features)} polygons)")

    # --- Individual trees via local-maxima on the CHM ---
    window_px = max(3, int(LOCAL_MAX_WINDOW_M / cellsize_m))
    if window_px % 2 == 0:
        window_px += 1
    print(f"[trees] local-max window {window_px}px (~{window_px * cellsize_m:.1f} m)")

    local_max = maximum_filter(chm, size=window_px)
    peaks = (chm == local_max) & (chm >= CANOPY_MIN_HEIGHT_M)
    ys, xs = np.nonzero(peaks)

    tree_features = []
    for y, x in zip(ys, xs):
        height = float(chm[y, x])
        lon, lat = rasterio.transform.xy(transform, y, x)
        # Canopy radius estimate: grow outward while CHM stays within 60% of peak height.
        radius_m = _canopy_radius(chm, y, x, height, cellsize_m)
        tree_features.append({
            "type": "Feature",
            "properties": {
                "kind": "tree",
                "height_m": round(height, 2),
                "canopy_radius_m": round(radius_m, 2),
            },
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
        })

    trees_path = derived / "individual_trees.geojson"
    with trees_path.open("w") as f:
        json.dump({"type": "FeatureCollection", "features": tree_features}, f)
    print(f"[trees] wrote {trees_path} ({len(tree_features)} trees)")

    return canopy_path, trees_path


def _cellsize_m(src) -> float:
    import math
    lat = src.bounds.top - (src.bounds.top - src.bounds.bottom) / 2
    px_x_m = abs(src.transform.a) * 111_000 * math.cos(math.radians(lat))
    px_y_m = abs(src.transform.e) * 111_000
    return (px_x_m + px_y_m) / 2.0


def _canopy_radius(chm: np.ndarray, y: int, x: int, peak: float, cellsize_m: float) -> float:
    """Grow outward from peak until CHM drops below 0.6 * peak. Max 10 m."""
    max_steps = max(3, int(10.0 / cellsize_m))
    threshold = 0.6 * peak
    for r in range(1, max_steps):
        y0, y1 = max(0, y - r), min(chm.shape[0], y + r + 1)
        x0, x1 = max(0, x - r), min(chm.shape[1], x + r + 1)
        ring = chm[y0:y1, x0:x1]
        if ring.min() < threshold:
            return r * cellsize_m
    return max_steps * cellsize_m


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    args = ap.parse_args()
    detect(args.course)


if __name__ == "__main__":
    main()
