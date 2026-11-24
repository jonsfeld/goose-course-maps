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
    """Each non-hole_line feature goes to the nearest hole line.

    Keyed by the hole line's position, not its number: courses that share hole numbers with a
    neighbour (TPC Harding Park + Fleming 9) used to collapse into one bucket per number, so
    Harding holes picked up Fleming greens (fixed 2026-11-23).
    """
    assigned = [{"hole_line": h, "greens": [], "tees": [], "bunkers": [], "fairways": []} for h in holes]
    lines = [shape(h["geometry"]) for h in holes]
    for feat in features:
        kind = feat["properties"]["kind"]
        if kind in ("hole_line", "course_boundary"):
            continue
        poly = shape(feat["geometry"])
        dists = [poly.distance(line) for line in lines]  # in degrees
        if not dists:
            continue
        best = min(range(len(dists)), key=dists.__getitem__)
        feat["properties"]["hole_ref"] = holes[best]["properties"]["hole_ref"]
        bucket = {"green": "greens", "tee_box": "tees", "bunker": "bunkers", "fairway": "fairways"}.get(kind)
        if bucket:
            assigned[best][bucket].append(feat)
    return assigned


def _back_tee(line, all_tees, other_starts, lat_c):
    """The back-most tee box in line with this hole.

    OSM hole lines often start at a forward tee. Look among this hole's own tee boxes for ones up to
    70 m behind the line's start, within 20 degrees of the hole's direction, that don't start
    another hole, and use the farthest one. Returns a Point (lon/lat) or None.
    """
    mlat, mlon = _meters_per_deg(lat_c)
    sx, sy = line.coords[0][:2]
    nx, ny = line.coords[1][:2] if len(line.coords) > 1 else line.coords[-1][:2]
    dx, dy = (nx - sx) * mlon, (ny - sy) * mlat
    n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n
    best, best_back = None, 5.0  # must be at least 5 m behind the line start
    for poly in all_tees:
        c = poly.centroid
        vx, vy = (c.x - sx) * mlon, (c.y - sy) * mlat
        back = -(vx * ux + vy * uy)          # metres behind the start, along the hole direction
        side = abs(vx * uy - vy * ux)        # metres off the hole's axis
        if back <= best_back or back > 70 or side > max(10.0, back * math.tan(math.radians(20))):
            continue
        if any(c.distance(o) * mlat < 15 for o in other_starts):
            continue
        best, best_back = c, back
    return best

def _scorecard(c):
    p = c / "notes" / "scorecard.json"
    return json.loads(p.read_text()) if p.exists() else None


