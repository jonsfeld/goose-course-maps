"""Fetch public USGS 3DEP elevation + lidar point clouds for a course bbox.

No API keys, no manual downloads. Two products:

1. Bare-earth DEM (1 m): exported straight from the USGS 3DEP Elevation
   ImageServer for exactly the course bbox, in the bbox's UTM zone.
   -> courses/<slug>/sources/dem/3dep_1m.tif
   This service serves the best available 3DEP elevation (newest lidar
   where it exists), so we never download whole 10 km tiles.

2. Lidar point cloud (LAZ): tiles from the USGS TNM Access API that
   intersect the bbox, from the NEWEST lidar project covering the course.
   -> courses/<slug>/sources/point_cloud/*.laz
   Used for the canopy height model (trees) and finer green surfaces.

Writes courses/<slug>/notes/lidar_sources.json recording exactly which
products were used (provenance for every layer).

    python3 tools/fetch_lidar.py --course tpc_harding_park
"""
from __future__ import annotations

import argparse
import json
import math
import re
import time
from pathlib import Path

import requests

from _common import bbox_from_course, course_dir, ensure_dir

UA = {"User-Agent": "goose-course-maps/0.2 (public-data pipeline)"}
DEM_SERVICE = "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage"
TNM_API = "https://tnmaccess.nationalmap.gov/api/v1/products"


