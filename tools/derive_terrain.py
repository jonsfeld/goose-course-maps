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


def _write(path: Path, arr: np.ndarray, base_meta: dict, dtype: str = "float32") -> None:
    meta = base_meta.copy()
    meta.update({"dtype": dtype, "count": 1, "compress": "deflate", "tiled": True})
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
        # Approximate cellsize in meters using the raster transform.
        # dem_clipped.tif is EPSG:4326 with a ~1m resolution computed by merge_clip_dem.py,
        # but we derive a local conversion via the y-transform step and latitude.
        lat_center = src.bounds.top - (src.bounds.top - src.bounds.bottom) / 2
        deg_per_m_y = 1 / 111_000
        deg_per_m_x = 1 / (111_000 * math.cos(math.radians(lat_center)))
        px_x_m = abs(src.transform.a) / deg_per_m_x
        px_y_m = abs(src.transform.e) / deg_per_m_y
        cellsize_m = (px_x_m + px_y_m) / 2.0

    print(f"[terrain] DEM {dem.shape}, cellsize ~{cellsize_m:.3f} m")

    dzdx, dzdy = _gradients(dem, cellsize_m)

    # Slope in degrees
    slope_rad = np.arctan(np.hypot(dzdx, dzdy))
    slope_deg = np.degrees(slope_rad)
    _write(derived / "slope.tif", slope_deg, meta)
    print(f"[terrain] wrote slope.tif (range {slope_deg.min():.2f}° – {slope_deg.max():.2f}°)")

    # Aspect in degrees (0 = N, clockwise)
    aspect_rad = np.arctan2(-dzdx, dzdy)
    aspect_deg = (np.degrees(aspect_rad) + 360.0) % 360.0
    # Flat cells → -1 sentinel
    flat = slope_deg < 0.01
    aspect_deg[flat] = -1.0
    _write(derived / "aspect.tif", aspect_deg, meta)
    print(f"[terrain] wrote aspect.tif")

    # Hillshade — standard Horn formulation
    az_rad = math.radians(360.0 - azimuth_deg + 90.0)
    alt_rad = math.radians(altitude_deg)
    hs = (
        np.sin(alt_rad) * np.cos(slope_rad)
        + np.cos(alt_rad) * np.sin(slope_rad) * np.cos(az_rad - aspect_rad)
    )
    hs = np.clip(hs, 0, 1) * 255.0
    _write(derived / "hillshade.tif", hs, meta, dtype="uint8")
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
