"""Render OSM features over NAIP for visual QC."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from shapely.geometry import shape as shp

from _common import course_dir


COLORS = {
    "course_boundary": ("#ffffff", 0.00, 2.0),   # outline only
    "fairway":         ("#66bb6a", 0.55, 0.8),
    "green":           ("#00e676", 0.85, 1.6),
    "bunker":          ("#ffd54f", 0.90, 1.0),
    "tee_box":         ("#29b6f6", 0.85, 1.0),
    "water":           ("#03a9f4", 0.80, 1.0),
    "rough":           ("#a5d6a7", 0.20, 0.4),
    "tree_canopy":     ("#2e7d32", 0.35, 0.3),
    "cart_path":       ("#cfd8dc", 0.60, 0.6),
    "out_of_bounds":   ("#ef5350", 0.40, 0.8),
    "hole_line":       ("#ffffff", 0.00, 1.6),   # white line
    "clubhouse":       ("#8d6e63", 0.75, 1.0),
    "driving_range":   ("#aed581", 0.40, 0.6),
}


def render(slug: str) -> Path:
    c = course_dir(slug)
    naip_path = c / "sources" / "imagery" / "naip_clip.tif"
    feat_path = c / "derived" / "features_osm.geojson"

    with rasterio.open(naip_path) as src:
        rgb = src.read([1, 2, 3]).transpose(1, 2, 0).astype("float32") / 255.0
        b = src.bounds
    extent = (b.left, b.right, b.bottom, b.top)

    with feat_path.open() as f:
        feats = json.load(f)["features"]

    fig, ax = plt.subplots(figsize=(22, 14))
    ax.imshow(np.clip(rgb, 0, 1), extent=extent)

    counts = {}
    # Draw polygons first (so lines go on top)
    draw_order = [
        "course_boundary", "rough", "fairway", "bunker", "water", "green",
        "tee_box", "cart_path", "driving_range", "clubhouse", "out_of_bounds",
    ]
    for target in draw_order:
        for feat in feats:
            kind = feat["properties"]["kind"]
            if kind != target:
                continue
            color, alpha, lw = COLORS.get(kind, ("#ff00ff", 0.4, 0.8))
            geom = feat["geometry"]
            if geom["type"] == "Polygon":
                rings = [geom["coordinates"][0]]
            elif geom["type"] == "MultiPolygon":
                rings = [poly[0] for poly in geom["coordinates"]]
            else:
                continue
            for ring in rings:
                xs = [p[0] for p in ring]
                ys = [p[1] for p in ring]
                if alpha > 0:
                    ax.fill(xs, ys, color=color, alpha=alpha, linewidth=0)
                ax.plot(xs, ys, color=color, linewidth=lw)
            counts[kind] = counts.get(kind, 0) + 1

    # Then hole_line features with labels (tee→green routing)
    for feat in feats:
        if feat["properties"]["kind"] != "hole_line":
            continue
        line = feat["geometry"]["coordinates"]
        xs = [p[0] for p in line]
        ys = [p[1] for p in line]
        ax.plot(xs, ys, color="white", linewidth=1.4, alpha=0.7, linestyle="--")
        # Label near the middle of the line
        mid = line[len(line) // 2]
        ref = feat["properties"].get("hole_ref") or "?"
        par = feat["properties"].get("par") or "?"
        ax.annotate(
            f"H{ref}·P{par}", mid, fontsize=10, fontweight="bold", color="white",
            ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="#005f1f", edgecolor="white"),
            zorder=6,
        )
        counts["hole_line"] = counts.get("hole_line", 0) + 1

    legend = [mpatches.Patch(color=c_[0], alpha=max(c_[1], 0.3), label=k)
              for k, c_ in COLORS.items() if k in counts]
    ax.legend(handles=legend, loc="upper right", fontsize=10, framealpha=0.85)

    ax.set_title(
        f"{slug} — OSM-derived features\n" +
        "  ".join(f"{k}:{v}" for k, v in counts.items()),
        fontsize=13,
    )
    ax.set_xticks([]); ax.set_yticks([])

    out = c / "derived" / "features_osm_preview.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[osm-preview] wrote {out}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    args = ap.parse_args()
    render(args.course)


if __name__ == "__main__":
    main()
