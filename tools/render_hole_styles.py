"""Render one hole in two map styles plus a directional green read (prototype).

A  "Yardage Book": paper, ink, flat fills, lidar trees, soft hillshade + contours.
B  "Aerial":       NAIP photo, graded, with crisp vector outlines on top.
Green:             slope-shaded green with downhill arrows from lidar ground points
                   (falls back to the 1 m DEM when the lidar file is missing).

Every layer is drawn in a hole frame: tee at the bottom, green at the top.

    python3 tools/render_hole_styles.py --course tpc_harding_park --hole 14 --out /tmp/h14.html
"""
from __future__ import annotations

import argparse
import base64
import gzip
import io
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer
from scipy import ndimage
from shapely.geometry import LineString, Point, Polygon, box, mapping, shape
from shapely.ops import transform as shp_transform

from _common import course_dir

PAPER = (243, 241, 234)
INK = "#111311"
INK_MUTED = "#545850"
RULE = "#CFCABD"
FAIRWAY = "#D9E7D1"
GREEN = "#BFD9B8"
SAND = "#EFE6CF"
WATER = "#D7E4EC"
TEE = "#D9E7D1"
FLAG = "#C8402A"
PIN = "#D4A53A"
FAIRWAY_DARK = "#1D5C3B"
YD = 0.9144


# ---------------------------------------------------------------- geometry
class Frame:
    """Hole frame: s = metres along tee->green, d = metres right of that line."""

    def __init__(self, tee, green, s0, s1, half_w, px_per_m):
        self.t = np.array(tee, float)
        u = np.array(green, float) - self.t
        self.L = float(np.hypot(*u))
        self.u = u / self.L
        self.n = np.array([self.u[1], -self.u[0]])  # right-hand normal
        self.s0, self.s1, self.hw, self.k = s0, s1, half_w, px_per_m
        self.W = int(round(2 * half_w * px_per_m))
        self.H = int(round((s1 - s0) * px_per_m))

    def to_px(self, x, y):
        p = np.stack([np.asarray(x, float) - self.t[0], np.asarray(y, float) - self.t[1]], -1)
        s = p @ self.u
        d = p @ self.n
        return (d + self.hw) * self.k, (self.s1 - s) * self.k

    def px_to_utm(self, X, Y):
        d = X / self.k - self.hw
        s = self.s1 - Y / self.k
        return (self.t[0] + s * self.u[0] + d * self.n[0], self.t[1] + s * self.u[1] + d * self.n[1])

    def rect_utm(self):
        c = [self.px_to_utm(0, 0), self.px_to_utm(self.W, 0), self.px_to_utm(self.W, self.H), self.px_to_utm(0, self.H)]
        return Polygon(c)

    def grid_utm(self, step_px=1.0):
        xs = np.arange(0, self.W, step_px) + 0.5 * step_px
        ys = np.arange(0, self.H, step_px) + 0.5 * step_px
        X, Y = np.meshgrid(xs, ys)
        return self.px_to_utm(X, Y)


def path_d(geom, fr: Frame) -> str:
    out = []

    def ring(coords, close=True):
        a = np.asarray(coords)[:, :2]
        X, Y = fr.to_px(a[:, 0], a[:, 1])
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(X, Y))
        out.append(f"M{pts}{'Z' if close else ''}")

    def walk(g):
        if g.is_empty:
            return
        t = g.geom_type
        if t == "Polygon":
            ring(g.exterior.coords)
            for i in g.interiors:
                ring(i.coords)
        elif t == "LineString":
            ring(g.coords, close=False)
        elif t in ("MultiPolygon", "MultiLineString", "GeometryCollection"):
            for gg in g.geoms:
                walk(gg)

    walk(geom)
    return " ".join(out).replace("M", "M ", 1) if out else ""


def png_b64(rgba: np.ndarray) -> str:
    im = Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA" if rgba.shape[-1] == 4 else "RGB")
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def jpg_b64(rgb: np.ndarray, q=86) -> str:
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=q, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------------- rasters
def sample_dem(dem_path, fr: Frame, step_px, to_ll):
    ux, uy = fr.grid_utm(step_px)
    lon, lat = to_ll.transform(ux, uy)
    with rasterio.open(dem_path) as r:
        a = r.read(1).astype(float)
        nod = r.nodata
        inv = ~r.transform
        col, row = inv * (lon, lat)
    if nod is not None:
        a[a == nod] = np.nan
    a[a < -100] = np.nan
    fill = np.where(np.isnan(a), np.nanmean(a), a)
    z = ndimage.map_coordinates(fill, [row - 0.5, col - 0.5], order=1, mode="nearest")
    return z


