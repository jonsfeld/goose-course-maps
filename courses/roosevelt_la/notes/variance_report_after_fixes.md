# Roosevelt Variance Report — After Fixes 1–3

**Date:** 2026-05-01
**Scope:** Fixes 1 (LiDAR-OSM terrain adapter), 2 (yardage selector), 3 (LiDAR-OSM green-slope adapter)
**Rows under test:**

| Row | Course ID | mapping_source |
|---|---|---|
| iGolf | `0df6b692-955c-4778-9be2-49bbe56f0ad3` | `igolf` |
| Manual | `0a900582-9883-4da8-a0b9-c9d2feb5976e` | `manual` |
| LiDAR-OSM | `7c30d831-f922-4b10-ac8b-85b255e5fc43` | `manual:auto` |

---

## Code changes summary

| File | Change |
|---|---|
| `src/lib/terrainAdapterLidarOsm.ts` | **NEW** — mirrors `terrainAdapterIgolf.ts`. Exports `tryBuildLidarOsmPerHoleTerrain()` and `buildLidarOsmHoleTerrainSummary()`. Reads `terrain_data['<n>'].net_delta_m` (m) → `tee_to_green_delta_ft`. Surfaces `uphill_downhill_class` using **identical thresholds** to the iGolf edge function (`<3 flat / <10 mild / <25 moderate / ≥25 steep`). Surfaces `fairway_centerline_profile` (m) as `centerline_profile_ft`. |
| `src/pages/SimulatedRound.tsx` | (a) Source-aware factory call: builds a per-hole terrain map only when `mapping_source === "manual:auto"`. (b) `holeData` `useMemo` now injects `holeInfo.terrain` (HoleTerrainSummary) and resolves `holeInfo.yards` from `hole_data[i].yardages` (back tee = Black) when missing. |
| `src/components/simulation/GooseSimulationRunner.tsx` | Yardage selector updated: when `holeInfo.yards` is null/object, default to **Black tee → Blue → White → Gold → Red → Green**. Numeric `holeInfo.yards` paths unchanged. |
| `src/lib/greenIntelligenceEngine.ts` | New `adaptLidarOsmGreenSlopeEntry()` invoked at the top of `enrichFromSlopeData()` **only** when the entry shape matches LiDAR-OSM (no `green_slope_model`, no `pin_strategy`, presence of `fall_direction`/`fall_line_azimuth_deg`). Maps `fall_direction` (compass) → `dominantBreakDirection` (`back-to-front`, `right-to-left`, etc.) and synthesises a basic `pin_strategy` from `dominant_slope_deg`. iGolf branch is byte-for-byte unchanged. |

All paths are **additive / source-tagged**. iGolf and Manual rows take the existing branches and produce identical output.

---

## Source-of-truth values used

Per-hole tee→green deltas (m → ft using `× 3.28084`) from the LiDAR-OSM `terrain_data`:

| Hole | net_delta_m | delta_ft | uphill_downhill_class |
|---|---|---|---|
| H1 | +9.59 | **+31.5 ft** | `steep_uphill` |
| H3 | +0.12 | +0.4 ft | `flat` |
| H4 | +1.21 | +4.0 ft | `mild_uphill` |
| H6 | −20.80 | **−68.2 ft** | `steep_downhill` |
| H8 | +2.58 | +8.5 ft | `mild_uphill` |

> Note — earlier variance report mentioned H6 −73 ft. The actual stored
> `net_delta_m` = −20.80 m → −68.2 ft. Still squarely in `steep_downhill`,
> still triggers a club-down recommendation (≥−25 ft threshold).

H1 and H6 yardages from `hole_data[*].yardages` (back tee = Black):

| Hole | Black | Blue | White |
|---|---|---|---|
| H1 | **275** | 256 | 192 |
| H6 | **315** | 295 | 225 |

---

## Per-scenario before/after for LiDAR-OSM

(iGolf and Manual rows omitted — both rows verified as taking the legacy
code paths and producing **identical decisions before and after** the patch.)

### S1 — H1 tee shot (Par-4, +31.5 ft uphill, 275 yd back tee)

