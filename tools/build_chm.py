"""Build a Canopy Height Model (CHM) from raw LAZ point cloud tiles.

CHM = DSM (first-return / highest-return raster) − DEM (bare earth).

Inputs:
  courses/<slug>/sources/point_cloud/*.laz
  courses/<slug>/derived/dem_clipped.tif      (produced by merge_clip_dem.py)

Output:
  courses/<slug>/derived/canopy_height_model.tif  (float32, meters above ground)

Notes:
  - Uses a simple max-height-per-cell rasterization at ~1 m resolution.
  - CHM is clipped to the course bbox and co-registered with the clipped DEM.
  - Heights below 0.3 m are clamped to 0 (ground + noise).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import laspy
import numpy as np
import rasterio
from rasterio.transform import Affine

from _common import course_dir, ensure_dir


CHM_NOISE_FLOOR_M = 0.3
CHM_MAX_PLAUSIBLE_M = 80.0   # anything above this is garbage (tallest trees ~50m)


def build(slug: str) -> Path:
    derived = ensure_dir(course_dir(slug) / "derived")
    dem_path = derived / "dem_clipped.tif"
    if not dem_path.exists():
        raise FileNotFoundError(f"{dem_path} not found; run merge_clip_dem.py first")

    laz_paths = sorted((course_dir(slug) / "sources" / "point_cloud").glob("*.laz"))
    if not laz_paths:
        raise FileNotFoundError("No LAZ tiles under sources/point_cloud/")

    # Reference grid: use the clipped DEM's transform + shape so the CHM is co-registered.
    with rasterio.open(dem_path) as dem_src:
        dem = dem_src.read(1).astype("float32")
        height, width = dem.shape
        transform: Affine = dem_src.transform
        crs = dem_src.crs
        bounds = dem_src.bounds
        meta = dem_src.meta.copy()
        dem_nodata = dem_src.nodata
    dem_valid = dem != dem_nodata if dem_nodata is not None else np.ones_like(dem, dtype=bool)

    print(f"[chm] target grid {width}x{height}, crs={crs}, bounds={bounds}")

    # Accumulate max-Z per cell from all LAZ tiles, in WGS-84 lat/lon to match the DEM.
    dsm = np.full((height, width), np.nan, dtype="float32")

    for laz_path in laz_paths:
        print(f"[chm] reading {laz_path.name}")
        with laspy.open(laz_path) as fh:
            las = fh.read()
            # LAZ is in UTM 11N (EPSG:26911 or similar); reproject to lat/lon for the grid.
            # We use the LAZ header's georeferencing via pyproj.
            from pyproj import Transformer

            src_crs = _extract_laz_crs(las)
            transformer = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
            lons, lats = transformer.transform(las.x, las.y)
            zs = np.asarray(las.z, dtype="float32")

            # Filter points outside the bbox for speed.
            inside = (
                (lons >= bounds.left)
                & (lons <= bounds.right)
                & (lats >= bounds.bottom)
                & (lats <= bounds.top)
            )
            lons, lats, zs = lons[inside], lats[inside], zs[inside]
            if lons.size == 0:
                continue

            cols = ((lons - transform.c) / transform.a).astype(int)
            rows = ((lats - transform.f) / transform.e).astype(int)
            valid = (rows >= 0) & (rows < height) & (cols >= 0) & (cols < width)
            rows, cols, zs = rows[valid], cols[valid], zs[valid]

            # Max-z accumulation. np.maximum.at handles duplicate indices.
            existing = dsm[rows, cols]
            new_vals = np.where(np.isnan(existing) | (zs > existing), zs, existing)
            dsm[rows, cols] = new_vals

    dsm_valid = ~np.isnan(dsm)
    valid = dsm_valid & dem_valid
    print(
        f"[chm] DSM populated for {dsm_valid.sum()} / {dsm.size} cells; "
        f"DEM valid for {dem_valid.sum()}; both valid {valid.sum()}"
    )

    chm = np.where(valid, dsm - dem, 0.0).astype("float32")
    chm[chm < CHM_NOISE_FLOOR_M] = 0.0
    # Clip impossible heights (hard cap; these are artifacts of mis-aligned cells)
    implausible = chm > CHM_MAX_PLAUSIBLE_M
    if implausible.any():
        print(f"[chm] clipping {implausible.sum()} implausible cells (>{CHM_MAX_PLAUSIBLE_M} m) to 0")
        chm[implausible] = 0.0

    out_path = derived / "canopy_height_model.tif"
    meta.update({"dtype": "float32", "compress": "deflate", "tiled": True})
    with rasterio.open(out_path, "w", **meta) as dst:
        dst.write(chm, 1)

    size_mb = out_path.stat().st_size / 1e6
    print(
        f"[chm] wrote {out_path} ({size_mb:.1f} MB, "
        f"max {chm.max():.1f} m, 95th pct {np.percentile(chm[chm > 0], 95):.1f} m if nonzero)"
    )
    return out_path


def _extract_laz_crs(las: laspy.LasData) -> str:
    """Best-effort CRS extraction from LAS header."""
    # USGS LPC CA LosAngeles B23 is UTM 11N NAD83(2011) → EPSG:6340 horizontal,
    # but many LAS files encode it as EPSG:26911 (NAD83 UTM 11N). Either works
    # for our ~1m precision.
    for vlr in las.header.vlrs:
        if hasattr(vlr, "parse_crs"):
            try:
                crs = vlr.parse_crs()
                if crs is not None:
                    return crs.to_string()
            except Exception:
                pass
    # Fallback — hardcoded for our current data source.
    return "EPSG:26911"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    args = ap.parse_args()
    build(args.course)


if __name__ == "__main__":
    main()
