"""Render a visual QC overlay of traced features on NAIP.

Input:  courses/<slug>/sources/imagery/naip_clip.tif
        courses/<slug>/derived/features.geojson
Output: courses/<slug>/derived/features_preview.png
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import rasterio

from _common import course_dir


COLORS = {
    "tree_canopy": ("#2e7d32", 0.40),    # dark green fill, 40% opacity
    "fairway":     ("#66bb6a", 0.55),    # mid-green
    "green":       ("#00e676", 0.85),    # bright highlight green
    "bunker":      ("#ffd54f", 0.90),    # warm yellow
    "water":       ("#03a9f4", 0.80),    # blue
    "rough":       ("#a5d6a7", 0.20),    # pale green, faint
}


def render(slug: str) -> Path:
    c = course_dir(slug)
    naip_path = c / "sources" / "imagery" / "naip_clip.tif"
    feat_path = c / "derived" / "features.geojson"

    with rasterio.open(naip_path) as src:
        rgb = src.read([1, 2, 3]).transpose(1, 2, 0).astype("float32") / 255.0
        bounds = src.bounds

    extent = (bounds.left, bounds.right, bounds.bottom, bounds.top)

    with feat_path.open() as f:
        coll = json.load(f)
    feats = coll["features"]

    # Two panels: (1) NAIP + filled overlay, (2) NAIP + outlines only
    fig, axes = plt.subplots(1, 2, figsize=(26, 14))
    for ax in axes:
        ax.imshow(np.clip(rgb, 0, 1), extent=extent)
        ax.set_xticks([])
        ax.set_yticks([])

    counts: dict = {}
    for feat in feats:
        kind = feat["properties"]["kind"]
        color, alpha = COLORS.get(kind, ("#ff00ff", 0.3))
        geom = feat["geometry"]
        polys = (
            geom["coordinates"] if geom["type"] == "Polygon"
            else [p for mp in geom["coordinates"] for p in mp]
        )
        for ring_list in ([geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]):
            exterior = ring_list[0]
            xs = [p[0] for p in exterior]
            ys = [p[1] for p in exterior]
            # filled overlay (left)
            axes[0].fill(xs, ys, color=color, alpha=alpha, linewidth=0)
            # outlined (right)
            axes[1].plot(xs, ys, color=color, linewidth=0.6, alpha=0.95)
        counts[kind] = counts.get(kind, 0) + 1

    axes[0].set_title(
        f"{slug} — Phase B v1 traced features (filled)\n" +
        "  ".join(f"{k}:{v}" for k, v in counts.items()),
        fontsize=13,
    )
    axes[1].set_title(f"{slug} — outlines only", fontsize=13)

    legend = [mpatches.Patch(color=c_[0], alpha=c_[1], label=k) for k, c_ in COLORS.items()]
    axes[0].legend(handles=legend, loc="upper right", fontsize=10, framealpha=0.85)

    out = c / "derived" / "features_preview.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"[features-preview] wrote {out}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    args = ap.parse_args()
    render(args.course)


if __name__ == "__main__":
    main()
