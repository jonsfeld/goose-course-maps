"""Render a high-res NAIP view of the course with lat/lon grid + labeled cell
grid so the user can identify each hole's green location.

Output: courses/<slug>/derived/green_picker.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import rasterio

from _common import course_dir


def render(slug: str, cells_x: int = 10, cells_y: int = 10) -> Path:
    c = course_dir(slug)
    naip_path = c / "sources" / "imagery" / "naip_clip.tif"
    with rasterio.open(naip_path) as src:
        rgb = src.read([1, 2, 3]).transpose(1, 2, 0).astype("float32") / 255.0
        b = src.bounds
    extent = (b.left, b.right, b.bottom, b.top)

    fig, ax = plt.subplots(figsize=(22, 22))
    ax.imshow(np.clip(rgb, 0, 1), extent=extent)

    # Fine lat/lon grid — every 0.0005° ≈ 55m
    step = 0.0005
    lons = np.arange(b.left, b.right + step / 2, step)
    lats = np.arange(b.bottom, b.top + step / 2, step)
    for lon in lons:
        ax.axvline(lon, color="white", linewidth=0.3, alpha=0.35)
    for lat in lats:
        ax.axhline(lat, color="white", linewidth=0.3, alpha=0.35)

    # Letter/number cell grid (A1..J10 style for easy verbal reference)
    letters = "ABCDEFGHIJ"
    for i in range(cells_x):
        for j in range(cells_y):
            cx = b.left + (i + 0.5) * (b.right - b.left) / cells_x
            cy = b.bottom + (j + 0.5) * (b.top - b.bottom) / cells_y
            label = f"{letters[i]}{cells_y - j}"  # so A1 is SW corner, J10 NE
            ax.text(cx, cy, label, fontsize=11, color="white",
                    alpha=0.55, ha="center", va="center", fontweight="bold")

    # Cell boundaries (thicker white lines)
    for i in range(cells_x + 1):
        lon = b.left + i * (b.right - b.left) / cells_x
        ax.axvline(lon, color="yellow", linewidth=0.8, alpha=0.45)
    for j in range(cells_y + 1):
        lat = b.bottom + j * (b.top - b.bottom) / cells_y
        ax.axhline(lat, color="yellow", linewidth=0.8, alpha=0.45)

    # Axis labels with actual lat/lon values
    ax.set_xticks(np.arange(b.left, b.right + 0.001, 0.001))
    ax.set_yticks(np.arange(b.bottom, b.top + 0.001, 0.001))
    ax.set_xlabel("Longitude (°W)", fontsize=13)
    ax.set_ylabel("Latitude (°N)", fontsize=13)
    ax.tick_params(labelsize=11)
    ax.set_title(
        f"Roosevelt GC — green picker view\n"
        f"Cell grid (yellow) = A1 (SW) to J10 (NE); white fine grid = 0.0005° (~55m) steps\n"
        f"Bounds: lon {b.left:.4f} to {b.right:.4f}  |  lat {b.bottom:.4f} to {b.top:.4f}",
        fontsize=13,
    )

    out = c / "derived" / "green_picker.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[green-picker] wrote {out}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    args = ap.parse_args()
    render(args.course)


if __name__ == "__main__":
    main()
