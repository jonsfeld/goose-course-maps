"""Build per-hole data structure for a course.

Joins OSM features to holes by proximity to hole_line, then layers LiDAR-
derived terrain intelligence onto each hole. Output is a single JSON file
consumed by the map.auto.md assembler.

For each hole_line (1..9):
  - Find nearest green, tee(s), fairway, and bunkers within a reasonable
    distance → tag them with hole_id.
  - Sample DEM at tee start + green center → tee/green elevation + net delta.
  - Sample DEM along hole_line centerline at 5yd → fairway_centerline_profile.
  - Clip DEM to green polygon → compute dominant + secondary slope, fall-line
    azimuth, and 0.5m elevation grid.
  - Raycast CHM along hole_line → measure overhead clearance + lateral clear
    width → tee_shot_corridor entry.

Output: courses/<slug>/derived/hole_data.json
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from shapely.geometry import LineString, Point, mapping, shape
from shapely.ops import transform as shp_transform

from _common import course_dir


GREEN_GRID_RESOLUTION_M = 0.5
CENTERLINE_SAMPLE_M = 4.5          # ~5 yd
CORRIDOR_SAMPLE_M = 5.0            # longitudinal step along hole_line
CORRIDOR_HALF_WIDTH_M = 30.0       # lateral scan ±30 m either side of line
CORRIDOR_LATERAL_STEP_M = 0.5
CANOPY_HEIGHT_THRESHOLD_M = 3.0    # below this is not considered overhead blockage


# --------------------------------------------------------------------------
# Geo helpers — treat WGS-84 as locally-planar for simplicity (course-scale)
# --------------------------------------------------------------------------

def _meters_per_deg(lat: float) -> tuple[float, float]:
    """Return (m_per_deg_lat, m_per_deg_lon) near this latitude."""
    return 111_000, 111_000 * math.cos(math.radians(lat))


def _project_to_meters(poly_geom, ref_lat: float):
    mpdl_lat, mpdl_lon = _meters_per_deg(ref_lat)
    def fwd(x, y):
        return (x * mpdl_lon, y * mpdl_lat)
    return shp_transform(fwd, poly_geom)


def _polygon_area_m2(geom) -> float:
    lat = geom.centroid.y
    return float(_project_to_meters(geom, lat).area)


def _haversine_m(a_lon, a_lat, b_lon, b_lat) -> float:
    mpdl_lat, mpdl_lon = _meters_per_deg((a_lat + b_lat) / 2)
    dx = (a_lon - b_lon) * mpdl_lon
    dy = (a_lat - b_lat) * mpdl_lat
    return math.hypot(dx, dy)


# --------------------------------------------------------------------------
# Raster sampling
# --------------------------------------------------------------------------

class Raster:
    def __init__(self, path: Path, fill_nodata_with: float = 0.0):
        self.path = path
        self.ds = rasterio.open(path)
        self.arr = self.ds.read(1).astype("float32")
        nodata = self.ds.nodata
        if nodata is not None:
            self.arr = np.where(self.arr == nodata, fill_nodata_with, self.arr)
        self.arr = np.where(np.isnan(self.arr), fill_nodata_with, self.arr)
        self.transform = self.ds.transform
        self.bounds = self.ds.bounds

    def sample(self, lon: float, lat: float) -> float:
        col = int((lon - self.transform.c) / self.transform.a)
        row = int((lat - self.transform.f) / self.transform.e)
        H, W = self.arr.shape
        if 0 <= row < H and 0 <= col < W:
            return float(self.arr[row, col])
        return float("nan")

    def close(self):
        self.ds.close()


# --------------------------------------------------------------------------
# Green slope analysis
# --------------------------------------------------------------------------

def _clip_dem_to_polygon(dem: Raster, poly) -> tuple[np.ndarray, rasterio.transform.Affine]:
    """Return (clipped_array, transform) for the DEM inside the polygon."""
    minx, miny, maxx, maxy = poly.bounds
    row_min = max(0, int((maxy - dem.transform.f) / dem.transform.e))
    row_max = min(dem.arr.shape[0], int((miny - dem.transform.f) / dem.transform.e) + 1)
    col_min = max(0, int((minx - dem.transform.c) / dem.transform.a))
    col_max = min(dem.arr.shape[1], int((maxx - dem.transform.c) / dem.transform.a) + 1)
    sub = dem.arr[row_min:row_max, col_min:col_max]
    sub_transform = rasterio.transform.from_origin(
        dem.transform.c + col_min * dem.transform.a,
        dem.transform.f + row_min * dem.transform.e,
        dem.transform.a,
        -dem.transform.e,
    )
    mask = geometry_mask([mapping(poly)], out_shape=sub.shape, transform=sub_transform, invert=True)
    sub = np.where(mask, sub, np.nan)
    return sub, sub_transform


def _green_slope_stats(dem: Raster, poly) -> dict:
    sub, sub_transform = _clip_dem_to_polygon(dem, poly)
    valid = ~np.isnan(sub)
    n_valid = int(valid.sum())
    if n_valid < 20:
        return {
            "sample_count": n_valid,
            "ok": False,
            "reason": "too few valid cells in green polygon",
        }

    lat_center = (poly.bounds[1] + poly.bounds[3]) / 2
    mpdl_lat, mpdl_lon = _meters_per_deg(lat_center)
    cellsize_m_x = abs(sub_transform.a) * mpdl_lon
    cellsize_m_y = abs(sub_transform.e) * mpdl_lat
    cell_m = (cellsize_m_x + cellsize_m_y) / 2

    # Compute gradient with nan-safe fill
    filled = np.where(valid, sub, np.nanmean(sub[valid]))
    dzdy, dzdx = np.gradient(filled, cell_m, cell_m)
    dzdx[~valid] = 0; dzdy[~valid] = 0

    # Mean gradient vector = dominant fall direction
    mean_dzdx = float(dzdx[valid].mean())
    mean_dzdy = float(dzdy[valid].mean())
    slope_magnitude_deg = float(math.degrees(math.atan(math.hypot(mean_dzdx, mean_dzdy))))

    # Azimuth: compass heading of the fall direction
    # gradient points uphill; fall line points downhill → negate
    fall_dx, fall_dy = -mean_dzdx, -mean_dzdy
    azimuth = (math.degrees(math.atan2(fall_dx, fall_dy)) + 360) % 360

    # Describe in cardinal-ish terms relative to compass
    def _dir(az):
        az = az % 360
        if az < 22.5 or az >= 337.5: return "N"
        if az < 67.5:  return "NE"
        if az < 112.5: return "E"
        if az < 157.5: return "SE"
        if az < 202.5: return "S"
        if az < 247.5: return "SW"
        if az < 292.5: return "W"
        return "NW"

    # Build compact elevation grid at GREEN_GRID_RESOLUTION_M
    # Keep the existing sub at DEM native resolution (~1m), document resolution.
    # For a truly 0.5m grid we'd bilinear-interp; for v0 we use native DEM res.
    grid_rows, grid_cols = sub.shape
    grid_list = [[None if np.isnan(v) else round(float(v), 3) for v in row] for row in sub]

    return {
        "ok": True,
        "sample_count": n_valid,
        "mean_elevation_m": round(float(np.nanmean(sub)), 2),
        "min_elevation_m": round(float(np.nanmin(sub)), 2),
        "max_elevation_m": round(float(np.nanmax(sub)), 2),
        "dominant_slope_deg": round(slope_magnitude_deg, 2),
        "fall_line_azimuth_deg": round(azimuth, 1),
        "fall_direction": _dir(azimuth),
        "cellsize_m": round(cell_m, 3),
        "grid": {
            "origin_latlon": [
                round(float(sub_transform.f + grid_rows * sub_transform.e), 7),
                round(float(sub_transform.c), 7),
            ],
            "resolution_m": round(cell_m, 3),
            "rows": grid_rows,
            "cols": grid_cols,
            "null_value": None,
            "values": grid_list,
        },
    }


# --------------------------------------------------------------------------
# Tee shot corridor: sample CHM along hole_line
# --------------------------------------------------------------------------

def _tee_shot_corridor(chm: Raster, hole_line: LineString, lat_center: float) -> dict:
    mpdl_lat, mpdl_lon = _meters_per_deg(lat_center)
    length_deg = hole_line.length
    length_m = length_deg * (mpdl_lat + mpdl_lon) / 2

    n_samples = max(10, int(length_m / CORRIDOR_SAMPLE_M))
    overhead_max = 0.0
    overhead_p90 = []
    clear_widths = []

    for i in range(1, n_samples):  # skip the tee itself
        frac = i / n_samples
        p = hole_line.interpolate(frac, normalized=True)
        # Along-direction tangent
        p_before = hole_line.interpolate(max(frac - 0.01, 0), normalized=True)
        p_after = hole_line.interpolate(min(frac + 0.01, 1), normalized=True)
        dx = (p_after.x - p_before.x) * mpdl_lon
        dy = (p_after.y - p_before.y) * mpdl_lat
        norm = math.hypot(dx, dy) or 1e-9
        # Perpendicular (unit) vector
        perp_lon = (-dy / norm) / mpdl_lon
        perp_lat = (dx / norm) / mpdl_lat

        overhead = chm.sample(p.x, p.y)
        if overhead and overhead > overhead_max:
            overhead_max = overhead
        overhead_p90.append(overhead if not math.isnan(overhead) else 0.0)

        # Lateral scan both sides until we hit canopy
        half_clear = 0.0
        for side in (-1, 1):
            step = 0
            while step * CORRIDOR_LATERAL_STEP_M < CORRIDOR_HALF_WIDTH_M:
                step += 1
                offset = side * step * CORRIDOR_LATERAL_STEP_M
                q = (p.x + offset * perp_lon, p.y + offset * perp_lat)
                h = chm.sample(q[0], q[1])
                if math.isnan(h) or h >= CANOPY_HEIGHT_THRESHOLD_M:
                    break
            half_clear += step * CORRIDOR_LATERAL_STEP_M
        clear_widths.append(half_clear)

    clear_widths = np.array(clear_widths)
    return {
        "length_m": round(length_m, 1),
        "length_yd": round(length_m * 1.09361, 1),
        "narrowest_clear_yd": round(float(clear_widths.min()) * 1.09361, 1) if clear_widths.size else None,
        "median_clear_yd": round(float(np.median(clear_widths)) * 1.09361, 1) if clear_widths.size else None,
        "max_overhead_m": round(overhead_max, 1),
        "p90_overhead_m": round(float(np.percentile(overhead_p90, 90)), 1) if overhead_p90 else None,
        "pinch_at_yd": round(float(np.argmin(clear_widths)) / max(1, len(clear_widths)) * length_m * 1.09361, 1) if clear_widths.size else None,
    }


# --------------------------------------------------------------------------
# Feature → hole assignment (spatial join)
# --------------------------------------------------------------------------

def _assign_features(features, holes):
    """Each non-hole_line feature gets hole_id = ref of nearest hole_line."""
    assigned = {h["properties"]["hole_ref"]: {"hole_line": h, "greens": [], "tees": [],
                                              "bunkers": [], "fairways": []} for h in holes}
    hole_by_ref = {h["properties"]["hole_ref"]: h for h in holes}
    for feat in features:
        kind = feat["properties"]["kind"]
        if kind in ("hole_line", "course_boundary"):
            continue
        poly = shape(feat["geometry"])
        # Distance to every hole_line — keep the nearest
        best_ref = None; best_dist = float("inf")
        for href, h in hole_by_ref.items():
            line = shape(h["geometry"])
            d = poly.distance(line)  # in degrees
            if d < best_dist:
                best_dist = d; best_ref = href
        if best_ref is None:
            continue
        feat["properties"]["hole_ref"] = best_ref
        bucket = {"green": "greens", "tee_box": "tees", "bunker": "bunkers", "fairway": "fairways"}.get(kind)
        if bucket:
            assigned[best_ref][bucket].append(feat)
    return assigned


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def build(slug: str) -> Path:
    c = course_dir(slug)
    osm_path = c / "derived" / "features_osm.geojson"
    dem_path = c / "derived" / "dem_clipped.tif"
    chm_path = c / "derived" / "canopy_height_model.tif"

    for p in (osm_path, dem_path, chm_path):
        if not p.exists():
            raise FileNotFoundError(p)

    with osm_path.open() as f:
        features = json.load(f)["features"]
    holes = [f for f in features if f["properties"]["kind"] == "hole_line"]
    holes.sort(key=lambda h: int(h["properties"]["hole_ref"]))
    print(f"[hole-data] {len(holes)} hole_lines, {len(features)} total features")

    dem = Raster(dem_path)
    chm = Raster(chm_path, fill_nodata_with=0.0)

    assigned = _assign_features(features, holes)

    output = {
        "course_slug": slug,
        "generated": "phase_e_v0",
        "holes": [],
    }

    for h in holes:
        ref = h["properties"]["hole_ref"]
        par = h["properties"]["par"]
        line = shape(h["geometry"])
        tee_pt = Point(line.coords[0])      # first vertex = tee
        green_pt = Point(line.coords[-1])   # last vertex = green

        tee_elev = dem.sample(tee_pt.x, tee_pt.y)
        green_elev = dem.sample(green_pt.x, green_pt.y)
        net_delta = green_elev - tee_elev

        # Fairway centerline profile: sample DEM along line every ~5 yd
        lat_c = (tee_pt.y + green_pt.y) / 2
        mpdl_lat, mpdl_lon = _meters_per_deg(lat_c)
        length_m = line.length * (mpdl_lat + mpdl_lon) / 2
        n_samples = max(5, int(length_m / CENTERLINE_SAMPLE_M))
        profile = []
        for i in range(n_samples + 1):
            frac = i / n_samples
            p = line.interpolate(frac, normalized=True)
            elev = dem.sample(p.x, p.y)
            yd_from_tee = round(frac * length_m * 1.09361, 1)
            profile.append({"yd_from_tee": yd_from_tee, "elev_m": round(elev, 2) if not math.isnan(elev) else None})

        # Corridor analysis
        corridor = _tee_shot_corridor(chm, line, lat_c)

        # Green slope analysis (use largest assigned green)
        greens = sorted(assigned[ref]["greens"], key=lambda f: -_polygon_area_m2(shape(f["geometry"])))
        green_entry = None
        green_stats = None
        if greens:
            green_entry = greens[0]
            green_poly = shape(green_entry["geometry"])
            green_stats = _green_slope_stats(dem, green_poly)

        # Tee positions — list any tee_boxes assigned to this hole
        tees = assigned[ref]["tees"]
        tee_positions = []
        for tp in tees:
            poly = shape(tp["geometry"])
            cx, cy = poly.centroid.x, poly.centroid.y
            tee_positions.append({
                "osm_id": tp["properties"]["osm_id"],
                "centroid": {"lat": round(cy, 7), "lng": round(cx, 7)},
                "area_m2": round(_polygon_area_m2(poly), 1),
            })

        # Bunker list
        bunkers = []
        for bk in assigned[ref]["bunkers"]:
            poly = shape(bk["geometry"])
            bunkers.append({
                "osm_id": bk["properties"]["osm_id"],
                "centroid": {"lat": round(poly.centroid.y, 7), "lng": round(poly.centroid.x, 7)},
                "area_m2": round(_polygon_area_m2(poly), 1),
            })

        # Fairway list (just osm_ids + areas; full polygons stay in OSM features)
        fairways = []
        for fw in assigned[ref]["fairways"]:
            poly = shape(fw["geometry"])
            fairways.append({
                "osm_id": fw["properties"]["osm_id"],
                "area_m2": round(_polygon_area_m2(poly), 1),
            })

        hole_record = {
            "hole": int(ref),
            "par": par,
            "hole_line": {
                "tee": {"lat": round(tee_pt.y, 7), "lng": round(tee_pt.x, 7)},
                "green_center": {"lat": round(green_pt.y, 7), "lng": round(green_pt.x, 7)},
                "length_m": round(length_m, 1),
                "length_yd": round(length_m * 1.09361, 1),
            },
            "terrain": {
                "tee_elevation_m": round(tee_elev, 2) if not math.isnan(tee_elev) else None,
                "green_elevation_m": round(green_elev, 2) if not math.isnan(green_elev) else None,
                "net_delta_m": round(net_delta, 2) if not (math.isnan(tee_elev) or math.isnan(green_elev)) else None,
                "fairway_centerline_profile": profile,
            },
            "green": {
                "osm_id": green_entry["properties"]["osm_id"] if green_entry else None,
                "area_m2": round(_polygon_area_m2(shape(green_entry["geometry"])), 1) if green_entry else None,
                "slope_analysis": green_stats,
            },
            "tees": tee_positions,
            "bunkers": bunkers,
            "fairways": fairways,
            "tee_shot_corridor": corridor,
        }
        output["holes"].append(hole_record)
        print(
            f"[hole-data] H{ref} par {par}: {length_m:.0f}m ({length_m*1.09361:.0f}yd), "
            f"Δelev {net_delta:+.1f}m, "
            f"green slope {green_stats['dominant_slope_deg'] if green_stats else '—'}° {green_stats['fall_direction'] if green_stats else ''}, "
            f"tees {len(tee_positions)} bunkers {len(bunkers)}"
        )

    out_path = c / "derived" / "hole_data.json"
    with out_path.open("w") as f:
        json.dump(output, f, indent=2, allow_nan=False)
    print(f"[hole-data] wrote {out_path}")

    dem.close(); chm.close()
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    args = ap.parse_args()
    build(args.course)


if __name__ == "__main__":
    main()