def _fit_tee_to_card(line, tee_polys, other_starts, lo, hi):
    """When the line's length is off the published scorecard, try each nearby tee box (within 90 m
    of the line start, on the hole's axis, not starting another hole) as the tee, and keep the one
    whose length lands inside the card's range, or closest to it. Returns a new LineString or None."""
    def length(ln):
        cs = [c[:2] for c in ln.coords]
        return sum(_haversine_m(cs[i][0], cs[i][1], cs[i + 1][0], cs[i + 1][1]) for i in range(len(cs) - 1)) * 1.09361
    def miss(L):
        return 0.0 if lo * 0.96 <= L <= hi * 1.04 else min(abs(L - lo), abs(L - hi))
    if miss(length(line)) == 0:
        return None
    mlat, mlon = _meters_per_deg(line.coords[0][1])
    sx, sy = line.coords[0][:2]
    nx, ny = line.coords[1][:2]
    ux, uy = (nx - sx) * mlon, (ny - sy) * mlat
    n = math.hypot(ux, uy) or 1.0
    ux, uy = ux / n, uy / n
    best, best_miss = None, miss(length(line))
    for poly in tee_polys:
        c = poly.centroid
        vx, vy = (c.x - sx) * mlon, (c.y - sy) * mlat
        along, side = vx * ux + vy * uy, abs(vx * uy - vy * ux)
        if math.hypot(vx, vy) > 90 or side > 25 or any(c.distance(o) * mlat < 15 for o in other_starts):
            continue
        rest = [p[:2] for p in line.coords[1:]] if along > 0 else [p[:2] for p in line.coords]
        cand = LineString([(c.x, c.y)] + rest)
        m = miss(length(cand))
        if m < best_miss:
            best, best_miss = cand, m
    return best


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
    all_tees = [shape(f["geometry"]) for f in features if f["properties"]["kind"] == "tee_box"]
    all_greens = [f for f in features if f["properties"]["kind"] == "green"]
    starts = [Point(shape(h["geometry"]).coords[0][:2]) for h in holes]
    # Scorecard applies to the main course: the first hole line for each number (same rule as
    # pick_holes: Harding before Fleming), matched by number.
    card = _scorecard(c)
    card_holes, seen = {}, set()
    if card:
        for i, h in enumerate(holes):
            n = int(h["properties"]["hole_ref"])
            if n not in seen and 1 <= n <= len(card["pars"]) and h["properties"].get("par") in (None, card["pars"][n - 1]):
                card_holes[i] = n - 1
                seen.add(n)

    output = {
        "course_slug": slug,
        "generated": "phase_e_v0",
        "holes": [],
    }

    for idx, h in enumerate(holes):
        ref = h["properties"]["hole_ref"]
        par = h["properties"]["par"]
        line = shape(h["geometry"])
        # Tee: the back-most tee box in line with the hole (OSM lines often start at a forward tee).
        own_tees = [shape(f["geometry"]) for f in assigned[idx]["tees"]]
        back = _back_tee(line, own_tees, [p for i, p in enumerate(starts) if i != idx], (line.coords[0][1] + line.coords[-1][1]) / 2)
        tee_source = "hole_line_start"
        if back is not None:
            line = LineString([(back.x, back.y)] + [c[:2] for c in line.coords])
            tee_source = "back_tee_box"
        # A published scorecard (notes/scorecard.json) referees the tee when the line's length is off it.
        if card and card_holes.get(idx) is not None:
            vals = [t[card_holes[idx]] for t in card["tees"].values()]
            fitted = _fit_tee_to_card(line, all_tees, [p for i, p in enumerate(starts) if i != idx], min(vals), max(vals))
            if fitted is not None:
                line, tee_source = fitted, "scorecard_fit"
        tee_pt = Point(line.coords[0])
        green_pt = Point(line.coords[-1])   # last vertex = green

        tee_elev = dem.sample(tee_pt.x, tee_pt.y)
        green_elev = dem.sample(green_pt.x, green_pt.y)
        net_delta = green_elev - tee_elev

        # Fairway centerline profile: sample DEM along line every ~5 yd
        lat_c = (tee_pt.y + green_pt.y) / 2
        mpdl_lat, mpdl_lon = _meters_per_deg(lat_c)
        # True ground length: sum each segment with its own lat/lon scale. (The old
        # line.length * average(m/deg lat, m/deg lon) overstated east–west holes: Harding 10 read 635 y
        # instead of ~550.)
        cs = [c[:2] for c in line.coords]
        length_m = sum(_haversine_m(cs[i][0], cs[i][1], cs[i + 1][0], cs[i + 1][1]) for i in range(len(cs) - 1))
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
        # The green is the one at the end of this hole's line (not the largest one nearby).
        greens = sorted(all_greens, key=lambda f: shape(f["geometry"]).distance(green_pt))
        green_entry = None
        green_stats = None
        if greens and shape(greens[0]["geometry"]).distance(green_pt) * _meters_per_deg(green_pt.y)[0] < 40:
            green_entry = greens[0]
            green_poly = shape(green_entry["geometry"])
            green_stats = _green_slope_stats(dem, green_poly)

        # Tee positions — list any tee_boxes assigned to this hole
        tees = assigned[idx]["tees"]
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
        for bk in assigned[idx]["bunkers"]:
            poly = shape(bk["geometry"])
            bunkers.append({
                "osm_id": bk["properties"]["osm_id"],
                "centroid": {"lat": round(poly.centroid.y, 7), "lng": round(poly.centroid.x, 7)},
                "area_m2": round(_polygon_area_m2(poly), 1),
            })

        # Fairway list (just osm_ids + areas; full polygons stay in OSM features)
        fairways = []
        for fw in assigned[idx]["fairways"]:
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
                "tee_source": tee_source,
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
