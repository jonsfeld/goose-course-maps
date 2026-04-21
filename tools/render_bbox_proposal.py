"""Render a NAIP image with proposed (and existing) bbox polygons overlaid,
so a human can approve a tightened course bbox before re-running derivation.

Usage:
  python3 render_bbox_proposal.py --course roosevelt_la \
      --proposed-bbox -118.3005 34.1222 -118.2920 34.1280
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio

from _common import bbox_from_course, course_dir, ensure_dir


def render(slug: str, proposed: tuple[float, float, float, float]) -> Path:
    c = course_dir(slug)
    naip_path = c / "sources" / "imagery" / "naip_clip.tif"
    if not naip_path.exists():
        raise FileNotFoundError(naip_path)

    with rasterio.open(naip_path) as src:
        rgb = src.read([1, 2, 3]).transpose(1, 2, 0).astype("float32") / 255.0
        bounds = src.bounds

    extent = (bounds.left, bounds.right, bounds.bottom, bounds.top)

    cur_minx, cur_miny, cur_maxx, cur_maxy = bbox_from_course(slug)
    prop_minx, prop_miny, prop_maxx, prop_maxy = proposed

    fig, ax = plt.subplots(1, 1, figsize=(14, 14))
    ax.imshow(np.clip(rgb, 0, 1), extent=extent)

    # Current bbox (red, dashed) — the wide one from Phase A
    rect_cur = plt.Rectangle(
        (cur_minx, cur_miny),
        cur_maxx - cur_minx,
        cur_maxy - cur_miny,
        linewidth=2.0, edgecolor="red", facecolor="none",
        linestyle="--", label="Current bbox (Phase A)",
    )
    ax.add_patch(rect_cur)

    # Proposed tight bbox (cyan, solid)
    rect_prop = plt.Rectangle(
        (prop_minx, prop_miny),
        prop_maxx - prop_minx,
        prop_maxy - prop_miny,
        linewidth=2.5, edgecolor="cyan", facecolor="none",
        label="Proposed tight bbox",
    )
    ax.add_patch(rect_prop)

    # Legend + info
    cur_area_km2 = (
        (cur_maxx - cur_minx) * 111_000
        * (cur_maxy - cur_miny) * 111_000 * np.cos(np.radians((cur_miny + cur_maxy) / 2))
    ) / 1e6
    prop_area_km2 = (
        (prop_maxx - prop_minx) * 111_000
        * (prop_maxy - prop_miny) * 111_000 * np.cos(np.radians((prop_miny + prop_maxy) / 2))
    ) / 1e6
    ax.set_title(
        f"{slug} — bbox comparison\n"
        f"Current: {cur_area_km2:.2f} km²  →  Proposed: {prop_area_km2:.2f} km² "
        f"({prop_area_km2/cur_area_km2*100:.0f}% of current)",
        fontsize=14,
    )
    ax.legend(loc="upper right", fontsize=11)
    ax.set_xticks([])
    ax.set_yticks([])

    out_path = c / "derived" / "bbox_proposal.png"
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"[bbox-proposal] wrote {out_path}")
    print(
        f"[bbox-proposal] current {cur_minx:.5f},{cur_miny:.5f},{cur_maxx:.5f},{cur_maxy:.5f} "
        f"({cur_area_km2:.2f} km²)"
    )
    print(
        f"[bbox-proposal] proposed {prop_minx:.5f},{prop_miny:.5f},{prop_maxx:.5f},{prop_maxy:.5f} "
        f"({prop_area_km2:.2f} km²)"
    )
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    ap.add_argument(
        "--proposed-bbox", nargs=4, type=float, required=True,
        metavar=("MINX", "MINY", "MAXX", "MAXY"),
        help="minx miny maxx maxy in WGS-84 decimal degrees",
    )
    args = ap.parse_args()
    render(args.course, tuple(args.proposed_bbox))


if __name__ == "__main__":
    main()