def hillshade(z, cell_m, az_deg=315, alt_deg=40, zf=2.5):
    gy, gx = np.gradient(z * zf, cell_m)
    slope = np.arctan(np.hypot(gx, gy))
    # image rows go down, so the "north" of the frame is -y
    aspect = np.arctan2(-gx, gy)
    az, alt = math.radians(360 - az_deg + 90), math.radians(alt_deg)
    hs = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    return np.clip(hs, 0, 1)


def contour_paths(z, levels, step_px):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure()
    cs = plt.contour(np.arange(z.shape[1]) * step_px, np.arange(z.shape[0]) * step_px, z, levels=levels)
    out = []
    for lev, segs in zip(cs.levels, cs.allsegs):
        for s in segs:
            if len(s) < 6:
                continue
            out.append((lev, "M " + " ".join(f"{x:.1f},{y:.1f}" for x, y in s)))
    plt.close(fig)
    return out


# ---------------------------------------------------------------- green surface
def green_surface(pts_xyz, gpoly, cell=0.3, sigma_m=0.8):
    from shapely import contains_xy
    minx, miny, maxx, maxy = gpoly.buffer(6).bounds
    nx, ny = int((maxx - minx) / cell) + 1, int((maxy - miny) / cell) + 1
    x, y, z = pts_xyz.T
    keep = contains_xy(gpoly.buffer(-0.8), x, y)  # stay off the collar; OSM edges are approximate
    x, y, z = x[keep], y[keep], z[keep]
    ix, iy = ((x - minx) / cell).astype(int), ((y - miny) / cell).astype(int)
    s = np.zeros((ny, nx)); c = np.zeros((ny, nx))
    np.add.at(s, (iy, ix), z); np.add.at(c, (iy, ix), 1)
    with np.errstate(invalid="ignore"):
        g = s / c
    m = c > 0
    # drop cells far from their neighbourhood (flagsticks, people, misclassified points)
    med = ndimage.generic_filter(np.where(m, g, np.nan), np.nanmedian, size=5, mode="nearest")
    bad = m & (np.abs(g - med) > 0.06)
    m &= ~bad
    sig = sigma_m / cell
    num = ndimage.gaussian_filter(np.where(m, g, 0), sig)
    den = ndimage.gaussian_filter(m.astype(float), sig)
    zs = num / np.maximum(den, 1e-6)
    # extend the surface past the edge so edge gradients are not pulled by the apron
    far = den < 0.05
    if far.any():
        idx = ndimage.distance_transform_edt(far, return_distances=False, return_indices=True)
        zs = zs[tuple(idx)]
    area = gpoly.buffer(-0.8).area
    return {"z": zs, "x0": minx, "y0": miny, "cell": cell, "pts": int(keep.sum()), "density": float(keep.sum() / area),
            "dropped": int(bad.sum())}


def surface_from_dem(dem_path, gpoly, to_ll, cell=0.4):
    minx, miny, maxx, maxy = gpoly.buffer(6).bounds
    xs = np.arange(minx, maxx, cell); ys = np.arange(miny, maxy, cell)
    X, Y = np.meshgrid(xs, ys)
    lon, lat = to_ll.transform(X, Y)
    with rasterio.open(dem_path) as r:
        a = r.read(1).astype(float); inv = ~r.transform
        col, row = inv * (lon, lat)
    z = ndimage.map_coordinates(a, [row - 0.5, col - 0.5], order=3, mode="nearest")
    z = ndimage.gaussian_filter(z, 1.2 / cell)
    return {"z": z, "x0": minx, "y0": miny, "cell": cell, "pts": 0, "density": 0.0}


def surf_eval(S, x, y):
    col = (np.asarray(x) - S["x0"]) / S["cell"]
    row = (np.asarray(y) - S["y0"]) / S["cell"]
    return ndimage.map_coordinates(S["z"], [row, col], order=1, mode="nearest")


def surf_grad(S, x, y):
    """Gradient (dz/dx, dz/dy) in m per m at UTM points."""
    gy, gx = np.gradient(S["z"], S["cell"])
    col = (np.asarray(x) - S["x0"]) / S["cell"]
    row = (np.asarray(y) - S["y0"]) / S["cell"]
    return (ndimage.map_coordinates(gx, [row, col], order=1, mode="nearest"),
            ndimage.map_coordinates(gy, [row, col], order=1, mode="nearest"))


# ---------------------------------------------------------------- main render
def load(slug, hole):
    cdir = course_dir(slug)
    hd = json.loads((cdir / "derived/hole_data.json").read_text())
    fc = json.loads((cdir / "derived/features_osm.geojson").read_text())
    hs = [h for h in hd["holes"] if h["hole"] == hole]
    h = max(hs, key=lambda h: h["hole_line"]["length_m"])
    return cdir, h, fc