def utm_epsg(lon: float, lat: float) -> int:
    zone = int((lon + 180) // 6) + 1
    return (32600 if lat >= 0 else 32700) + zone


def fetch_dem(slug: str, bbox) -> dict:
    minx, miny, maxx, maxy = bbox
    lat0 = (miny + maxy) / 2
    w_m = (maxx - minx) * 111320 * math.cos(math.radians(lat0))
    h_m = (maxy - miny) * 110540
    # 1 m pixels; ImageServer caps a single export around 4000-8000 px a side.
    w_px, h_px = min(int(w_m) + 1, 6000), min(int(h_m) + 1, 6000)
    params = {
        "bbox": f"{minx},{miny},{maxx},{maxy}", "bboxSR": 4326,
        "imageSR": utm_epsg((minx + maxx) / 2, lat0),
        "size": f"{w_px},{h_px}", "format": "tiff", "pixelType": "F32",
        "interpolation": "RSP_BilinearInterpolation", "f": "image",
    }
    out = ensure_dir(course_dir(slug) / "sources" / "dem") / "3dep_1m.tif"
    for attempt in range(4):
        r = requests.get(DEM_SERVICE, params=params, headers=UA, timeout=300)
        if r.ok and r.content[:2] in (b"II", b"MM"):
            out.write_bytes(r.content)
            print(f"[dem] {w_px}x{h_px} px (~1 m) -> {out} ({len(r.content)/1e6:.1f} MB)")
            return {"product": "USGS 3DEP Elevation ImageServer (best available)", "url": DEM_SERVICE,
                    "pixels": [w_px, h_px], "epsg": params["imageSR"]}
        print(f"[dem] attempt {attempt+1} failed: HTTP {r.status_code} {r.text[:200]!r}")
        time.sleep(10 * (attempt + 1))
    raise SystemExit("[dem] could not export DEM")


def _project_key(item: dict) -> str:
    # Titles look like "USGS Lidar Point Cloud CA_SanFrancisco_2023_A23 10SEG4512..."
    t = item.get("title", "")
    m = re.search(r"Point Cloud\s+(\S+)", t)
    return m.group(1) if m else t


def _year(item: dict) -> int:
    m = re.findall(r"(19|20)\d{2}", _project_key(item))
    yrs = [int(y) for y in re.findall(r"(?:19|20)\d{2}", _project_key(item))]
    if yrs:
        return max(yrs)
    d = item.get("publicationDate") or item.get("dateCreated") or "1900"
    return int(d[:4])


def _mirrors(url: str) -> list[str]:
    """USGS stages the same LAZ files on rockyweb and on its public S3 bucket."""
    out = []
    if "rockyweb.usgs.gov/vdelivery/Datasets/Staged/" in url:
        out.append(url.replace("https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/",
                               "https://prd-tnm.s3.amazonaws.com/StagedProducts/"))
    out.append(url)
    return out


def _download(url: str, dest: Path) -> None:
    last = None
    for attempt in range(4):
        for u in _mirrors(url):
            try:
                with requests.get(u, headers=UA, timeout=(20, 120), stream=True) as resp:
                    if resp.status_code in (429, 502, 503):
                        last = f"HTTP {resp.status_code} from {u}"
                        continue
                    resp.raise_for_status()
                    tmp = dest.with_suffix(".part")
                    with tmp.open("wb") as f:
                        for chunk in resp.iter_content(1 << 20):
                            f.write(chunk)
                    tmp.rename(dest)
                    return
            except requests.RequestException as e:
                last = f"{e} ({u})"
        time.sleep(15 * (attempt + 1))
    raise SystemExit(f"[lpc] failed to download {url}: {last}")


def fetch_lpc(slug: str, bbox, max_tiles: int) -> dict:
    minx, miny, maxx, maxy = bbox
    items, offset = [], 0
    while True:
        r = requests.get(TNM_API, params={
            "datasets": "Lidar Point Cloud (LPC)", "bbox": f"{minx},{miny},{maxx},{maxy}",
            "outputFormat": "JSON", "max": 200, "offset": offset,
        }, headers=UA, timeout=120)
        r.raise_for_status()
        js = r.json()
        batch = js.get("items", [])
        items += batch
        if len(batch) < 200:
            break
        offset += 200
    items = [i for i in items if str(i.get("downloadURL", "")).lower().endswith(".laz")]
    if not items:
        print("[lpc] no LAZ tiles found for this bbox")
        return {"product": None}
    projects: dict[str, list] = {}
    for i in items:
        projects.setdefault(_project_key(i), []).append(i)
    newest = max(projects, key=lambda k: (_year(projects[k][0]), len(projects[k])))
    chosen = projects[newest][:max_tiles]
    print(f"[lpc] {len(items)} tiles across {len(projects)} projects; using newest: {newest} ({len(chosen)} tiles)")
    out_dir = ensure_dir(course_dir(slug) / "sources" / "point_cloud")
    from concurrent.futures import ThreadPoolExecutor, as_completed
    t0 = time.time()

    def one(i):
        url = i["downloadURL"]
        dest = out_dir / url.split("/")[-1]
        if dest.exists() and dest.stat().st_size > 0:
            return dest.name, dest.stat().st_size, 0.0
        s0 = time.time()
        _download(url, dest)
        return dest.name, dest.stat().st_size, time.time() - s0

    failed = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(one, i): i for i in chosen}
        for f in as_completed(futs):
            try:
                name, size, secs = f.result()
                print(f"[lpc]   {name} {size/1e6:.0f} MB in {secs:.0f}s", flush=True)
            except BaseException as e:  # SystemExit from _download included
                failed.append(futs[f]["downloadURL"])
                print(f"[lpc]   FAILED {futs[f]['downloadURL'].split('/')[-1]}: {e}", flush=True)
    print(f"[lpc] {len(chosen) - len(failed)}/{len(chosen)} tiles in {time.time() - t0:.0f}s", flush=True)
    return {"product": "USGS 3DEP Lidar Point Cloud", "project": newest, "year": _year(chosen[0]),
            "tiles": [i["downloadURL"] for i in chosen], "failed_tiles": failed,
            "other_projects": sorted(k for k in projects if k != newest)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    ap.add_argument("--skip-lpc", action="store_true")
    ap.add_argument("--only", choices=["dem", "lpc"], default=None)
    ap.add_argument("--max-tiles", type=int, default=16)
    a = ap.parse_args()
    bbox = bbox_from_course(a.course)
    record = {"bbox": bbox, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    notes_path = course_dir(a.course) / "notes" / "lidar_sources.json"
    if notes_path.exists():
        record = {**json.loads(notes_path.read_text()), **record}
    if a.only in (None, "dem"):
        record["dem"] = fetch_dem(a.course, bbox)
    if a.only in (None, "lpc") and not a.skip_lpc:
        record["point_cloud"] = fetch_lpc(a.course, bbox, a.max_tiles)
    notes = ensure_dir(course_dir(a.course) / "notes")
    (notes / "lidar_sources.json").write_text(json.dumps(record, indent=2))
    print(f"[lidar] provenance -> {notes / 'lidar_sources.json'}")


if __name__ == "__main__":
    main()
