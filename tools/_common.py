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
