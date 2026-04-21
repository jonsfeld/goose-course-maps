"""Phase B (first-pass auto): trace course features from NAIP + derived rasters.

Produces a single `features.geojson` with polygons tagged by `kind`:
  tree_canopy, fairway, green, bunker, water, rough

Approach (no deep-learning yet — classical CV first pass):
  1. Align CHM, slope, DEM to NAIP pixel grid (upsample)
  2. Compute NDVI from NAIP R + NIR bands
  3. Build vegetation mask from NDVI
  4. Split vegetation: tree_canopy (CHM > 2m), mowed (CHM < 1m)
  5. Within mowed: split by slope + NDVI tiers → green vs fairway vs rough
  6. Non-vegetation split: bunker (bright sandy) vs water (blue-dominant) vs other
  7. Morphological clean-up (remove tiny noise, fill small holes)
  8. Polygonize each class, attach properties (kind, area_m2), write GeoJSON

Known limitations of this first pass (Phase B v1):
  - fringe / first-cut bands are too narrow to extract reliably → omitted
  - tee_box detection not attempted here (easier after hole assignment)
  - OB lines not derivable from imagery alone → omitted
  - hole assignment (which polygon belongs to which hole) not performed
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio import features as rio_features
from rasterio.warp import Resampling, reproject
from scipy import ndimage
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from _common import course_dir, ensure_dir


# Class labels used in the integer classification raster.
CLASS_BG        = 0
CLASS_TREE      = 1
CLASS_FAIRWAY   = 2
CLASS_GREEN     = 3
CLASS_BUNKER    = 4
CLASS_WATER     = 5
CLASS_ROUGH     = 6

CLASS_TO_KIND = {
    CLASS_TREE:    "tree_canopy",
    CLASS_FAIRWAY: "fairway",
    CLASS_GREEN:   "green",
    CLASS_BUNKER:  "bunker",
    CLASS_WATER:   "water",
    CLASS_ROUGH:   "rough",
}

# Tunables for the first-pass classifier.
CHM_TREE_THRESHOLD_M = 2.0       # CHM >= this → tree
CHM_MOWED_CEILING_M  = 1.0       # CHM <= this → mowed grass (fairway/green)
NDVI_VEG_THRESHOLD   = 0.15      # NDVI >= this → vegetation
FAIRWAY_MAX_SLOPE    = 5.0       # slope <= this → fairway candidate
GREEN_MAX_SLOPE      = 2.5       # tighter flat → green candidate
BUNKER_NDVI_MAX      = 0.10      # bunker must be non-vegetation
MIN_FEATURE_AREA_M2  = {
    "green":   180,      # typical putting green is 200-600 m^2
    "fairway": 800,      # fairways are large
    "bunker":  12,       # smallest playable bunker ~15 m^2
    "water":   30,
    "tree_canopy": 15,
    "rough":   300,
}
# After classification, bunkers must be within this distance of mowed grass
# to count as golf-course bunkers (vs hillside chaparral).
BUNKER_ADJACENCY_RADIUS_M = 5.0    # bunkers must be within 5m of mowed grass
BUNKER_SURROUND_FRAC = 0.20        # ≥20% of 3m-radius shell is mowed grass


def _resample_to_grid(src_path: Path, ref_transform, ref_shape, ref_crs,
                      valid_min: float = 0.0, valid_max: float = 1e6) -> np.ndarray:
    """Resample src raster to the reference NAIP grid.

    After resampling, values outside [valid_min, valid_max] are clamped to valid_min.
    This suppresses nodata leak from bilinear interpolation near boundaries.
    """
    with rasterio.open(src_path) as src:
        src_nodata = src.nodata
        # Read into a masked array so nodata is handled correctly
        arr = src.read(1).astype("float32")
        if src_nodata is not None:
            arr = np.where(arr == src_nodata, np.nan, arr)
        # Write a cleaned temp source without the bad nodata sentinel
        src_meta = src.meta.copy()
        src_meta.update({"dtype": "float32", "nodata": np.nan})

    # Reproject, passing nan-cleaned source
    out = np.zeros(ref_shape, dtype="float32")
    # We need to pass the cleaned array back through reproject. Easiest:
    # write to memory via rasterio.MemoryFile.
    with rasterio.MemoryFile() as memfile:
        with memfile.open(**src_meta) as memsrc:
            memsrc.write(arr, 1)
            reproject(
                source=rasterio.band(memsrc, 1),
                destination=out,
                src_transform=memsrc.transform,
                src_crs=memsrc.crs,
                dst_transform=ref_transform,
                dst_crs=ref_crs,
                resampling=Resampling.bilinear,
                src_nodata=np.nan,
                dst_nodata=np.nan,
            )
    # Replace nan with valid_min, then clamp
    out = np.where(np.isnan(out), valid_min, out)
    out = np.clip(out, valid_min, valid_max)
    return out


def _approx_cellsize_m(transform, bounds) -> float:
    lat = (bounds.top + bounds.bottom) / 2
    px_x_m = abs(transform.a) * 111_000 * math.cos(math.radians(lat))
    px_y_m = abs(transform.e) * 111_000
    return (px_x_m + px_y_m) / 2.0


def _polygonize(mask: np.ndarray, transform, kind: str, min_area_m2: float, cell_area_m2: float):
    """Extract polygons from a binary mask; drop polygons below min_area_m2."""
    shapes = rio_features.shapes(
        mask.astype("uint8"), mask=mask.astype(bool), transform=transform, connectivity=8,
    )
    feats = []
    for geom, _val in shapes:
        poly = shape(geom)
        pixel_count = int(poly.area / abs(transform.a * transform.e))
        area_m2 = pixel_count * cell_area_m2
        if area_m2 < min_area_m2:
            continue
        feats.append({
            "type": "Feature",
            "properties": {"kind": kind, "area_m2": round(area_m2, 1)},
            "geometry": mapping(poly),
        })
    return feats


def classify(slug: str) -> Path:
    c = course_dir(slug)
    naip_path = c / "sources" / "imagery" / "naip_clip.tif"
    chm_path = c / "derived" / "canopy_height_model.tif"
    slope_path = c / "derived" / "slope.tif"

    for p in (naip_path, chm_path, slope_path):
        if not p.exists():
            raise FileNotFoundError(p)

    # Reference grid = NAIP (highest resolution).
    with rasterio.open(naip_path) as src:
        naip = src.read().astype("float32")                  # (4, H, W)
        naip_transform = src.transform
        naip_shape = src.shape
        naip_bounds = src.bounds
        naip_crs = src.crs
        naip_meta = src.meta.copy()

    r, g, b, nir = naip[0], naip[1], naip[2], naip[3]
    print(f"[trace] NAIP {naip_shape}, 4-band, extent {naip_bounds}")

    cell_m = _approx_cellsize_m(naip_transform, naip_bounds)
    cell_area_m2 = cell_m ** 2
    print(f"[trace] cellsize ~{cell_m:.3f} m, cell area {cell_area_m2:.3f} m²")

    # Resample CHM + slope to NAIP grid (with nodata handled)
    chm = _resample_to_grid(chm_path, naip_transform, naip_shape, naip_crs,
                            valid_min=0.0, valid_max=80.0)
    slope = _resample_to_grid(slope_path, naip_transform, naip_shape, naip_crs,
                              valid_min=0.0, valid_max=90.0)
    print(f"[trace] CHM resampled: min {chm.min():.1f} max {chm.max():.1f} mean {chm.mean():.1f}")
    print(f"[trace] slope resampled: min {slope.min():.1f} max {slope.max():.1f} mean {slope.mean():.1f}")

    # --- Spectral indices ---
    # NDVI = (NIR - R) / (NIR + R)  (range -1 to +1)
    eps = 1e-6
    ndvi = (nir - r) / (nir + r + eps)

    # Blueness (water detector): normalized blue dominance
    blueness = (b - (r + g) / 2.0) / (b + r + g + eps)

    # Sand/bunker index: bright R+G, low NDVI
    brightness = (r + g + b) / 3.0
    sand_score = (brightness / 255.0) * (1.0 - np.clip(ndvi, 0, 1))

    # --- Masks ---
    veg_mask = ndvi >= NDVI_VEG_THRESHOLD
    tree_mask = (chm >= CHM_TREE_THRESHOLD_M) & veg_mask
    mowed_mask = veg_mask & (chm <= CHM_MOWED_CEILING_M)

    water_mask = (blueness > 0.12) & (~veg_mask) & (brightness < 180)
    # Bunker: sand-colored, flat, non-vegetated — but chaparral matches this too.
    # We'll additionally require adjacency + surround to mowed grass.
    bunker_candidates = (
        (ndvi <= BUNKER_NDVI_MAX)
        & (brightness > 160)        # moderate — catches weathered sand too
        & (chm < 0.3)
        & (slope < 6)               # bunkers are nearly flat
        & (~water_mask)
    )

    # Green vs fairway vs rough within mowed_mask
    # Green: very flat, brightest NDVI (shortest-mown, healthiest turf)
    green_mask = mowed_mask & (slope <= GREEN_MAX_SLOPE) & (ndvi >= 0.38)
    fairway_mask = (
        mowed_mask
        & (slope <= FAIRWAY_MAX_SLOPE)
        & (ndvi >= 0.22)
        & (~green_mask)
    )
    rough_mask = (
        veg_mask
        & (~tree_mask)
        & (~green_mask)
        & (~fairway_mask)
    )

    # Bunker constraint: each connected bunker component must have enough mowed
    # grass within a short radius (3m shell) — a softer form of "surrounded".
    adj_radius_px = max(2, int(BUNKER_ADJACENCY_RADIUS_M / cell_m))
    shell_radius_px = max(3, int(3.0 / cell_m))
    mowed_or_green = fairway_mask | green_mask
    struct_adj = np.ones((3, 3), dtype=bool)
    near_mowed = ndimage.binary_dilation(
        mowed_or_green, structure=struct_adj, iterations=adj_radius_px,
    )

    step1 = bunker_candidates & near_mowed
    labels, n_lab = ndimage.label(step1, structure=struct_adj)
    bunker_mask = np.zeros_like(step1)
    kept_count = 0
    for lab in range(1, n_lab + 1):
        comp = labels == lab
        # Build a shell within `shell_radius_px` around the component
        shell = ndimage.binary_dilation(comp, structure=struct_adj, iterations=shell_radius_px) & ~comp
        n_shell = int(shell.sum())
        if n_shell == 0:
            continue
        n_shell_on_mowed = int((shell & mowed_or_green).sum())
        # Require: at least 20% of the 3m-radius shell is mowed grass
        if n_shell_on_mowed / n_shell >= BUNKER_SURROUND_FRAC:
            bunker_mask |= comp
            kept_count += 1
    print(
        f"[trace] bunker filter: {int(bunker_candidates.sum())} candidate px, "
        f"{n_lab} raw components, {kept_count} survived shell≥{BUNKER_SURROUND_FRAC:.0%}"
    )

    # --- Clean up: open (remove tiny noise) then close (fill small holes) ---
    struct = np.ones((3, 3), dtype=bool)
    def _clean(m: np.ndarray, iter_open: int = 1, iter_close: int = 2) -> np.ndarray:
        m = ndimage.binary_opening(m, structure=struct, iterations=iter_open)
        m = ndimage.binary_closing(m, structure=struct, iterations=iter_close)
        return m

    tree_mask    = _clean(tree_mask,    iter_open=1, iter_close=2)
    fairway_mask = _clean(fairway_mask, iter_open=2, iter_close=2)   # less aggressive merge
    green_mask   = _clean(green_mask,   iter_open=2, iter_close=3)
    bunker_mask  = _clean(bunker_mask,  iter_open=1, iter_close=2)
    water_mask   = _clean(water_mask,   iter_open=1, iter_close=2)
    rough_mask   = _clean(rough_mask,   iter_open=2, iter_close=2)

    # Fairway should not overlap green (green wins where both)
    fairway_mask = fairway_mask & ~green_mask

    # --- Polygonize + write GeoJSON ---
    feats: list = []
    feats += _polygonize(tree_mask,    naip_transform, "tree_canopy", MIN_FEATURE_AREA_M2["tree_canopy"], cell_area_m2)
    feats += _polygonize(fairway_mask, naip_transform, "fairway",     MIN_FEATURE_AREA_M2["fairway"],     cell_area_m2)
    feats += _polygonize(green_mask,   naip_transform, "green",       MIN_FEATURE_AREA_M2["green"],       cell_area_m2)
    feats += _polygonize(bunker_mask,  naip_transform, "bunker",      MIN_FEATURE_AREA_M2["bunker"],      cell_area_m2)
    feats += _polygonize(water_mask,   naip_transform, "water",       MIN_FEATURE_AREA_M2["water"],       cell_area_m2)
    feats += _polygonize(rough_mask,   naip_transform, "rough",       MIN_FEATURE_AREA_M2["rough"],       cell_area_m2)

    counts: dict = {}
    for f in feats:
        k = f["properties"]["kind"]
        counts[k] = counts.get(k, 0) + 1
    print(f"[trace] polygon counts: {counts}")

    out_path = ensure_dir(c / "derived") / "features.geojson"
    with out_path.open("w") as f:
        json.dump({"type": "FeatureCollection", "features": feats}, f)
    size_mb = out_path.stat().st_size / 1e6
    print(f"[trace] wrote {out_path} ({size_mb:.2f} MB, {len(feats)} polygons)")

    # Also write the classification raster for visual debugging
    cls = np.zeros(naip_shape, dtype="uint8")
    cls[rough_mask]   = CLASS_ROUGH
    cls[fairway_mask] = CLASS_FAIRWAY
    cls[tree_mask]    = CLASS_TREE
    cls[green_mask]   = CLASS_GREEN
    cls[bunker_mask]  = CLASS_BUNKER
    cls[water_mask]   = CLASS_WATER

    cls_meta = naip_meta.copy()
    cls_meta.update({
        "count": 1, "dtype": "uint8", "compress": "deflate", "tiled": True, "nodata": 0,
    })
    cls_path = c / "derived" / "classification.tif"
    with rasterio.open(cls_path, "w", **cls_meta) as dst:
        dst.write(cls, 1)
    print(f"[trace] wrote {cls_path}")

    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    args = ap.parse_args()
    classify(args.course)


if __name__ == "__main__":
    main()
