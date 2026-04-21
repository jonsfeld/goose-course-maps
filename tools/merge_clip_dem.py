"""Merge the course's 1m DEM tiles and clip to the course bbox.

Inputs:  courses/<slug>/sources/dem/*.tif  (all GeoTIFFs in that dir are merged)
Output:  courses/<slug>/derived/dem_clipped.tif  (WGS-84, EPSG:4326)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import rasterio
from rasterio.mask import mask
from rasterio.merge import merge
from rasterio.warp import Resampling, calculate_default_transform, reproject
from shapely.geometry import box, mapping

from _common import bbox_from_course, course_dir, ensure_dir


def merge_clip(slug: str) -> Path:
    src_dir = course_dir(slug) / "sources" / "dem"
    tifs = sorted(src_dir.glob("*.tif"))
    if not tifs:
        raise FileNotFoundError(f"No DEM tiles found in {src_dir}")

    out_dir = ensure_dir(course_dir(slug) / "derived")
    merged_utm_path = out_dir / "_tmp_dem_merged_utm.tif"
    out_path = out_dir / "dem_clipped.tif"

    print(f"[dem] merging {len(tifs)} tiles from {src_dir}")
    srcs = [rasterio.open(p) for p in tifs]
    try:
        mosaic, transform = merge(srcs)
        meta = srcs[0].meta.copy()
        meta.update({
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": transform,
            "compress": "deflate",
            "tiled": True,
        })
        with rasterio.open(merged_utm_path, "w", **meta) as dst:
            dst.write(mosaic)
        src_crs = srcs[0].crs
    finally:
        for s in srcs:
            s.close()
    print(f"[dem] merged mosaic CRS: {src_crs}")

    # Reproject to WGS-84 and clip to the course bbox in one pass.
    minx, miny, maxx, maxy = bbox_from_course(slug)
    print(f"[dem] clipping to bbox {minx:.5f},{miny:.5f},{maxx:.5f},{maxy:.5f}")

    with rasterio.open(merged_utm_path) as src:
        dst_crs = "EPSG:4326"
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds,
            resolution=(1 / 111000, 1 / 111000),  # ~1m at this latitude
        )
        reproj_meta = src.meta.copy()
        reproj_meta.update({
            "crs": dst_crs,
            "transform": transform,
            "width": width,
            "height": height,
            "compress": "deflate",
            "tiled": True,
        })
        reproj_path = out_dir / "_tmp_dem_merged_wgs84.tif"
        with rasterio.open(reproj_path, "w", **reproj_meta) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=Resampling.bilinear,
            )

    # Now clip the reprojected raster to the course bbox.
    clip_geom = [mapping(box(minx, miny, maxx, maxy))]
    with rasterio.open(reproj_path) as src:
        clipped, clipped_transform = mask(src, clip_geom, crop=True)
        out_meta = src.meta.copy()
        out_meta.update({
            "height": clipped.shape[1],
            "width": clipped.shape[2],
            "transform": clipped_transform,
            "compress": "deflate",
            "tiled": True,
        })
    with rasterio.open(out_path, "w", **out_meta) as dst:
        dst.write(clipped)

    merged_utm_path.unlink(missing_ok=True)
    reproj_path.unlink(missing_ok=True)

    size_mb = out_path.stat().st_size / 1e6
    print(f"[dem] wrote {out_path} ({size_mb:.1f} MB, {clipped.shape[2]}x{clipped.shape[1]})")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    args = ap.parse_args()
    merge_clip(args.course)


if __name__ == "__main__":
    main()
