"""Render NAIP + the v1-picked green polygons labeled by centroid_id."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from shapely.geometry import shape as shp

from _common import course_dir


def render(slug: str) -> Path:
    c = course_dir(slug)
    naip_path = c / "sources" / "imagery" / "naip_clip.tif"
    greens_path = c / "derived" / "greens_picked.geojson"
    seeds_path = c / "notes" / "green_centroids_draft.geojson"

    with rasterio.open(naip_path) as src:
        rgb = src.read([1, 2, 3]).transpose(1, 2, 0).astype("float32") / 255.0
        b = src.bounds
    extent = (b.left, b.right, b.bottom, b.top)

    with greens_path.open() as f:
        feats = json.load(f)["features"]
    with seeds_path.open() as f:
        seeds = json.load(f)["features"]

    fig, ax = plt.subplots(figsize=(20, 14))
    ax.imshow(np.clip(rgb, 0, 1), extent=extent)

    # Draw all original seed points faintly (yellow circles)
    for s in seeds:
        sid = s["properties"].get("centroid_id") or s["properties"].get("hole")
        x, y = s["geometry"]["coordinates"]
        ax.scatter([x], [y], s=120, facecolor="none", edgecolor="yellow",
                   linewidths=1.5, zorder=4)
        ax.annotate(str(sid), (x, y), fontsize=9, color="yellow",
                    ha="center", va="center", alpha=0.7, zorder=4)

    # Draw picked green polygons (bright green fill + white outline)
    picked_ids = set()
    for feat in feats:
        cid = feat["properties"].get("centroid_id")
        area = feat["properties"].get("area_m2", "?")
        source = feat["properties"].get("kind_source", "?")
        geom = feat["geometry"]
        rings = [geom["coordinates"][0]] if geom["type"] == "Polygon" else [p[0] for p in geom["coordinates"]]
        for ring in rings:
            xs = [p[0] for p in ring]
            ys = [p[1] for p in ring]
            ax.fill(xs, ys, color="#00ff88", alpha=0.55, linewidth=0)
            ax.plot(xs, ys, color="white", linewidth=1.4)
        centroid = shp(geom).centroid
        ax.annotate(
            f"#{cid}\n{area:.0f}m²\n({source})" if isinstance(area, (int, float)) else str(cid),
            (centroid.x, centroid.y),
            fontsize=10, fontweight="bold", color="white",
            ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#005f1f", edgecolor="white"),
            zorder=6,
        )
        picked_ids.add(cid)

    missing = [s["properties"].get("centroid_id") for s in seeds
               if s["properties"].get("centroid_id") not in picked_ids]

    ax.set_title(
        f"Roosevelt GC — v1-picked greens ({len(feats)} of {len(seeds)})\n"
        f"Green fill = picked polygon; yellow ring = seed placement; "
        f"{'missing: ' + ','.join(str(m) for m in missing) if missing else 'all seeds matched'}",
        fontsize=12,
    )
    ax.set_xticks([]); ax.set_yticks([])

    out = c / "derived" / "greens_picked_preview.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"[picked-preview] wrote {out}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    args = ap.parse_args()
    render(args.course)


if __name__ == "__main__":
    main()