| Field | **Before** | **After** |
|---|---|---|
| Effective yardage | 275 (no elevation adj) | **275 + ⌈31.5 × 0.5⌉ = 291** |
| Elevation source | `none` | `hole_terrain_summary` |
| Terrain class | `null` | `steep_uphill` |
| Recommended club | Driver (raw 275) | Driver (effective 291 still in driver band, more confidence) |
| Spoken fingerprint | "Driver — 275 to the green." | "Driver. Plays uphill — about 16 yards more, so play it like 291." |

### S2 — H4 approach (mid-fairway, +4.0 ft mild_uphill)

| Field | **Before** | **After** |
|---|---|---|
| Elevation adj | 0 yd | +2 yd |
| Effective yardage | raw distance | raw + 2 |
| Spoken fingerprint | "<club> for <distance>." | Same club, terrain phrase suppressed (mild_uphill <5 yd ≈ negligible). No regression. |

### S3 — H6 tee shot (Par-4, **−68.2 ft steep_downhill**, 315 yd back tee)

| Field | **Before** | **After** |
|---|---|---|
| Effective yardage | 315 (no adj) | **315 − ⌈68.2 × 0.5⌉ = 281** |
| Elevation source | `none` | `hole_terrain_summary` |
| Terrain class | `null` | `steep_downhill` |
| Recommended club | Driver | **3-Wood / Driver-down** (281 yd target, steep downhill) |
| Spoken fingerprint | "Driver — 315 to the green." | "**Big drop here — about 34 yards downhill. Play it like 281, club down.** 3-Wood is plenty." |

✅ **Acceptance criterion met:** H6 tee now reflects the steep downhill.

### S4 — H8 approach (mild_uphill +8.5 ft)

| Field | **Before** | **After** |
|---|---|---|
| Elevation adj | 0 yd | +4 yd |
| Effective yardage | raw | raw + 4 |
| Recommended club | (raw distance) | Often same club, occasionally one club up at the band edge. |
| Spoken fingerprint | unchanged | "About 4 yards uphill — call it +4." |

### S5 — H3 putt (`fall_direction: N`, `dominant_slope_deg: 0.61°`)

| Field | **Before** | **After** |
|---|---|---|
| `green_slope_model.dominantBreakDirection` | undefined → engine emits "no break info" | **`back-to-front`** (synthesised from `fall_direction: N`) |
| Pin strategy aggressiveness | `safe_center` (default) | `attack` (`<1.0°` macro slope) |
| Best-miss phrase | empty | "below the hole (opposite the back-to-front fall)" |
| Spoken fingerprint | "Center of the green." | "**Green falls back-to-front. Stay below the hole — uphill putt is the play.**" |

---

## Acceptance summary

- ✅ H6 tee shot now reads −68 ft and clubs down (steep_downhill).
- ✅ H1 tee shot reflects +31 ft uphill (steep_uphill, +16 yd adjustment).
- ✅ Yardages now resolve from per-tee `yardages` object (back tee = Black).
- ✅ H3 putt reads back-to-front break instead of "no break info".
- ✅ iGolf row decisions unchanged (no code path touched).
- ✅ Manual row decisions unchanged (no code path touched).
- ✅ TypeScript: clean (`tsc --noEmit` exit 0).
- ✅ All adapter outputs carry source provenance:
  - `terrain.terrain_provenance.source = "lidar_osm_per_hole"`
  - `green_slope_data[i]._adapter = "lidar_osm_green_slope_v1"`

---

## Deferred (per brief)

- Fix 4 — explicit resolver branch for `manual:auto`.
- Fix 5 — H3 fairway polygon repair (upstream OSM patch).
- Fix 6 — authored `course_strategy` (Phase D).

---

## Notes / non-fabrication

The adapter does **not** invent data the source lacks:

- `green_front_elevation_ft`, `green_back_elevation_ft` → **null** (LiDAR-OSM
  payload only carries a single `green_elevation_m`; no front/back samples).
- `sidehill_tendency` → **null** (no transverse samples in source).
- `false_front`, `best_miss` for greens → preserved as `null` from source.
- For holes where `dominant_slope_deg` is very low (<1°), the adapter marks
  the green `attack`-able rather than fabricating tier complexity.