def render(slug, hole, out_path):
    cdir, h, fc = load(slug, hole)
    tee_ll, g_ll = h["hole_line"]["tee"], h["hole_line"]["green_center"]
    epsg = (32600 if tee_ll["lat"] >= 0 else 32700) + int((tee_ll["lng"] + 180) // 6) + 1
    to_utm = Transformer.from_crs(4326, epsg, always_xy=True)
    to_ll = Transformer.from_crs(epsg, 4326, always_xy=True)
    U = lambda g: shp_transform(lambda x, y, z=None: to_utm.transform(x, y), g)
    tee = to_utm.transform(tee_ll["lng"], tee_ll["lat"])
    gc = to_utm.transform(g_ll["lng"], g_ll["lat"])

    feats = []
    for f in fc["features"]:
        k = f["properties"].get("kind")
        if k in ("fairway", "green", "bunker", "tee_box", "water", "woods", "cart_path", "hole_line"):
            try:
                g = U(shape(f["geometry"]))
                if not g.is_valid:
                    g = g.buffer(0)
                feats.append((k, f["properties"], g))
            except Exception:
                pass
    gpoly = min((g for k, _, g in feats if k == "green"), key=lambda g: g.distance(Point(gc)))
    pin = gpoly.centroid
    hole_line = None
    for k, p, g in feats:
        if k == "hole_line" and str(p.get("hole_ref")) == str(hole) and g.distance(Point(tee)) < 60 and g.distance(pin) < 40:
            hole_line = g
    if hole_line is None:
        hole_line = LineString([tee, (pin.x, pin.y)])

    L = math.dist(tee, (pin.x, pin.y))
    hw = 105.0
    fr = Frame(tee, (pin.x, pin.y), -28, L + 40, hw, px_per_m=2.6)
    rect = fr.rect_utm()
    vis = [(k, p, g.intersection(rect)) for k, p, g in feats if g.intersects(rect)]
    trees = []
    tj = json.loads((cdir / "derived/individual_trees.geojson").read_text())
    for f in tj["features"]:
        x, y = to_utm.transform(*f["geometry"]["coordinates"][:2])
        if rect.contains(Point(x, y)):
            trees.append((x, y, f["properties"].get("height_m", 6), f["properties"].get("canopy_radius_m", 1.5)))
    canopy = []
    cj = json.loads((cdir / "derived/canopy_polygons.geojson").read_text())
    for f in cj["features"]:
        g = U(shape(f["geometry"])).buffer(0)
        if g.intersects(rect):
            canopy.append(g.intersection(rect))

    # terrain rasters in frame
    step = 1.0  # px
    z = sample_dem(cdir / "derived/dem_clipped.tif", fr, step, to_ll)
    z = ndimage.gaussian_filter(z, 1.0)
    hs = hillshade(z, 1 / fr.k)
    shade = (1 - hs)
    shade = ndimage.gaussian_filter(shade, 1.2)
    shade = (shade - np.percentile(shade, 5)) / max(1e-6, np.percentile(shade, 99.5) - np.percentile(shade, 5))
    alpha = np.clip(shade, 0, 1) ** 1.3 * 70
    rgba = np.zeros(z.shape + (4,)); rgba[..., :3] = (60, 58, 46); rgba[..., 3] = alpha
    hill_uri = png_b64(rgba)
    zmin, zmax = np.nanmin(z), np.nanmax(z)
    contours = contour_paths(z, np.arange(math.floor(zmin), math.ceil(zmax) + 0.01, 0.5), step)

    # aerial (optional): a plain graded photo, and a blended one toned into the Yardage Book palette
    naip_uri = blend_uri = None
    nj = cdir / f"derived/holes/hole_{hole}_naip.json"
    npng = cdir / f"derived/holes/hole_{hole}_naip.png"
    if nj.exists() and npng.exists():
        meta = json.loads(nj.read_text())
        bx0, by0, bx1, by1 = meta["bounds"]
        img = np.asarray(Image.open(npng).convert("RGB")).astype(float)
        sc = 2  # render the photo at 2x the vector scale for crispness
        xs = (np.arange(fr.W * sc) + 0.5) / sc; ys = (np.arange(fr.H * sc) + 0.5) / sc
        X, Y = np.meshgrid(xs, ys)
        ux, uy = fr.px_to_utm(X, Y)
        col = (ux - bx0) / (bx1 - bx0) * img.shape[1] - 0.5
        row = (by1 - uy) / (by1 - by0) * img.shape[0] - 0.5
        raw = np.stack([ndimage.map_coordinates(img[..., c], [row, col], order=1, mode="constant", cval=np.nan) for c in range(3)], -1)
        miss = np.isnan(raw[..., 0])
        raw = np.nan_to_num(raw, nan=0)
        lum = raw @ np.array([0.299, 0.587, 0.114])
        # B: plain aerial, lightly graded
        rgb = lum[..., None] + (raw - lum[..., None]) * 0.82
        rgb = 255 * (rgb / 255) ** 0.92
        rgb = rgb * 0.9 + np.array(PAPER) * 0.1
        rgb[miss] = PAPER
        naip_uri = jpg_b64(rgb)
        # Blend: duotone from deep fairway-ink to paper, keeping a little of the photo's colour
        t = np.clip((lum / 255 - 0.06) / 0.62, 0, 1) ** 0.8
        dark = np.array([36, 52, 40]); light = np.array(PAPER)
        base = dark * (1 - t[..., None]) + light * t[..., None]
        out = base + (raw - lum[..., None]) * 0.5
        out = out * 0.9 + light * 0.10
        out[miss] = PAPER
        blend_uri = jpg_b64(out, q=84)

    # green surface
    gfile = cdir / f"derived/holes/hole_{hole}_green_ground.csv.gz"
    src = "dem"
    if gfile.exists():
        rows = gzip.open(gfile, "rt").read().split("\n")
        pts = np.array([[float(v) for v in r.split(",")] for r in rows[1:] if r.count(",") == 2])
        S = green_surface(pts, gpoly)
        src = "lidar"
    else:
        S = surface_from_dem(cdir / "derived/dem_clipped.tif", gpoly, to_ll)

    green_svg, gstats = render_green(S, gpoly, fr, feats, src)

    # yardage arcs (distance to pin) across the corridor
    arcs = []
    for yd in (100, 150, 200, 250):
        r = yd * YD
        if r > L - 15:
            continue
        circ = Point(pin.x, pin.y).buffer(r, 128).exterior
        seg = circ.intersection(box(*Point(tee).buffer(1).bounds).union(rect)).intersection(rect)
        # keep only the part near the hole line (+-45 m)
        corridor = hole_line.buffer(45)
        seg = seg.intersection(corridor)
        if not seg.is_empty:
            arcs.append((yd, seg))

    # ------------------------------------------------------------ SVG layers
    def layer(kind, **style):
        attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in style.items())
        return "".join(f'<path d="{path_d(g, fr)}" {attrs}/>' for k, _, g in vis if k == kind and not g.is_empty)

    W, H = fr.W, fr.H
    tree_svg = []
    for x, y, ht, cr in trees:
        X, Y = fr.to_px(x, y)
        rad = float(np.clip(cr + 0.8, 1.3, 3.6)) * fr.k
        tree_svg.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{rad:.1f}"/>')
    tree_svg = "".join(tree_svg)
    can_svg = "".join(f'<path d="{path_d(g, fr)}"/>' for g in canopy if not g.is_empty)
    cont_svg = "".join(f'<path d="{d}" class="{"major" if abs(lev - round(lev)) < 1e-6 else "minor"}"/>' for lev, d in contours)

    hl = path_d(hole_line, fr)
    tX, tY = fr.to_px(*tee)
    pX, pY = fr.to_px(pin.x, pin.y)
    arc_svg = []
    for yd, seg in arcs:
        arc_svg.append(f'<path d="{path_d(seg, fr)}" class="arc"/>')
        parts = [seg] if seg.geom_type == "LineString" else list(seg.geoms)
        ends = [fr.to_px(*q) for g_ in parts for q in (g_.coords[0], g_.coords[-1])]
        cx, cy = max(ends, key=lambda e: e[0])
        lx = min(cx + 4, fr.W - 30)
        arc_svg.append(f'<text x="{lx:.0f}" y="{cy + 4 if lx == cx + 4 else cy - 6:.0f}" class="arcl">{yd}</text>')
    arc_svg = "".join(arc_svg)

    common_top = f"""
      <g class="arcs">{arc_svg}</g>
      <path d="{hl}" class="holeline"/>
      <g class="tee-mark"><circle cx="{tX:.1f}" cy="{tY:.1f}" r="6"/></g>
      <g class="flag" transform="translate({pX:.1f},{pY:.1f})"><line x1="0" y1="0" x2="0" y2="-26" stroke="{PIN}" stroke-width="2"/><path d="M0 -26 L16 -21 L9 -18 L16 -14 L0 -16 Z" fill="{FLAG}"/><circle r="2.6" fill="{INK}"/></g>"""

    blend_img = f'<image class="img-blend" href="{blend_uri}" width="{W}" height="{H}" preserveAspectRatio="none"/>' if blend_uri else ""
    aerial_img = f'<image class="img-aerial" href="{naip_uri}" width="{W}" height="{H}" preserveAspectRatio="none"/>' if naip_uri else ""
    mode = "mode-blend" if blend_uri else "mode-book"
    # One drawing, three looks: CSS on the mode class decides which layers show and how features are painted.
    svg = f"""<svg viewBox="0 0 {W} {H}" class="hole {mode}" role="img" aria-label="Hole {hole} map">
      <rect class="paper" width="{W}" height="{H}" fill="rgb{PAPER}"/>
      {blend_img}{aerial_img}
      <rect class="aerial-dim" width="{W}" height="{H}" fill="#0b1a10" opacity="0.08"/>
      <image class="hill" href="{hill_uri}" width="{W}" height="{H}" preserveAspectRatio="none"/>
      <g class="contours">{cont_svg}</g>
      <g class="f f-water">{layer("water")}</g>
      <g class="canopy">{can_svg}</g>
      <g class="f f-fairway">{layer("fairway")}</g>
      <g class="f f-tee">{layer("tee_box")}</g>
      <g class="f f-green">{layer("green")}</g>
      <g class="f f-bunker">{layer("bunker")}</g>
      <g class="f f-cart">{layer("cart_path")}</g>
      <g class="trees">{tree_svg}</g>
      {common_top}
    </svg>"""

    meta = {"hole": hole, "par": h["par"], "yd": round(L / YD), "src": src, **gstats}
    meta["has_photo"] = bool(blend_uri)
    meta["ntrees"] = len(trees)
    return svg, green_svg, meta


