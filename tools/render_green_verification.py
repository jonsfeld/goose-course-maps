"""Render NAIP with proposed green centroids labeled 1-9, plus the v1
detected green polygons, so the user can approve/correct per-hole
green placement before region-grow.

Input:  courses/<slug>/sources/imagery/naip_clip.tif
        courses/<slug>/notes/green_centroids_draft.geojson
        courses/<slug>/derived/features.geojson (v1 greens as context)
Output: courses/<slug>/derived/green_verification.png
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
    centroids_path = c / "notes" / "green_centroids_draft.geojson"
    features_path = c / "derived" / "features.geojson"

    with rasterio.open(naip_path) as src:
        rgb = src.read([1, 2, 3]).transpose(1, 2, 0).astype("float32") / 255.0
        b = src.bounds
    extent = (b.left, b.right, b.bottom, b.top)

    fig, ax = plt.subplots(figsize=(14, 14))
    ax.imshow(np.clip(rgb, 0, 1), extent=extent)

    # Draw v1 detected greens (faint cyan) for context
    with features_path.open() as f:
        feats = json.load(f)["features"]
    v1_greens = 0
    for feat in feats:
        if feat["properties"]["kind"] != "green":
            continue
        v1_greens += 1
        ring = feat["geometry"]["coordinates"][0]
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        ax.plot(xs, ys, color="cyan", linewidth=0.9, alpha=0.7)

    # Draw my proposed 9 green centroids + hole labels
    with centroids_path.open() as f:
        centroids = json.load(f)["features"]
    for c_ in centroids:
        props = c_["properties"]
        label = props.get("hole") or props.get("centroid_id") or props.get("provisional_hole") or "?"
        x, y = c_["geometry"]["coordinates"]
        ax.scatter([x], [y], s=180, marker="o",
                   facecolor="yellow", edgecolor="red", linewidths=2, zorder=5)
        ax.annotate(str(label), (x, y), fontsize=14, fontweight="bold",
                    color="white", ha="center", va="center", zorder=6)

    ax.set_title(
        f"Roosevelt GC — proposed 9 green centroids (yellow, labeled 1-9)\n"
        f"Cyan outlines = v1 classifier's {v1_greens} 'green' polygons for context",
        fontsize=13,
    )
    ax.set_xticks([]); ax.set_yticks([])

    out = c / "derived" / "green_verification.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"[greens] wrote {out}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    args = ap.parse_args()
    render(args.course)


if __name__ == "__main__":
    main()
