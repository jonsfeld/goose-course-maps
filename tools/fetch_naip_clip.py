"""Fetch a NAIP aerial-imagery clip for a course bbox from the USGS NAIPImagery ImageServer.

Produces a 4-band (R/G/B/NIR) GeoTIFF at sources/imagery/naip_clip.tif.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import requests

from _common import bbox_from_course, course_dir, ensure_dir


IMAGE_SERVER = (
    "https://imagery.nationalmap.gov/arcgis/rest/services/"
    "USGSNAIPImagery/ImageServer/exportImage"
)


def fetch(slug: str, width: int = 4096, height: int = 4096) -> Path:
    minx, miny, maxx, maxy = bbox_from_course(slug)

    out_dir = ensure_dir(course_dir(slug) / "sources" / "imagery")
    out_path = out_dir / "naip_clip.tif"

    params = {
        "bbox": f"{minx},{miny},{maxx},{maxy}",
        "bboxSR": 4326,
        "imageSR": 4326,
        "size": f"{width},{height}",
        "format": "tiff",
        "pixelType": "U8",
        "interpolation": "RSP_BilinearInterpolation",
        "f": "image",
    }

    print(f"[naip] bbox {minx:.5f},{miny:.5f},{maxx:.5f},{maxy:.5f}")
    print(f"[naip] requesting {width}x{height} clip from {IMAGE_SERVER}")

    r = requests.get(IMAGE_SERVER, params=params, timeout=120, stream=True)
    r.raise_for_status()

    with out_path.open("wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 20):
            f.write(chunk)

    size_mb = out_path.stat().st_size / 1e6
    print(f"[naip] wrote {out_path} ({size_mb:.1f} MB)")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True, help="Course slug (e.g. roosevelt_la)")
    ap.add_argument("--width", type=int, default=4096, help="Output pixel width")
    ap.add_argument("--height", type=int, default=4096, help="Output pixel height")
    args = ap.parse_args()

    fetch(args.course, args.width, args.height)


if __name__ == "__main__":
    main()
