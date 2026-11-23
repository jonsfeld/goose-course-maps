"""Summarize what the public sources gave us for a course, hole by hole.

Reads derived/features_osm.geojson (+ optional hole_data.json, individual_trees.geojson,
notes/lidar_sources.json) and writes derived/coverage.json and derived/coverage.md.

    python3 tools/coverage_report.py --course tpc_harding_park
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

from shapely.geometry import shape

from _common import course_dir


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    slug = ap.parse_args().course
    c = course_dir(slug)
    d = c / "derived"
    feats = json.loads((d / "features_osm.geojson").read_text())["features"] if (d / "features_osm.geojson").exists() else []
    kinds = Counter(f["properties"].get("kind") for f in feats)
    holes = sorted([f for f in feats if f["properties"].get("kind") == "hole_line"],
                   key=lambda f: int(f["properties"].get("hole_ref") or 999) if str(f["properties"].get("hole_ref") or "").isdigit() else 999)

    per_hole = []
    polys = [(f["properties"].get("kind"), shape(f["geometry"])) for f in feats
             if f["geometry"]["type"] in ("Polygon", "MultiPolygon") and f["properties"].get("kind") != "course_boundary"]
    for h in holes:
        line = shape(h["geometry"])
        near = Counter()
        for k, g in polys:
            try:
                if g.distance(line) < 0.0004:  # ~40 m
                    near[k] += 1
            except Exception:
                pass
        per_hole.append({"hole": h["properties"].get("hole_ref"), "par": h["properties"].get("par"),
                         "green": near["green"], "fairway": near["fairway"], "tees": near["tee_box"],
                         "bunkers": near["bunker"], "water": near["water"], "woods": near["woods"]})

    trees = 0
    if (d / "individual_trees.geojson").exists():
        trees = len(json.loads((d / "individual_trees.geojson").read_text())["features"])
    lidar = json.loads((c / "notes" / "lidar_sources.json").read_text()) if (c / "notes" / "lidar_sources.json").exists() else {}
    hole_data = (d / "hole_data.json").exists()

    out = {"course": slug, "feature_counts": dict(kinds), "hole_lines": len(holes), "per_hole": per_hole,
           "trees_detected": trees, "hole_data_built": hole_data,
           "lidar_project": (lidar.get("point_cloud") or {}).get("project"),
           "lidar_year": (lidar.get("point_cloud") or {}).get("year"),
           "dem": (lidar.get("dem") or {}).get("product")}
    (d / "coverage.json").write_text(json.dumps(out, indent=2))

    md = [f"# Coverage — {slug}", "",
          f"- OSM features: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())),
          f"- Hole lines (golf=hole): {len(holes)}",
          f"- Lidar point cloud: {out['lidar_project']} ({out['lidar_year']})",
          f"- Trees detected from lidar: {trees}",
          f"- Per-hole terrain built: {'yes' if hole_data else 'no'}", "",
          "| Hole | Par | Green | Fairway | Tees | Bunkers | Water | Woods |", "|---|---|---|---|---|---|---|---|"]
    for r in per_hole:
        md.append(f"| {r['hole']} | {r['par']} | {r['green']} | {r['fairway']} | {r['tees']} | {r['bunkers']} | {r['water']} | {r['woods']} |")
    (d / "coverage.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
