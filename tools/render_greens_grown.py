"""Render NAIP + the region-grown green polygons labeled 1-9.

Output: courses/<slug>/derived/greens_grown_preview.png
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio

from _common import course_dir


def render(slug: str) -> Path:
    c = course_dir(slug)
    naip_path = c / "sources" / "imagery" / "naip_clip.tif"
    greens_path = c / "derived" / "greens_grown.geojson"

    with rasterio.open(naip_path) as src:
        rgb = src.read([1, 2, 3]).transpose(1, 2, 0).astype("float32") / 255.0
        b = src.bounds
    extent = (b.left, b.right, b.bottom, b.top)

    with greens_path.open() as f:
        feats = json.load(f)["features"]

    fig, ax = plt.subplots(figsize=(20, 14))
    ax.imshow(np.clip(rgb, 0, 1), extent=extent)

    for feat in feats:
        cid = feat["properties"].get("centroid_id") or "?"
        area = feat["properties"].get("area_m2", "?")
        geom = feat["geometry"]
        coords = geom["coordinates"]
        rings = [coords[0]] if geom["type"] == "Polygon" else [p[0] for p in coords]
        for ring in rings:
            xs = [p[0] for p in ring]
            ys = [p[1] for p in ring]
            ax.fill(xs, ys, color="#00ff88", alpha=0.55, linewidth=0)
            ax.plot(xs, ys, color="white", linewidth=1.2)
        # Label at centroid
        from shapely.geometry import shape as shp
        centroid = shp(geom).centroid
        ax.annotate(
            f"{cid}\n{area:.0f}m²" if isinstance(area, (int, float)) else str(cid),
            (centroid.x, centroid.y),
            fontsize=12, fontweight="bold", color="white", ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#005f1f", edgecolor="white", linewidth=1),
            zorder=6,
        )

    ax.set_title(
        f"Roosevelt GC — region-grown greens ({len(feats)} of 9)\n"
        "Green fill + white outline = final polygon; label = centroid_id + area",
        fontsize=13,
    )
    ax.set_xticks([])
    ax.set_yticks([])

    out = c / "derived" / "greens_grown_preview.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"[grown-preview] wrote {out}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    args = ap.parse_args()
    render(args.course)


if __name__ == "__main__":
    main()
