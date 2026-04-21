# Phase B v1 — classical-CV feature tracing (Roosevelt LA)

First-pass automated tracing. Honest record of what works, what doesn't, and what to fix.

## Method

Pixel classification from NAIP 4-band (R,G,B,NIR) + derived CHM + slope rasters, resampled to NAIP grid. Single-pass rule-based classifier:

1. **NDVI** from NIR + R → vegetation mask.
2. **CHM threshold** → tree_canopy (≥2m) vs mowed grass (≤1m).
3. **Slope threshold** within mowed → fairway (≤5°) vs green (≤2.5° + high NDVI).
4. **Sand signature** (low NDVI, high brightness, flat) + **shell-surround check** (≥20% of 3m shell is mowed grass) → bunker.
5. **Blue-dominance** → water.
6. **Morphological open+close** to suppress pixel noise and merge fragments.
7. **Polygonize** with per-kind min-area thresholds.

## Output

`derived/features.geojson` — FeatureCollection with `properties.kind` ∈ {tree_canopy, fairway, green, bunker, water, rough}.

## Known limitations (honest)

| Layer | Count | Reality check | Confidence |
|---|---|---|---|
| tree_canopy | 579 | reasonable canopy density; may include some hillside shrubs | Medium-high |
| fairway | 5 | course has 9 holes — fairways merged across hole boundaries via morphological closing | **Low for per-hole assignment**, OK for "course area" |
| green | 15 | should be 9 — over-segmented (bright patches within fairway pass green NDVI threshold) | **Low** |
| bunker | 21 | realistic range for 9-hole muni | Medium |
| water | 0 | no water on Roosevelt; sensible | N/A |
| rough | 51 | broad catch-all for remaining vegetation | Low |

## What this first-pass is useful for

- Identifying course footprint (polygon union of fairway + green + bunker ≈ playable area)
- Seeding Phase C.5 work (green elevation grid per-green-polygon, tee corridor raycast)
- Running the end-to-end pipeline assembly (Phase E — map.auto.md)
- Providing a baseline to beat in Phase B v2 (variance measurement)

## What this first-pass is NOT ready for

- Per-hole feature assignment (green 1, green 2, etc.) — would need clustering + scorecard logic
- Prescriptive caddie calls like "you're 12 yd short of the front of the green" — green boundaries too noisy
- First-cut or fringe bands — classical CV can't resolve narrow color gradients reliably
- Tee-box polygons — not attempted (needs hole-start geometry)
- OB lines — not derivable from imagery alone

## Path to Phase B v2

In priority order:

1. **SAM2 prompted segmentation** — use the current v1 masks as point prompts; SAM2 gives clean polygon boundaries. Expected: green IoU 75→90%, fairway IoU 65→85%.
2. **Per-green merging via connected components + hull** — post-process v1 green polygons: cluster nearby greens, take convex hull of each cluster. Might yield 9 clean greens from v1's 15.
3. **Hole assignment** — after clean polygons, walk the course (tee → fairway → green) using spatial ordering + scorecard par/yardage distances.
4. **Manual QGIS corrections** — the ground truth for variance reporting.

## Data source for variance reporting

When Phase B v2 runs, compare against this v1 output using:
- IoU per feature
- Polygon count delta
- Boundary Hausdorff distance

Variance report goes in `courses/roosevelt_la/notes/variance_report.md` (future).
