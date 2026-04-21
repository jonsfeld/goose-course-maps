"""Render a high-DPI zoomed NAIP view focused on the course area for
precise green annotation by the user.

Output: courses/<slug>/derived/green_picker_zoom.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.windows import from_bounds

from _common import course_dir


# Zoom to just the course area (tight bbox of visible course from v4 NAIP).
ZOOM_LON_MIN = -118.2955
ZOOM_LON_MAX = -118.2830
ZOOM_LAT_MIN =   34.1175
ZOOM_LAT_MAX =   34.1235


def render(slug: str) -> Path:
    c = course_dir(slug)
    naip_path = c / "sources" / "imagery" / "naip_clip.tif"

    with rasterio.open(naip_path) as src:
        # Read only the zoomed window to keep output sharp
        win = from_bounds(
            ZOOM_LON_MIN, ZOOM_LAT_MIN, ZOOM_LON_MAX, ZOOM_LAT_MAX,
            transform=src.transform,
        )
        rgb = src.read([1, 2, 3], window=win).transpose(1, 2, 0).astype("float32") / 255.0
        out_transform = src.window_transform(win)
        # Actual bounds of what we read (may be slightly expanded to window edges)
        h, w = rgb.shape[:2]
        left = out_transform.c
        top = out_transform.f
        right = left + w * out_transform.a
        bottom = top + h * out_transform.e
        print(f"[picker-zoom] read {w}x{h} pixels; bounds {left:.5f}..{right:.5f}, {bottom:.5f}..{top:.5f}")

    fig, ax = plt.subplots(figsize=(28, 14))
    ax.imshow(np.clip(rgb, 0, 1), extent=(left, right, bottom, top))

    # Fine grid every 0.0002° (~22m)
    fine_step = 0.0002
    # Medium grid every 0.001° (~110m)
    med_step = 0.001

    def _arange_inclusive(start, stop, step):
        n = int(round((stop - start) / step)) + 1
        return [start + i * step for i in range(n)]

    # Fine white grid
    for lon in _arange_inclusive(left, right, fine_step):
        ax.axvline(lon, color="white", linewidth=0.2, alpha=0.25)
    for lat in _arange_inclusive(bottom, top, fine_step):
        ax.axhline(lat, color="white", linewidth=0.2, alpha=0.25)

    # Medium yellow grid
    for lon in _arange_inclusive(left, right, med_step):
        ax.axvline(lon, color="yellow", linewidth=0.8, alpha=0.55)
        ax.annotate(
            f"{lon:.4f}", (lon, top - (top - bottom) * 0.005),
            fontsize=9, color="yellow", alpha=0.85, ha="center", va="top",
        )
    for lat in _arange_inclusive(bottom, top, med_step):
        ax.axhline(lat, color="yellow", linewidth=0.8, alpha=0.55)
        ax.annotate(
            f"{lat:.4f}", (left + (right - left) * 0.005, lat),
            fontsize=9, color="yellow", alpha=0.85, ha="left", va="center",
        )

    # Axis labels
    ax.set_xticks(np.arange(round(left, 3), right + 0.001, 0.002))
    ax.set_yticks(np.arange(round(bottom, 3), top + 0.001, 0.001))
    ax.tick_params(labelsize=10)
    ax.set_xlabel("Longitude (°)", fontsize=12)
    ax.set_ylabel("Latitude (°)", fontsize=12)
    ax.set_title(
        f"Roosevelt GC — zoomed course view for green annotation\n"
        f"Yellow grid: 0.001° (~110m). Fine white: 0.0002° (~22m). "
        f"Bounds: lon {left:.4f}..{right:.4f}  |  lat {bottom:.4f}..{top:.4f}",
        fontsize=12,
    )

    out = c / "derived" / "green_picker_zoom.png"
    fig.savefig(out, dpi=260, bbox_inches="tight")
    plt.close(fig)
    size_mb = out.stat().st_size / 1e6
    print(f"[picker-zoom] wrote {out} ({size_mb:.1f} MB)")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    args = ap.parse_args()
    render(args.course)


if __name__ == "__main__":
    main()
