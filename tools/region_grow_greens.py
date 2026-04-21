"""Region-grow precise green polygons from user-placed seed centroids.

For each seed:
  1. Find nearest green-like pixel within a search radius (NDVI > 0.30,
     slope < GREEN_MAX_SLOPE, CHM < 0.5m).
  2. Flood-fill from that anchor using multi-criteria tolerance:
     - NDVI within NDVI_TOL of anchor
     - RGB within RGB_TOL of anchor
     - slope < GREEN_MAX_SLOPE
     - CHM < GREEN_MAX_CHM
  3. Close + clean the mask, polygonize, keep largest component touching anchor.
  4. Write one polygon per seed (+ its centroid_id) to greens_grown.geojson.

Input:  courses/<slug>/notes/green_centroids_draft.geojson
        courses/<slug>/sources/imagery/naip_clip.tif
        courses/<slug>/derived/slope.tif
        courses/<slug>/derived/canopy_height_model.tif
Output: courses/<slug>/derived/greens_grown.geojson
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio import features as rio_features
from rasterio.warp import Resampling, reproject
from scipy import ndimage
from shapely.geometry import mapping, shape

from _common import course_dir


SEARCH_RADIUS_M = 40.0         # search this far from seed to find an anchor pixel
NDVI_GREEN_MIN = 0.25          # slightly looser — some greens have lower NDVI
GREEN_MAX_SLOPE = 4.0          # a bit more tolerant; real greens have gentle slopes
GREEN_MAX_CHM = 0.7            # allow thin fringe canopy around edges
NDVI_TOL = 0.15                # wider flood-fill tolerance
RGB_TOL = 55                   # looser RGB tolerance
MIN_GREEN_AREA_M2 = 100
MAX_GREEN_AREA_M2 = 1500       # cap growth so it doesn't eat the whole fairway


def _resample_to_naip(path: Path, ref_transform, ref_shape, ref_crs) -> np.ndarray:
    with rasterio.open(path) as src:
        src_nodata = src.nodata
        arr = src.read(1).astype("float32")
        if src_nodata is not None:
            arr = np.where(arr == src_nodata, np.nan, arr)
        meta = src.meta.copy()
        meta.update({"dtype": "float32", "nodata": np.nan})
    out = np.zeros(ref_shape, dtype="float32")
    with rasterio.MemoryFile() as mf:
        with mf.open(**meta) as ms:
            ms.write(arr, 1)
            reproject(
                source=rasterio.band(ms, 1), destination=out,
                src_transform=ms.transform, src_crs=ms.crs,
                dst_transform=ref_transform, dst_crs=ref_crs,
                resampling=Resampling.bilinear,
                src_nodata=np.nan, dst_nodata=np.nan,
            )
    return np.where(np.isnan(out), 0.0, out)


def _find_anchor(r, g, b, nir, slope, chm, yx, search_px):
    """Starting at (y, x), spiral outward to find the nearest 'green-like' pixel."""
    y0, x0 = yx
    H, W = r.shape
    # Simple bounded-box search: pick best-score pixel within window
    y_lo = max(0, y0 - search_px); y_hi = min(H, y0 + search_px + 1)
    x_lo = max(0, x0 - search_px); x_hi = min(W, x0 + search_px + 1)
    eps = 1e-6
    ndvi = (nir[y_lo:y_hi, x_lo:x_hi] - r[y_lo:y_hi, x_lo:x_hi]) / (
        nir[y_lo:y_hi, x_lo:x_hi] + r[y_lo:y_hi, x_lo:x_hi] + eps
    )
    ok = (
        (ndvi >= NDVI_GREEN_MIN)
        & (slope[y_lo:y_hi, x_lo:x_hi] <= GREEN_MAX_SLOPE)
        & (chm[y_lo:y_hi, x_lo:x_hi] <= GREEN_MAX_CHM)
    )
    if not ok.any():
        return None
    # Pick the ok pixel nearest to the seed, tiebreak by highest NDVI
    ys, xs = np.nonzero(ok)
    ys_abs = ys + y_lo; xs_abs = xs + x_lo
    dists = (ys_abs - y0) ** 2 + (xs_abs - x0) ** 2
    # Blend distance + (1 - ndvi) for score
    scores = dists - (ndvi[ys, xs] * 200)   # prefer higher NDVI, closer to seed
    idx = int(np.argmin(scores))
    return int(ys_abs[idx]), int(xs_abs[idx])


def _flood_fill_mask(r, g, b, nir, slope, chm, anchor, rgb_tol, ndvi_tol, max_pixels):
    """BFS flood-fill from anchor while RGB + NDVI stay within tolerance."""
    H, W = r.shape
    ay, ax = anchor
    ar = float(r[ay, ax]); ag = float(g[ay, ax]); ab = float(b[ay, ax])
    eps = 1e-6
    anchor_ndvi = float((nir[ay, ax] - r[ay, ax]) / (nir[ay, ax] + r[ay, ax] + eps))

    mask = np.zeros((H, W), dtype=bool)
    visited = np.zeros((H, W), dtype=bool)
    queue = [(ay, ax)]
    visited[ay, ax] = True
    count = 0
    while queue and count < max_pixels:
        y, x = queue.pop()
        # Test criteria at this pixel
        dr = float(r[y, x]) - ar
        dg = float(g[y, x]) - ag
        db = float(b[y, x]) - ab
        if abs(dr) > rgb_tol or abs(dg) > rgb_tol or abs(db) > rgb_tol:
            continue
        ndvi = (float(nir[y, x]) - float(r[y, x])) / (float(nir[y, x]) + float(r[y, x]) + eps)
        if abs(ndvi - anchor_ndvi) > ndvi_tol:
            continue
        if slope[y, x] > GREEN_MAX_SLOPE or chm[y, x] > GREEN_MAX_CHM:
            continue
        mask[y, x] = True
        count += 1
        # Enqueue neighbors
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and not visited[ny, nx]:
                visited[ny, nx] = True
                queue.append((ny, nx))
    return mask, count


def grow(slug: str) -> Path:
    c = course_dir(slug)
    naip_path = c / "sources" / "imagery" / "naip_clip.tif"
    slope_path = c / "derived" / "slope.tif"
    chm_path = c / "derived" / "canopy_height_model.tif"
    seeds_path = c / "notes" / "green_centroids_draft.geojson"

    for p in (naip_path, slope_path, chm_path, seeds_path):
        if not p.exists():
            raise FileNotFoundError(p)

    with rasterio.open(naip_path) as src:
        bands = src.read().astype("float32")
        transform = src.transform
        shape_hw = src.shape
        crs = src.crs
        bounds = src.bounds

    r, g, b, nir = bands[0], bands[1], bands[2], bands[3]
    slope = _resample_to_naip(slope_path, transform, shape_hw, crs)
    chm = _resample_to_naip(chm_path, transform, shape_hw, crs)

    # Approx cellsize in meters
    lat = (bounds.top + bounds.bottom) / 2
    px_x_m = abs(transform.a) * 111_000 * math.cos(math.radians(lat))
    px_y_m = abs(transform.e) * 111_000
    cell_m = (px_x_m + px_y_m) / 2.0
    search_px = max(3, int(SEARCH_RADIUS_M / cell_m))
    cell_area_m2 = cell_m ** 2
    max_green_px = int(MAX_GREEN_AREA_M2 / cell_area_m2)
    print(f"[grow] NAIP {shape_hw}, cellsize ~{cell_m:.3f} m, search {search_px} px, max green {max_green_px} px")

    # Load seeds
    with seeds_path.open() as f:
        seeds = json.load(f)["features"]

    out_feats = []
    for seed in seeds:
        cid = seed["properties"].get("centroid_id") or seed["properties"].get("hole")
        lon, lat_ = seed["geometry"]["coordinates"]
        col = int((lon - transform.c) / transform.a)
        row = int((lat_ - transform.f) / transform.e)
        if not (0 <= row < shape_hw[0] and 0 <= col < shape_hw[1]):
            print(f"[grow] seed #{cid} outside raster — skipping")
            continue

        anchor = _find_anchor(r, g, b, nir, slope, chm, (row, col), search_px)
        if anchor is None:
            print(f"[grow] seed #{cid}: no green-like anchor within {SEARCH_RADIUS_M}m")
            continue
        ay, ax = anchor
        aly, alx = float(transform.f + ay * transform.e), float(transform.c + ax * transform.a)
        dist_m = math.hypot((ay - row) * px_y_m, (ax - col) * px_x_m)
        print(f"[grow] seed #{cid}: anchor at ({aly:.5f}, {alx:.5f}), {dist_m:.1f}m from seed")

        mask, nfill = _flood_fill_mask(
            r, g, b, nir, slope, chm, anchor, RGB_TOL, NDVI_TOL, max_green_px,
        )
        print(f"[grow] seed #{cid}: raw flood fill {int(mask.sum())} px ({nfill} visited)")
        # Clean up: close small holes only. Skip opening — it can erode small greens.
        struct = np.ones((3, 3), dtype=bool)
        mask = ndimage.binary_closing(mask, structure=struct, iterations=2)

        # Keep only the connected component containing anchor
        labels, _ = ndimage.label(mask, structure=struct)
        anchor_label = labels[ay, ax]
        if anchor_label == 0:
            # Closing can sometimes knock the anchor pixel off the mask.
            # Find the biggest component in the mask and use it.
            unique, counts = np.unique(labels[labels > 0], return_counts=True)
            if unique.size == 0:
                print(f"[grow] seed #{cid}: empty mask after closing — skipping")
                continue
            anchor_label = int(unique[np.argmax(counts)])
            print(f"[grow] seed #{cid}: anchor not on post-closing mask, using largest component")
        mask = labels == anchor_label

        npix = int(mask.sum())
        area_m2 = npix * cell_area_m2
        if area_m2 < MIN_GREEN_AREA_M2:
            print(f"[grow] seed #{cid}: final area {area_m2:.0f} m² below min, skipping")
            continue

        # Polygonize — take the single shape produced
        shapes = list(rio_features.shapes(
            mask.astype("uint8"), mask=mask, transform=transform, connectivity=8,
        ))
        if not shapes:
            continue
        geom, _ = max(shapes, key=lambda s: shape(s[0]).area)
        poly = shape(geom)

        out_feats.append({
            "type": "Feature",
            "properties": {
                "centroid_id": cid,
                "provisional_hole": None,
                "kind": "green",
                "area_m2": round(area_m2, 1),
                "anchor_latlon": [round(aly, 6), round(alx, 6)],
                "source": "phase_b_v1.5_region_grow",
            },
            "geometry": mapping(poly),
        })
        print(f"[grow] seed #{cid}: grown polygon {area_m2:.0f} m² ({npix} px)")

    out_path = c / "derived" / "greens_grown.geojson"
    with out_path.open("w") as f:
        json.dump({"type": "FeatureCollection", "features": out_feats}, f)
    print(f"[grow] wrote {out_path} with {len(out_feats)} greens")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    args = ap.parse_args()
    grow(args.course)


if __name__ == "__main__":
    main()