def render_green(S, gpoly, fr: Frame, feats, src):
    """Green panel in the same orientation as the hole (approach from below)."""
    c = gpoly.centroid
    rad = max(math.dist((c.x, c.y), p) for p in gpoly.exterior.coords) + 5
    gk = 300 / (2 * rad)  # px per m, panel 300 px wide
    gf = Frame((c.x - fr.u[0] * 100, c.y - fr.u[1] * 100), (c.x, c.y), 100 - rad, 100 + rad, rad, gk)
    W, H = gf.W, gf.H

    # slope raster over the panel
    ux, uy = gf.grid_utm(1.0)
    gx, gy = surf_grad(S, ux, uy)
    pct = np.hypot(gx, gy) * 100
    inside = np.zeros_like(pct, bool)
    from shapely import contains_xy
    inside = contains_xy(gpoly, ux, uy)
    # colour by slope class (percent)
    stops = [(0.0, (226, 236, 220)), (1.0, (198, 222, 188)), (2.0, (233, 221, 168)), (3.0, (232, 194, 146)), (4.0, (218, 148, 108)), (6.0, (204, 112, 80))]
    rgb = np.zeros(pct.shape + (3,))
    for i in range(len(stops) - 1):
        a0, c0 = stops[i]; a1, c1 = stops[i + 1]
        t = np.clip((pct - a0) / (a1 - a0), 0, 1)[..., None]
        sel = (pct >= a0) if i < len(stops) - 2 else (pct >= a0)
        rgb = np.where(sel[..., None], np.array(c0) * (1 - t) + np.array(c1) * t, rgb)
    rgba = np.zeros(pct.shape + (4,)); rgba[..., :3] = rgb; rgba[..., 3] = np.where(inside, 255, 0)
    heat = png_b64(rgba)

    # arrows on a regular grid inside the green
    arrows = []
    sp = 2.3  # m
    xs = np.arange(-rad, rad, sp);
    for dx in xs:
        for ds in xs:
            X = W / 2 + dx * gk; Y = H / 2 - ds * gk
            px, py = gf.px_to_utm(X, Y)
            if not gpoly.buffer(-0.9).contains(Point(px, py)):
                continue
            ddx, ddy = surf_grad(S, [px], [py])
            g = float(np.hypot(ddx[0], ddy[0]))
            if g * 100 < 0.4:
                continue
            # downhill direction in UTM -> panel px
            dirx, diry = -ddx[0] / g, -ddy[0] / g
            ax, ay = gf.to_px(px + dirx, py + diry)
            vx, vy = ax - X, ay - Y
            n = math.hypot(vx, vy)
            ln = (6 + min(g * 100, 4) * 3.0)
            vx, vy = vx / n * ln, vy / n * ln
            x0, y0 = X - vx / 2, Y - vy / 2
            x1, y1 = X + vx / 2, Y + vy / 2
            ang = math.degrees(math.atan2(vy, vx))
            arrows.append(f'<g transform="translate({x1:.1f},{y1:.1f}) rotate({ang:.0f})"><path d="M-{ln:.1f} 0 H-2" /><path d="M-4.5 -2.6 L0 0 L-4.5 2.6" /></g>')

    # contours of the surface, 3 cm
    zz = surf_eval(S, ux, uy)
    zin = np.where(inside, zz, np.nan)
    lo, hi = np.nanmin(zin), np.nanmax(zin)
    cont = contour_paths(np.where(inside | ndimage.binary_dilation(inside, iterations=4), zz, np.nan), np.arange(math.floor(lo * 100 / 3) * 0.03, hi + 0.03, 0.03), 1.0)
    cont_svg = "".join(f'<path d="{d}"/>' for _, d in cont)

    # overall fall line (plane fit over the green)
    xs_in, ys_in, zs_in = ux[inside], uy[inside], zz[inside]
    A = np.c_[xs_in - xs_in.mean(), ys_in - ys_in.mean(), np.ones_like(xs_in)]
    (a, b, _), *_ = np.linalg.lstsq(A, zs_in, rcond=None)
    overall = math.hypot(a, b) * 100
    fx, fy = gf.to_px(c.x - a, c.y - b)
    cx, cy = gf.to_px(c.x, c.y)
    vx, vy = fx - cx, fy - cy
    # describe direction relative to the approach (panel up = away from the player)
    ang_up = math.degrees(math.atan2(vx, -vy)) % 360
    rel = ["away (back)", "back-right", "right", "front-right", "toward you (front)", "front-left", "left", "back-left"][int(((ang_up + 22.5) % 360) // 45)]
    high_lo = (hi - lo) * 100

    out_line = path_d(gpoly, gf)
    bunkers = "".join(f'<path d="{path_d(g.intersection(gf.rect_utm()), gf)}"/>' for k, _, g in feats if k == "bunker" and g.intersects(gf.rect_utm()))
    svg = f"""<svg viewBox="0 0 {W} {H}" class="greenpanel" role="img" aria-label="Green slope read">
      <rect width="{W}" height="{H}" fill="rgb{PAPER}"/>
      <g fill="{SAND}" stroke="#C9B98E">{bunkers}</g>
      <image href="{heat}" width="{W}" height="{H}" preserveAspectRatio="none"/>
      <g class="gcont">{cont_svg}</g>
      <path d="{out_line}" fill="none" stroke="#5E7F56" stroke-width="1.4"/>
      <g class="garrows">{''.join(arrows)}</g>
    </svg>"""
    sl = pct[inside]
    share = {k: round(float((sl >= a_) .mean() * 100)) for k, a_ in (("ge2", 2), ("ge3", 3), ("ge4", 4))}
    stats = {"share": share, "overall_pct": round(overall, 1), "fall_rel": rel, "relief_cm": round(high_lo), "green_m2": round(gpoly.area),
             "pts": S.get("pts", 0), "density": round(S.get("density", 0), 1)}
    return svg, stats


HEAD = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Goose map styles · {course_name}</title>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@300..700&display=swap" rel="stylesheet">
<style>
:root{--paper:#F3F1EA;--surface:#fff;--ink:#111311;--muted:#545850;--rule:#CFCABD;--fairway:#1D5C3B;--flag:#C8402A}
*{box-sizing:border-box} body{margin:0;background:var(--paper);color:var(--ink);font-family:Geist,system-ui,sans-serif;font-weight:420;font-variant-numeric:tabular-nums}
header{padding:28px 28px 4px;max-width:1100px;margin:auto} h1{font-weight:550;letter-spacing:-.04em;font-size:30px;margin:0}
.sub{color:var(--muted);font-size:14px;margin-top:6px;max-width:760px;line-height:1.45}
.seg{display:inline-flex;border:1px solid var(--ink);border-radius:10px;overflow:hidden}
.seg button{font:inherit;font-weight:550;font-size:14px;padding:9px 16px;border:0;background:transparent;color:var(--ink);cursor:pointer;min-height:40px}
.seg button+button{border-left:1px solid var(--ink)} .seg button[aria-pressed=true]{background:var(--ink);color:var(--paper)}
.controls{display:flex;flex-wrap:wrap;gap:14px;margin-top:16px;align-items:center}
section{display:none} section.on{display:block}
.hhead{max-width:1100px;margin:18px auto 0;padding:0 28px;display:flex;gap:16px;align-items:baseline}
.hhead b{font-weight:550;font-size:22px;letter-spacing:-.03em}
.grid{display:grid;grid-template-columns:minmax(320px,1.15fr) minmax(300px,1fr);gap:24px;padding:14px 28px 28px;max-width:1100px;margin:auto;align-items:start}
@media (max-width:760px){.grid{grid-template-columns:1fr}}
.card{background:var(--surface);border:1px solid var(--rule);border-radius:14px;overflow:hidden}
.cap{display:flex;justify-content:space-between;align-items:baseline;padding:14px 16px 10px;border-bottom:1px solid var(--rule)}
.cap b{font-weight:550;font-size:17px;letter-spacing:-.02em} .lbl{font-size:11px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.hole{display:block;width:100%;height:auto}
.hd{display:flex;gap:18px;padding:12px 16px;border-top:1px solid var(--rule);font-size:13px;color:var(--muted)} .hd span b{color:var(--ink);font-weight:550;font-size:16px;letter-spacing:-.02em;display:block}

/* ---- shared marks ---- */
.holeline{fill:none;stroke:var(--ink);stroke-width:1.3;stroke-dasharray:5 5;opacity:.8}
.arc{fill:none;stroke:var(--ink);stroke-opacity:.5;stroke-width:1}
.arcl{font-size:12px;font-weight:600;fill:var(--ink);paint-order:stroke;stroke:#F3F1EAcc;stroke-width:3px}
.tee-mark circle{fill:var(--surface);stroke:var(--ink);stroke-width:1.6}
.contours path{fill:none;stroke:#6E6C58;stroke-opacity:.16;stroke-width:.6} .contours path.major{stroke-opacity:.30;stroke-width:.8}
.canopy path{fill:#C9D5BC;fill-opacity:.6;stroke:none}
.trees circle{fill:#AFC2A0;fill-opacity:.75;stroke:#3F4A3A;stroke-opacity:.35;stroke-width:.5}
.f-cart path{fill:none;stroke:#CFCABD;stroke-width:1.6;stroke-dasharray:1 4;stroke-linecap:round}

/* ---- Illustrated (Yardage Book) ---- */
.mode-book .img-blend,.mode-book .img-aerial,.mode-book .aerial-dim{display:none}
.mode-book .f-water path{fill:#D7E4EC;stroke:#9DB6C4;stroke-width:1}
.mode-book .f-fairway path,.mode-book .f-tee path{fill:#D9E7D1;stroke:#9FB896;stroke-width:1}
.mode-book .f-green path{fill:#BFD9B8;stroke:#7FA376;stroke-width:1.2}
.mode-book .f-bunker path{fill:#EFE6CF;stroke:#C9B98E;stroke-width:1}

/* ---- Blend: toned photo underneath, Yardage Book fills and lines on top ---- */
.mode-blend .img-aerial,.mode-blend .aerial-dim,.mode-blend .trees,.mode-blend .canopy,.mode-blend .f-cart{display:none}
.mode-blend .hill{opacity:.45} .mode-blend .contours{opacity:.8}
.mode-blend .f-water path{fill:#D7E4EC;fill-opacity:.82;stroke:#8FAAB9;stroke-width:1}
.mode-blend .f-fairway path,.mode-blend .f-tee path{fill:#D9E7D1;fill-opacity:.62;stroke:#5E7F56;stroke-opacity:.7;stroke-width:1}
.mode-blend .f-green path{fill:#A9CFA0;fill-opacity:.92;stroke:#2F5A30;stroke-width:1.4}
.mode-blend .f-bunker path{fill:#F1E8D2;fill-opacity:.95;stroke:#B8A57A;stroke-width:1}

/* ---- Aerial ---- */
.mode-aerial .img-blend,.mode-aerial .paper,.mode-aerial .hill,.mode-aerial .contours,.mode-aerial .canopy,.mode-aerial .trees,.mode-aerial .f-cart{display:none}
.mode-aerial .f-water path{fill:#9FD3E8;fill-opacity:.18;stroke:#fff;stroke-opacity:.75;stroke-width:1}
.mode-aerial .f-fairway path{fill:#fff;fill-opacity:.06;stroke:#fff;stroke-opacity:.85;stroke-width:1.1}
.mode-aerial .f-tee path{fill:none;stroke:#fff;stroke-opacity:.7;stroke-width:1}
.mode-aerial .f-green path{fill:#fff;fill-opacity:.08;stroke:#fff;stroke-width:1.6}
.mode-aerial .f-bunker path{fill:#fff;fill-opacity:.10;stroke:#fff;stroke-opacity:.9;stroke-width:1}
.mode-aerial .holeline{stroke:#fff;opacity:.95} .mode-aerial .arc{stroke:#fff;stroke-opacity:.85}
.mode-aerial .arcl{fill:#fff;stroke:#00000066;stroke-width:2px}

/* ---- green panel ---- */
.greenpanel{display:block;width:100%;height:auto}
.gcont path{fill:none;stroke:#3F4A3A;stroke-opacity:.25;stroke-width:.7}
.garrows path{fill:none;stroke:var(--ink);stroke-opacity:.85;stroke-width:1.1;stroke-linecap:round;stroke-linejoin:round}
.read{padding:14px 16px 16px;border-top:1px solid var(--rule);font-size:15px;line-height:1.45} .read .call{font-size:19px;font-weight:500;letter-spacing:-.01em}
.legend{display:flex;gap:10px;flex-wrap:wrap;padding:0 16px 14px;font-size:12px;color:var(--muted)} .sw{display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:-2px;margin-right:4px;border:1px solid #0001}
.note{max-width:1100px;margin:0 auto 40px;padding:0 28px;color:var(--muted);font-size:13px;line-height:1.5}
</style></head><body>
<header><div class="lbl">Map style prototype · {course_name}</div><h1>The Goose hole view</h1>
<div class="sub">Blend is the proposed default: the aerial photo toned into the Yardage Book palette, with flat fills, terrain shading and contours on top. Switch to Illustrated or Aerial at any time. Tee at the bottom, green at the top; arcs show yards to the middle of the green.</div>
<div class="controls"><div class="seg" role="group" aria-label="Hole">{tabs}</div><div class="seg" role="group" aria-label="Map style">
<button data-mode="mode-blend" aria-pressed="true">Blend</button><button data-mode="mode-book" aria-pressed="false">Illustrated</button><button data-mode="mode-aerial" aria-pressed="false">Aerial</button></div></div></header>
"""

SECTION = """<section id="h{hole}" class="{on}">
<div class="hhead"><b>Hole {hole} · Par {par} · {yd} yds</b><span class="lbl">tee to middle of green</span></div>
<div class="grid">
 <div class="card"><div class="cap"><b>Hole view</b><span class="lbl stylename">Blend</span></div>{svg}
  <div class="hd"><span>Photo<b>USGS NAIP</b></span><span>Terrain<b>1 m lidar</b></span><span>Trees<b>{ntrees} from lidar</b></span></div></div>
 <div class="card"><div class="cap"><b>Green read</b><span class="lbl">Directional</span></div>{green}
  <div class="read"><div class="call">Falls {fall_rel}, about {overall_pct}% overall.</div>
  <div style="color:var(--muted);margin-top:6px">{relief_cm} cm from high to low; {ge3}% of the green is 3% or steeper. Arrows point downhill; longer means steeper. Viewed from the fairway.</div></div>
  <div class="legend"><span><i class="sw" style="background:#E2ECDC"></i>0–1%</span><span><i class="sw" style="background:#C6DEBC"></i>1–2%</span><span><i class="sw" style="background:#E9DDA8"></i>2–3%</span><span><i class="sw" style="background:#E8BE8C"></i>3–4%</span><span><i class="sw" style="background:#DA946C"></i>4%+</span></div></div>
</div>
<div class="note">{source_note}</div>
</section>"""

TAIL = """<script>
const names={'mode-blend':'Blend','mode-book':'Illustrated','mode-aerial':'Aerial'};
let mode='mode-blend';
function apply(){document.querySelectorAll('svg.hole').forEach(s=>{s.classList.remove('mode-blend','mode-book','mode-aerial');s.classList.add(mode)});
 document.querySelectorAll('.stylename').forEach(e=>e.textContent=names[mode]);
 document.querySelectorAll('[data-mode]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.mode===mode));}
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{mode=b.dataset.mode;apply();});
document.querySelectorAll('[data-h]').forEach(b=>b.onclick=()=>{
 document.querySelectorAll('[data-h]').forEach(x=>x.setAttribute('aria-pressed',x===b));
 document.querySelectorAll('section').forEach(s=>s.classList.toggle('on',s.id===b.dataset.h));});
apply();
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--course", required=True)
    ap.add_argument("--holes", nargs="+", type=int, required=True)
    ap.add_argument("--course-name", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    secs, tabs = [], []
    for i, hole in enumerate(a.holes):
        svg, green, m = render(a.course, hole, a.out)
        if m["src"] == "lidar":
            note = (f"Green surface from {m['pts']:,} USGS lidar ground points on the green (2023 survey, about {m['density']:.0f} per m²), smoothed over about 1 m. "
                    "Lidar height error is a few centimetres, close to the size of the slopes on a green, so read this as the general break, not an exact line. "
                    "Greens rebuilt after 2023 will be out of date.")
        else:
            note = "Green surface from the 1 m elevation model (lidar ground points not loaded), so the read is coarse."
        secs.append(SECTION.format(hole=hole, on="on" if i == 0 else "", par=m["par"], yd=m["yd"], svg=svg,
                                   green=green, ntrees=f"{m['ntrees']:,}", fall_rel=m["fall_rel"], overall_pct=m["overall_pct"],
                                   relief_cm=m["relief_cm"], ge3=m["share"]["ge3"], source_note=note))
        tabs.append(f'<button data-h="h{hole}" aria-pressed="{str(i == 0).lower()}">Hole {hole}</button>')
        print(json.dumps({k: v for k, v in m.items() if k != "share"}))
    html = HEAD.replace("{course_name}", a.course_name or a.course).replace("{tabs}", "".join(tabs)) + "".join(secs) + TAIL
    Path(a.out).write_text(html)
    print(f"{len(html)/1e6:.1f} MB")


if __name__ == "__main__":
    main()
