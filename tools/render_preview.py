"""Render a 4-panel QC preview of a course's derived layers.

Inputs:  courses/<slug>/sources/imagery/naip_clip.tif
         courses/<slug>/derived/{hillshade,slope,canopy_height_model}.tif
         courses/<slug>/derived/canopy_polygons.geojson

Output:  courses/<slug>/derived/preview.png  (multi-panel QC image)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

from _common import course_dir, ensure_dir


def _read_to_shape(path: Path, target_shape: tuple[int, int], target_transform, target_crs):
    """Read a raster and resample it to match target grid."""
    with rasterio.open(path) as src:
        bands = src.count
        out = np.zeros((bands, *target_shape), dtype="float32")
        for i in range(bands):
            reproject(
                source=rasterio.band(src, i + 1),
                destination=out[i],
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=target_transform,
                dst_crs=target_crs,
                resampling=Resampling.bilinear,
            )
    return out.squeeze()


def render(slug: str) -> Path:
    c = course_dir(slug)
    naip_path = c / "sources" / "imagery" / "naip_clip.tif"
    hillshade_path = c / "derived" / "hillshade.tif"
    slope_path = c / "derived" / "slope.tif"
    chm_path = c / "derived" / "canopy_height_model.tif"
    canopy_poly_path = c / "derived" / "canopy_polygons.geojson"

    for p in (naip_path, hillshade_path, slope_path, chm_path, canopy_poly_path):
        if not p.exists():
            raise FileNotFoundError(f"Missing input: {p}")

    # NAIP is the reference grid (2048x2048, WGS-84).
    with rasterio.open(naip_path) as src:
        naip_rgb = src.read([1, 2, 3]).transpose(1, 2, 0).astype("float32") / 255.0
        naip_shape = src.shape
        naip_transform = src.transform
        naip_crs = src.crs
        naip_bounds = src.bounds

    print(f"[preview] NAIP {naip_shape}, bounds {naip_bounds}")

    # Resample hillshade / slope / CHM to NAIP grid
    hs = _read_to_shape(hillshade_path, naip_shape, naip_transform, naip_crs)
    slope = _read_to_shape(slope_path, naip_shape, naip_transform, naip_crs)
    chm = _read_to_shape(chm_path, naip_shape, naip_transform, naip_crs)

    # Build panels
    fig, axes = plt.subplots(2, 2, figsize=(18, 18))
    fig.suptitle(
        f"{slug} — Phase C QC preview",
        fontsize=16, fontweight="bold", y=0.995,
    )
    extent = (naip_bounds.left, naip_bounds.right, naip_bounds.bottom, naip_bounds.top)

    # (0,0) NAIP
    axes[0, 0].imshow(np.clip(naip_rgb, 0, 1), extent=extent)
    axes[0, 0].set_title("NAIP aerial (2025 ImageServer, 2048² clip)")

    # (0,1) Hillshade
    axes[0, 1].imshow(hs, cmap="gray", extent=extent, vmin=0, vmax=255)
    axes[0, 1].set_title("Hillshade (315° az, 45° alt)")

    # (1,0) Slope — mask nodata (=-1) for display
    slope_display = np.where(slope < 0, np.nan, slope)
    im = axes[1, 0].imshow(
        slope_display, cmap="inferno", extent=extent, vmin=0, vmax=45,
    )
    axes[1, 0].set_title("Slope (degrees, 0-45° ramp)")
    plt.colorbar(im, ax=axes[1, 0], fraction=0.04, pad=0.02)

    # (1,1) NAIP + canopy polygon outlines
    axes[1, 1].imshow(np.clip(naip_rgb, 0, 1), extent=extent)
    with canopy_poly_path.open() as f:
        canopy = json.load(f)
    n_polys = 0
    for feat in canopy["features"]:
        geom = feat["geometry"]
        if geom["type"] == "Polygon":
            for ring in geom["coordinates"]:
                xs = [p[0] for p in ring]
                ys = [p[1] for p in ring]
                axes[1, 1].plot(xs, ys, color="#00FF88", linewidth=0.35, alpha=0.85)
            n_polys += 1
    axes[1, 1].set_title(f"NAIP + canopy polygons ({n_polys} outlined)")
    axes[1, 1].set_xlim(extent[0], extent[1])
    axes[1, 1].set_ylim(extent[2], extent[3])

    for ax in axes.flat:
        ax.set_xticks([])
        ax.set_yticks([])

    out_path = c / "derived" / "preview.png"
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    size_mb = out_path.stat().st_size / 1e6
    print(f"[preview] wrote {out_path} ({size_mb:.2f} MB)")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    args = ap.parse_args()
    render(args.course)


if __name__ == "__main__":
    main()
