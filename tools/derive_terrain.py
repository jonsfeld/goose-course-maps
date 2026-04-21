"""Derive slope / hillshade / aspect rasters from a clipped DEM.

Inputs:  courses/<slug>/derived/dem_clipped.tif
Outputs: courses/<slug>/derived/{slope,hillshade,aspect}.tif
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import rasterio

from _common import course_dir, ensure_dir


def _gradients(arr: np.ndarray, cellsize_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Central-difference gradient (dz/dx, dz/dy) in meters per meter."""
    dzdy, dzdx = np.gradient(arr, cellsize_m, cellsize_m)
    return dzdx, dzdy


def _write(
    path: Path,
    arr: np.ndarray,
    base_meta: dict,
    dtype: str = "float32",
    nodata: float | int | None = None,
) -> None:
    meta = base_meta.copy()
    meta.update({"dtype": dtype, "count": 1, "compress": "deflate", "tiled": True})
    if nodata is None:
        meta.pop("nodata", None)
    else:
        meta["nodata"] = nodata
    with rasterio.open(path, "w", **meta) as dst:
        dst.write(arr.astype(dtype), 1)


def derive(slug: str, azimuth_deg: float = 315.0, altitude_deg: float = 45.0) -> None:
    derived = ensure_dir(course_dir(slug) / "derived")
    dem_path = derived / "dem_clipped.tif"
    if not dem_path.exists():
        raise FileNotFoundError(f"{dem_path} not found; run merge_clip_dem.py first")

    with rasterio.open(dem_path) as src:
        dem = src.read(1).astype("float32")
        meta = src.meta.copy()
        src_nodata = src.nodata
        # Approximate cellsize in meters using the raster transform.
        lat_center = src.bounds.top - (src.bounds.top - src.bounds.bottom) / 2
        deg_per_m_y = 1 / 111_000
        deg_per_m_x = 1 / (111_000 * math.cos(math.radians(lat_center)))
        px_x_m = abs(src.transform.a) / deg_per_m_x
        px_y_m = abs(src.transform.e) / deg_per_m_y
        cellsize_m = (px_x_m + px_y_m) / 2.0

    print(f"[terrain] DEM {dem.shape}, cellsize ~{cellsize_m:.3f} m")

    # Mask nodata before computing gradients so boundary cells don't produce
    # spurious 90° slopes. Replace with nearest-valid via simple infill.
    if src_nodata is not None:
        valid_mask = dem != src_nodata
    else:
        valid_mask = np.ones_like(dem, dtype=bool)
    # Fill nodata cells with the local mean of valid cells so gradient is smooth.
    if not valid_mask.all():
        fill_value = float(dem[valid_mask].mean())
        dem_filled = np.where(valid_mask, dem, fill_value)
    else:
        dem_filled = dem

    dzdx, dzdy = _gradients(dem_filled, cellsize_m)

    # Slope in degrees
    slope_rad = np.arctan(np.hypot(dzdx, dzdy))
    slope_deg = np.degrees(slope_rad).astype("float32")
    slope_deg[~valid_mask] = -1.0
    _write(derived / "slope.tif", slope_deg, meta, dtype="float32", nodata=-1.0)
    valid_slope = slope_deg[valid_mask]
    print(
        f"[terrain] wrote slope.tif (valid range {valid_slope.min():.2f}° – "
        f"{valid_slope.max():.2f}°, mean {valid_slope.mean():.2f}°)"
    )

    # Aspect in degrees (0 = N, clockwise)
    aspect_rad = np.arctan2(-dzdx, dzdy)
    aspect_deg = (np.degrees(aspect_rad) + 360.0) % 360.0
    flat = slope_deg < 0.01
    aspect_deg[flat] = -1.0
    aspect_deg[~valid_mask] = -1.0
    _write(derived / "aspect.tif", aspect_deg.astype("float32"), meta, dtype="float32", nodata=-1.0)
    print("[terrain] wrote aspect.tif")

    # Hillshade — Horn formulation, uint8 with 0 as nodata sentinel
    az_rad = math.radians(360.0 - azimuth_deg + 90.0)
    alt_rad = math.radians(altitude_deg)
    hs = (
        np.sin(alt_rad) * np.cos(slope_rad)
        + np.cos(alt_rad) * np.sin(slope_rad) * np.cos(az_rad - aspect_rad)
    )
    hs = np.clip(hs, 0, 1) * 255.0
    hs[~valid_mask] = 0
    _write(derived / "hillshade.tif", hs, meta, dtype="uint8", nodata=0)
    print(f"[terrain] wrote hillshade.tif (az={azimuth_deg}°, alt={altitude_deg}°)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    ap.add_argument("--azimuth", type=float, default=315.0)
    ap.add_argument("--altitude", type=float, default=45.0)
    args = ap.parse_args()
    derive(args.course, args.azimuth, args.altitude)


if __name__ == "__main__":
    main()
