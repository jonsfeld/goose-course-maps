"""Fetch only the lidar points inside a course bbox from the USGS 3DEP
Entwine Point Tile (EPT) copy on AWS (s3://usgs-lidar-public), via PDAL.

Why: the per-tile LAZ downloads from rockyweb.usgs.gov are throttled (HTTP 429)
and come in local coordinate systems (e.g. San Francisco CS13). The EPT copy is
in one coordinate system (Web Mercator) and can be queried by bounds, so we
download just the course's points and write them in the course's UTM zone.

  -> courses/<slug>/sources/point_cloud/ept_<resource>.laz   (EPSG:326xx, meters)
  -> notes/lidar_sources.json  ("point_cloud" entry updated)

Requires the `pdal` command-line tool (apt install pdal on Ubuntu).

    python3 tools/fetch_points_ept.py --course tpc_harding_park
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import time
import xml.etree.ElementTree as ET

import requests
from pyproj import Transformer

from _common import bbox_from_course, course_dir, ensure_dir

UA = {"User-Agent": "goose-course-maps/0.3"}
BUCKET = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public"
RESOURCES = "https://raw.githubusercontent.com/hobuinc/usgs-lidar/master/boundaries/resources.geojson"


def utm_epsg(lon: float, lat: float) -> int:
    return (32600 if lat >= 0 else 32700) + int((lon + 180) // 6) + 1


def _year(name: str) -> int:
    yrs = [int(y) for y in re.findall(r"(?:19|20)\d{2}", name)]
    m = re.search(r"_[A-Z](\d{2})$", name)  # e.g. CA_SanFrancisco_B23 -> 2023
    if m:
        yrs.append(2000 + int(m.group(1)))
    return max(yrs) if yrs else 0


def candidates_from_index(bbox) -> list[str]:
    """Resources whose boundary intersects the bbox, from the public index."""
    from shapely.geometry import box, shape
    r = requests.get(RESOURCES, headers=UA, timeout=120)
    r.raise_for_status()
    target = box(*bbox)
    out = []
    for f in r.json().get("features", []):
        try:
            if shape(f["geometry"]).intersects(target):
                out.append(f["properties"].get("name"))
        except Exception:
            continue
    return [n for n in out if n]


def candidates_from_listing(prefix: str) -> list[str]:
    """Fallback: list bucket prefixes (e.g. 'CA_') and keep those whose ept.json bounds cover the bbox."""
    names, token = [], None
    while True:
        params = {"list-type": "2", "prefix": prefix, "delimiter": "/"}
        if token:
            params["continuation-token"] = token
        r = requests.get(BUCKET + "/", params=params, headers=UA, timeout=120)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        ns = {"s": root.tag.split("}")[0].strip("{")}
        names += [p.find("s:Prefix", ns).text.rstrip("/") for p in root.findall("s:CommonPrefixes", ns)]
        nxt = root.find("s:NextContinuationToken", ns)
        if nxt is None:
            break
        token = nxt.text
    return names


def ept_bounds_ok(name: str, merc_bounds) -> bool:
    r = requests.get(f"{BUCKET}/{name}/ept.json", headers=UA, timeout=60)
    if not r.ok:
        return False
    b = r.json().get("bounds") or r.json().get("boundsConforming")
    xmin, ymin, _, xmax, ymax, _ = b
    return not (merc_bounds[2] < xmin or merc_bounds[0] > xmax or merc_bounds[3] < ymin or merc_bounds[1] > ymax)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    a = ap.parse_args()
    slug = a.course
    minx, miny, maxx, maxy = bbox_from_course(slug)
    to_merc = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    mx0, my0 = to_merc.transform(minx, miny)
    mx1, my1 = to_merc.transform(maxx, maxy)
    merc = (mx0, my0, mx1, my1)

    try:
        names = candidates_from_index((minx, miny, maxx, maxy))
        print(f"[ept] index: {len(names)} resources intersect the course: {names}")
    except Exception as e:
        print(f"[ept] index unavailable ({e}); listing the bucket")
        state = "CA_" if -125 < minx < -114 and 32 < miny < 42 else ""
        names = [n for n in candidates_from_listing(state) if ept_bounds_ok(n, merc)]
        print(f"[ept] listing: {names}")
    names = [n for n in names if ept_bounds_ok(n, merc)]
    if not names:
        raise SystemExit("[ept] no EPT resource covers this course")
    name = max(names, key=lambda n: (_year(n), n))
    print(f"[ept] using newest: {name} (year {_year(name)})")

    epsg = utm_epsg((minx + maxx) / 2, (miny + maxy) / 2)
    out_dir = ensure_dir(course_dir(slug) / "sources" / "point_cloud")
    for old in out_dir.glob("*.laz"):   # tile LAZs in other CRSs would confuse the CHM step
        old.unlink()
    out = out_dir / f"ept_{name}.laz"
    pipeline = {"pipeline": [
        {"type": "readers.ept", "filename": f"{BUCKET}/{name}/ept.json",
         "bounds": f"([{mx0:.2f}, {mx1:.2f}], [{my0:.2f}, {my1:.2f}])", "threads": 8},
        {"type": "filters.reprojection", "out_srs": f"EPSG:{epsg}"},
        {"type": "writers.las", "filename": str(out), "compression": "laszip",
         "a_srs": f"EPSG:{epsg}", "scale_x": 0.01, "scale_y": 0.01, "scale_z": 0.01,
         "offset_x": "auto", "offset_y": "auto", "offset_z": "auto"},
    ]}
    t0 = time.time()
    import shutil
    pdal = shutil.which("pdal")
    if not pdal:
        raise SystemExit("[ept] pdal not installed")
    subprocess.run([pdal, "pipeline", "--stdin"], input=json.dumps(pipeline).encode(), check=True)
    print(f"[ept] wrote {out.name} ({out.stat().st_size/1e6:.0f} MB) in {time.time()-t0:.0f}s, EPSG:{epsg}")

    notes = ensure_dir(course_dir(slug) / "notes") / "lidar_sources.json"
    rec = json.loads(notes.read_text()) if notes.exists() else {}
    rec["point_cloud"] = {"product": "USGS 3DEP lidar (EPT copy on AWS usgs-lidar-public)", "project": name,
                          "year": _year(name), "epsg": epsg, "file": out.name, "candidates": names}
    notes.write_text(json.dumps(rec, indent=2))


if __name__ == "__main__":
    main()
