"""Fetch high-detail layers for individual holes (map prototype, Nov 2026).

For each requested hole:
  1. Green surface points: lidar GROUND points (class 2) inside the hole's green
     (plus a 12 m apron) from the USGS 3DEP EPT copy on AWS, via PDAL.
       -> courses/<slug>/derived/holes/hole_<n>_green_ground.csv.gz  (x,y,z in UTM metres)
  2. Aerial photo: a NAIP clip of the whole hole (tee to green + 70 m margin),
     reprojected to UTM so it lines up with the vector layers.
       -> courses/<slug>/derived/holes/hole_<n>_naip.png  (+ hole_<n>_naip.json bounds)

The green is the OSM green polygon nearest the hole's green_center, NOT the
`green.osm_id` stored in hole_data.json (that pairing is wrong on courses that
share hole numbers with a neighbouring course, e.g. Harding + Fleming).

    python3 tools/fetch_hole_detail.py --course tpc_harding_park --holes 14
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import os
import shutil
import subprocess

import requests
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform as shp_transform

from _common import course_dir, ensure_dir
from fetch_points_ept import BUCKET, UA, ept_bounds_ok, utm_epsg

NAIP = "https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer/exportImage"


def pdal_bin() -> str:
    p = os.environ.get("PDAL_BIN", "")
    if p and os.path.exists(p):
        return p
    p = shutil.which("pdal")
    if not p:
        raise SystemExit("[detail] pdal not installed")
    return p


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    ap.add_argument("--holes", nargs="+", type=int, required=True)
    ap.add_argument("--px-per-m", type=float, default=3.0, help="aerial clip resolution (NAIP native is ~0.6 m)")
    a = ap.parse_args()
    cdir = course_dir(a.course)
    hd = json.loads((cdir / "derived" / "hole_data.json").read_text())
    fc = json.loads((cdir / "derived" / "features_osm.geojson").read_text())
    notes = json.loads((cdir / "notes" / "lidar_sources.json").read_text())
    ept_name = notes.get("point_cloud", {}).get("project")
    out = ensure_dir(cdir / "derived" / "holes")

    h0 = hd["holes"][0]["hole_line"]["tee"]
    epsg = utm_epsg(h0["lng"], h0["lat"])
    to_utm = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    to_merc = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:3857", always_xy=True)
    greens = [(f["properties"]["osm_id"], shp_transform(lambda x, y, z=None: to_utm.transform(x, y), shape(f["geometry"])))
              for f in fc["features"] if f["properties"].get("kind") == "green"]

    for n in a.holes:
        holes = [h for h in hd["holes"] if h["hole"] == n]
        if not holes:
            print(f"[detail] hole {n}: not found")
            continue
        h = max(holes, key=lambda h: h["hole_line"]["length_m"]) if len(holes) > 1 else holes[0]
        if len(holes) > 1:
            print(f"[detail] hole {n}: {len(holes)} entries share this number; using the longest")
        tee, gc = h["hole_line"]["tee"], h["hole_line"]["green_center"]
        tx, ty = to_utm.transform(tee["lng"], tee["lat"])
        gx, gy = to_utm.transform(gc["lng"], gc["lat"])
        gid, gpoly = min(greens, key=lambda g: g[1].distance(Point(gx, gy)))
        print(f"[detail] hole {n}: green osm {gid} ({gpoly.area:.0f} m2)")

        # 1. green ground points
        if ept_name:
            minx, miny, maxx, maxy = gpoly.buffer(12).bounds
            mx0, my0 = to_merc.transform(minx, miny)
            mx1, my1 = to_merc.transform(maxx, maxy)
            tmp = out / f"_tmp_{n}.csv"
            pipe = {"pipeline": [
                {"type": "readers.ept", "filename": f"{BUCKET}/{ept_name}/ept.json",
                 "bounds": f"([{mx0:.2f}, {mx1:.2f}], [{my0:.2f}, {my1:.2f}])", "threads": 8},
                {"type": "filters.range", "limits": "Classification[2:2]"},
                {"type": "filters.reprojection", "out_srs": f"EPSG:{epsg}"},
                {"type": "writers.text", "filename": str(tmp), "format": "csv", "order": "X,Y,Z",
                 "keep_unspecified": False, "precision": 3},
            ]}
            try:
                subprocess.run([pdal_bin(), "pipeline", "--stdin"], input=json.dumps(pipe).encode(), check=True)
                rows = tmp.read_text().splitlines()
                with gzip.open(out / f"hole_{n}_green_ground.csv.gz", "wt") as f:
                    f.write("\n".join(rows))
                tmp.unlink()
                print(f"[detail] hole {n}: {len(rows)-1} ground points around the green")
            except Exception as e:
                print(f"[detail] hole {n}: green points FAILED: {e}")
        else:
            print("[detail] no EPT project in notes/lidar_sources.json; skipping green points")

        # 2. aerial clip of the hole, in UTM
        bx0, by0, bx1, by1 = Point(tx, ty).union(gpoly).buffer(70).bounds
        w = min(4000, int((bx1 - bx0) * a.px_per_m))
        hgt = min(4000, int((by1 - by0) * a.px_per_m))
        params = {"bbox": f"{bx0},{by0},{bx1},{by1}", "bboxSR": epsg, "imageSR": epsg,
                  "size": f"{w},{hgt}", "format": "png", "pixelType": "U8", "bandIds": "0,1,2",
                  "interpolation": "RSP_CubicConvolution", "f": "image"}
        try:
            r = requests.get(NAIP, params=params, headers=UA, timeout=180)
            r.raise_for_status()
            if "image" not in r.headers.get("content-type", ""):
                raise RuntimeError(r.text[:300])
            (out / f"hole_{n}_naip.png").write_bytes(r.content)
            (out / f"hole_{n}_naip.json").write_text(json.dumps(
                {"epsg": epsg, "bounds": [bx0, by0, bx1, by1], "size": [w, hgt], "source": "USGS NAIP ImageServer",
                 "green_osm_id": gid}, indent=2))
            print(f"[detail] hole {n}: aerial clip {w}x{hgt} ({len(r.content)/1e6:.1f} MB)")
        except Exception as e:
            print(f"[detail] hole {n}: aerial clip FAILED: {e}")


if __name__ == "__main__":
    main()
