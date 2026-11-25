#!/usr/bin/env python3
"""Check every hole's centerline before a course is published.

Fails (exit 1) when, on a par 4 or 5:
  - the line runs over fairway for less than MIN_ON_FAIRWAY of its middle stretch (tee area and
    green approach excluded), or
  - the line is a bare straight tee->green segment although the course maps a bent golf=hole line.
Warns when the line's length is outside the published scorecard range (notes/scorecard.json).

Why: Roosevelt 5's hole view once drew a straight line through the trees on a dogleg left because
two scripts chose the line by different rules. hole_data.json's hole_line.coords is now the one
line; this check makes sure it is a sensible one.

Usage: python3 tools/check_hole_lines.py [course ...]   (default: every course)
"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import pick_holes
from build_hole_data import _fairway_cover
from shapely.geometry import shape, LineString
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
MIN_ON_FAIRWAY = 0.60


def metres(lon, lat, lat0):
    return (lon * 111320 * math.cos(math.radians(lat0)), lat * 110540)


def check(course: str) -> int:
    cdir = ROOT / "courses" / course
    hd = json.loads((cdir / "derived" / "hole_data.json").read_text())
    holes = hd["holes"] if isinstance(hd, dict) else hd
    fc = json.loads((cdir / "derived" / "features_osm.geojson").read_text())
    # Main course only (Harding shares hole numbers with Fleming 9).
    holes = [h for _, h in sorted(pick_holes(holes, fc).items())]
    feats = list(fc["features"])
    traced = cdir / "notes" / "traced_features.geojson"
    if traced.exists():
        feats += json.loads(traced.read_text())["features"]
    card = {}
    sc = cdir / "notes" / "scorecard.json"
    if sc.exists():
        tees = json.loads(sc.read_text()).get("tees", {})
        for vals in tees.values():
            for i, v in enumerate(vals):
                if isinstance(v, (int, float)):
                    card.setdefault(i + 1, []).append(v)
    lat0 = holes[0]["hole_line"]["tee"]["lat"]
    to_m = lambda g: shape({"type": g["type"], "coordinates": _map(g["coordinates"], lat0)})
    fairway = unary_union([to_m(f["geometry"]).buffer(0) for f in feats if f["properties"].get("kind") == "fairway"])
    bent = {}
    for f in feats:
        p = f["properties"]
        if p.get("kind") == "hole_line" and len(f["geometry"]["coordinates"]) > 2:
            bent.setdefault(str(p.get("hole_ref")), []).append(f)
    fails = 0
    for h in holes:
        hl = h["hole_line"]
        coords = hl.get("coords") or []
        tag = f"{course} hole {h['hole']} (par {h.get('par')})"
        if len(coords) < 2:
            print(f"FAIL {tag}: no centerline coords"); fails += 1; continue
        line = LineString([metres(x, y, lat0) for x, y in coords])
        if (h.get("par") or 0) >= 4:
            on = _fairway_cover(line, fairway)
            straight = len(coords) == 2
            if straight and str(h["hole"]) in bent and on < 0.9:
                print(f"FAIL {tag}: drawn as a straight tee->green line, but the course maps a bent hole line"); fails += 1
            elif on < MIN_ON_FAIRWAY:
                print(f"FAIL {tag}: once it reaches the fairway, the line stays on it only {on:.0%} of the way"); fails += 1
            else:
                print(f"ok   {tag}: {on:.0%} over fairway, {hl['length_yd']:.0f} y")
        else:
            print(f"ok   {tag}: {hl['length_yd']:.0f} y")
        v = card.get(h["hole"])
        if v and not (min(v) * 0.95 <= hl["length_yd"] <= max(v) * 1.05):
            print(f"WARN {tag}: {hl['length_yd']:.0f} y is outside the card ({min(v)}–{max(v)})")
    return fails


def _map(c, lat0):
    if isinstance(c[0], (int, float)):
        return list(metres(c[0], c[1], lat0))
    return [_map(x, lat0) for x in c]


if __name__ == "__main__":
    courses = sys.argv[1:] or sorted(p.name for p in (ROOT / "courses").iterdir() if (p / "derived" / "hole_data.json").exists())
    total = sum(check(c) for c in courses)
    print(f"\n{total} failing hole(s)")
    sys.exit(1 if total else 0)
