"""Shared helpers for Phase C scripts."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def course_dir(slug: str) -> Path:
    p = REPO_ROOT / "courses" / slug
    if not p.exists():
        raise FileNotFoundError(f"Course directory not found: {p}")
    return p


def bbox_from_course(slug: str) -> tuple[float, float, float, float]:
    """Return (minx, miny, maxx, maxy) in WGS-84 from notes/bbox.geojson."""
    bbox_file = course_dir(slug) / "notes" / "bbox.geojson"
    with bbox_file.open() as f:
        gj = json.load(f)
    coords = gj["features"][0]["geometry"]["coordinates"][0]
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return min(xs), min(ys), max(xs), max(ys)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def pick_holes(holes: list[dict], features: dict | None = None) -> dict[int, dict]:
    """One entry per hole number for the main course.

    Some courses share hole numbers with a neighbouring course (TPC Harding Park +
    Fleming 9). Every combination of the shared entries is scored (at most 2^9), preferring:
      1. stroke-index handicaps with no repeats (the main course's 18 holes carry 1..18),
         read from the OSM hole line that starts at each entry's tee;
      2. the higher total par (the main course is the full-length one);
      3. the shortest total walk from each green to the next tee.
    """
    import itertools
    by_n: dict[int, list[dict]] = {}
    for h in holes:
        by_n.setdefault(h["hole"], []).append(h)
    nums = sorted(by_n)
    dup = [n for n in nums if len(by_n[n]) > 1]
    if not dup:
        return {n: by_n[n][0] for n in nums}

    lines = []
    for f in (features or {}).get("features", []):
        p = f["properties"]
        if p.get("kind") == "hole_line" and f["geometry"]["type"] == "LineString":
            lines.append((p.get("hole_ref"), p.get("handicap"), f["geometry"]["coordinates"][0]))

    def hcp(h):
        t = h["hole_line"]["tee"]
        best = None
        for ref, hc, (x, y, *_) in lines:
            d = ((y - t["lat"]) ** 2 + ((x - t["lng"]) * 0.79) ** 2) ** 0.5
            if str(ref) == str(h["hole"]) and d < 0.0003 and (best is None or d < best[0]):
                best = (d, hc)
        return best[1] if best else None

    def gap(a, b):
        g, t = a["hole_line"]["green_center"], b["hole_line"]["tee"]
        return ((g["lat"] - t["lat"]) ** 2 + ((g["lng"] - t["lng"]) * 0.79) ** 2) ** 0.5

    best, best_key = None, None
    for combo in itertools.product(*[range(len(by_n[n])) for n in dup]):
        pick = {n: by_n[n][0] for n in nums}
        pick.update({n: by_n[n][c] for n, c in zip(dup, combo)})
        hs = [hcp(pick[n]) for n in nums]
        known = [x for x in hs if x not in (None, "")]
        hcp_ok = len(known) == len(set(known))
        par = sum(pick[n]["par"] or 0 for n in nums)
        walk = sum(gap(pick[n], pick[n + 1]) for n in nums if n + 1 in pick)
        key = (hcp_ok, len(known), par, -walk)
        if best_key is None or key > best_key:
            best, best_key = pick, key
    return best
