# Roosevelt Variance Report — iGolf vs Manual vs LiDAR-OSM

**Generated:** 2026-05-01
**Engine versions audited (no modifications):**
- `src/lib/strategyEngine.ts`
- `src/lib/shotDecisionEngine.ts`
- `src/lib/caddieDecisionEngine.ts`
- `src/lib/greenIntelligenceEngine.ts`
- `src/lib/terrainService.ts` + `src/lib/terrainAdapterIgolf.ts`
- `src/pages/SimulatedRound.tsx` (data plumbing)

## Rows under test

| Row | id | mapping_source | igolf_id | holes |
|---|---|---|---|---|
| **iGolf**     | `0df6b692-955c-4778-9be2-49bbe56f0ad3` | `igolf`       | `4bXCfj78Kmv3` | 9 |
| **Manual**    | `0a900582-9883-4da8-a0b9-c9d2feb5976e` | `manual`      | `4bXCfj78Kmv3` ⚠ | 9 |
| **LiDAR-OSM** | `7c30d831-f922-4b10-ac8b-85b255e5fc43` | `manual:auto` | `NULL`         | 9 |

⚠ The Manual row has `igolf_id` set, which violates the project rule
"`mapping_source = manual` must have `igolf_id = NULL`". Reported only — not modified.

## Method

The deterministic strategy/shot/green pipeline is pure data-in/data-out
(`courseStrategyModel.ts`, `strategyEngine.ts`, `shotDecisionEngine.ts`,
`greenIntelligenceEngine.ts`). Variance between the three rows is therefore
fully predicted by **what shape each row puts into `hole_data`,
`green_slope_data`, `terrain_data`, and `course_intelligence`**, and **which
keys the engines actually read**. This report cross-references the two:
field-by-field shape, then a five-scenario walk-through, then a gap list.

## Top-level shape diff

| Top-level field            | iGolf                                                                                   | Manual                                                                          | LiDAR-OSM                                                                                              |
|---------------------------|-----------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| `green_slope_data`         | **array**, sample keys: `best_miss, general_slope, green_insights, green_slope_model, hole, pin_strategy, zones` | **array**, same keys as iGolf                                                   | **object** keyed by hole, sample keys: `best_miss, dominant_slope_deg, fall_direction, fall_line_azimuth_deg, false_front, mean_elevation_m, note, sample_count, zones` |
| `terrain_data`             | single `GooseTerrainGrid` (`bounds, elevations, numCols, numRows, provenance, sourceUnits`) | same as iGolf                                                                   | **per-hole object** `{1..9}`, each `{tee_elevation_m, green_elevation_m, net_delta_m, fairway_centerline_profile, green_elevation_grid}` |
| `course_intelligence` keys | `condition_rules, course_name, course_rating, course_style, default_strategy_principle, enriched_at, enrichment_adapter_version, location, slope_rating, strategy_identity, tees_available, yardages_by_tee` | `condition_rules, course_name, course_style, default_strategy_principle, location, strategy_identity` | `confidence_notes, data_sources, payload_version, pipeline, scorecard, tee_shot_corridors`             |

## hole_data shape diff (per-hole presence)

`bunkers` / `water_hazards` / `out_of_bounds` / `trees` columns are item
counts. `fp` = `fairway_polygon` vertex count. `gp` = `green_perimeter`
vertex count. `dft` = `terrain.tee_to_green_delta_ft`. `class` =
`terrain.uphill_downhill_class`. `centerline` =
`terrain.centerline_profile_ft` length. `strat` = `course_strategy`
present? `ftz`/`so`/`corr` = `fairway_target_zones` /
`strategy_options` / `tee_shot_corridors` lengths.

| Hole | Row       | par | bunkers | water | oob | trees | fp  | gp | dft   | class           | centerline | strat | ftz | so | corr |
|------|-----------|----:|--------:|------:|----:|------:|----:|---:|------:|-----------------|-----------:|:-----:|:---:|:--:|:----:|
| 1    | iGolf     |   4 |       1 |     0 |   0 |     0 |  67 | 45 |  39.9 | steep_uphill    |         11 |  Y    |  -  |  - |   -  |
| 1    | Manual    |   4 |       1 |     0 |   0 |     0 |  67 | 45 |   —   | —               |          0 |  Y    |  -  |  - |   -  |
| 1    | LiDAR-OSM |   4 |       1 |     0 |   0 |     0 |  46 | 31 |   —   | —               |          0 |  -    |  -  |  - |   -  |
| 2    | iGolf     |   4 |       0 |     0 |   0 |     0 |  69 | 47 |  42.4 | steep_uphill    |         16 |  Y    |  -  |  - |   -  |
| 2    | Manual    |   4 |       0 |     0 |   0 |     0 |  69 | 47 |   —   | —               |          0 |  Y    |  -  |  - |   -  |
| 2    | LiDAR-OSM |   4 |       0 |     0 |   0 |     0 |  62 | 32 |   —   | —               |          0 |  -    |  -  |  - |   -  |
| 3    | iGolf     |   3 |       1 |     0 |   0 |     0 |  54 | 43 |  -8.2 | mild_downhill   |          6 |  Y    |  -  |  - |   -  |
| 3    | Manual    |   3 |       1 |     0 |   0 |     0 |  54 | 43 |   —   | —               |          0 |  Y    |  -  |  - |   -  |
| 3    | LiDAR-OSM |   3 |       1 |     0 |   0 |     0 |   0 | 29 |   —   | —               |          0 |  -    |  -  |  - |   -  |
| 4    | iGolf     |   4 |       1 |     0 |   0 |     0 |  96 | 45 |   6.5 | mild_uphill     |         13 |  Y    |  -  |  1 |   -  |
| 4    | Manual    |   4 |       1 |     0 |   0 |     0 |  96 | 45 |   —   | —               |          0 |  Y    |  -  |  - |   -  |
| 4    | LiDAR-OSM |   4 |       1 |     0 |   0 |     0 |  38 | 17 |   —   | —               |          0 |  -    |  -  |  - |   -  |
| 5    | iGolf     |   4 |       1 |     0 |   0 |     0 |  99 | 42 |  -4.5 | mild_downhill   |         12 |  Y    |  -  |  - |   -  |
| 5    | Manual    |   4 |       1 |     0 |   0 |     0 |  99 | 42 |   —   | —               |          0 |  Y    |  -  |  - |   -  |
| 5    | LiDAR-OSM |   4 |       2 |     0 |   0 |     0 |  27 | 11 |   —   | —               |          0 |  -    |  -  |  - |   -  |
| 6    | iGolf     |   4 |       0 |     0 |   0 |     0 |  43 | 34 | -73.3 | steep_downhill  |         13 |  Y    |  -  |  - |   -  |
| 6    | Manual    |   4 |       0 |     0 |   0 |     0 |  40 | 34 |   —   | —               |          0 |  Y    |  -  |  - |   -  |
| 6    | LiDAR-OSM |   4 |       0 |     0 |   0 |     0 |  23 | 12 |   —   | —               |          0 |  -    |  -  |  - |   -  |
| 7    | iGolf     |   3 |       0 |     0 |   0 |     0 |  38 | 46 |  13.0 | moderate_uphill |          7 |  Y    |  -  |  - |   -  |
| 7    | Manual    |   3 |       0 |     0 |   0 |     0 |  38 | 46 |   —   | —               |          0 |  Y    |  -  |  - |   -  |
| 7    | LiDAR-OSM |   3 |       2 |     0 |   0 |     0 |  25 |  9 |   —   | —               |          0 |  -    |  -  |  - |   -  |
| 8    | iGolf     |   4 |       1 |     0 |   0 |     0 | 102 | 40 |   5.9 | mild_uphill     |         12 |  Y    |  -  |  - |   -  |
| 8    | Manual    |   4 |       1 |     0 |   0 |     0 | 102 | 40 |   —   | —               |          0 |  Y    |  -  |  - |   -  |
| 8    | LiDAR-OSM |   4 |       3 |     0 |   0 |     0 |  53 | 23 |   —   | —               |          0 |  -    |  -  |  - |   -  |
| 9    | iGolf     |   3 |       0 |     0 |   0 |     0 |  48 | 41 | -49.7 | steep_downhill  |          7 |  Y    |  -  |  - |   -  |
| 9    | Manual    |   3 |       0 |     0 |   0 |     0 |  48 | 41 |   —   | —               |          0 |  Y    |  -  |  - |   -  |
| 9    | LiDAR-OSM |   3 |       0 |     0 |   0 |     0 |  38 | 28 |   —   | —               |          0 |  -    |  -  |  - |   -  |

**Manual row note:** geometry mirrors iGolf (it was forked from iGolf
vectors), but every per-hole `terrain.*` field is empty — the Manual row
has no inline elevation summary. It still has `course_intelligence` =
`{condition_rules, course_style, default_strategy_principle,
strategy_identity}`, which is the source of its differentiation.

**LiDAR-OSM row note:** geometry exists but at much lower vertex counts
(e.g. H4 fp drops 96→38, gp drops 45→17; H3 fairway is empty). All
per-hole `terrain.*` keys are empty — the elevation data is stored at
the **top-level `terrain_data`** under per-hole keys instead. Authored
`course_strategy` is also absent from every hole.

## Five representative scenarios

For each scenario, the report tracks **inputs the engines actually read**
in `caddieDecisionEngine.recompute → strategyEngine.computeStrategy →
shotDecisionEngine.decide → caddieVoiceFormatter`. Where a row provides
no input, the engine falls back to the next tier in the
`authored-strategy-precedence` ladder.

### Scenario 1 — H1 tee shot (par 4, ~250–275y)

Geometry-grade source: `holeInfo.tee`, `green_center`, `fairway_polygon`,
`bunkers`, `terrain.tee_to_green_delta_ft`, `course_strategy.tee_strategy`.

| Field used by engine                       | iGolf                                       | Manual                                   | LiDAR-OSM                              |
|--------------------------------------------|---------------------------------------------|------------------------------------------|----------------------------------------|
| Yards baseline (`holeInfo.yards`)          | `null` → falls back to geodesic tee→green   | `null` → geodesic                        | `null` → geodesic (per-tee `yardages` object **silently ignored**) |
| Elevation (`terrain.tee_to_green_delta_ft`)| **+39.9 ft / steep_uphill**                 | absent → 0                               | absent → 0                             |
| Fairway polygon                            | 67-pt                                       | 67-pt                                    | **46-pt** (sparser; affects in_fairway test) |
| Authored `course_strategy.tee_strategy`    | `preferred_target=left_center`, `bias=hybrid_or_long_iron` | same                       | **absent**                             |
| **Predicted club**                         | hybrid / long iron (authored override)      | hybrid / long iron (authored override)   | driver default (no authored override; `tee-shot-strategy-logic` defaults to driver for par-4 ≥150y) |
| **Predicted target**                       | left-center fairway                         | left-center fairway                      | center fairway (geometric default)     |
| **Effective yardage**                      | raw + `+0.5 yd × 39.9` ≈ raw + 20 yds       | raw (no elevation)                       | raw (no elevation)                     |
| **Spoken commentary fingerprint**          | "uphill, club up, hybrid favored left-center" | "hybrid favored left-center"          | "driver, fairway center"               |

### Scenario 2 — H4 approach from 150y (par 4)

| Field used                                  | iGolf                          | Manual                         | LiDAR-OSM                       |
|---------------------------------------------|--------------------------------|--------------------------------|---------------------------------|
| `terrain.tee_to_green_delta_ft`             | +6.5 mild_uphill               | absent                         | absent                          |
| Bunker count (`hole.bunkers`)               | 1                              | 1                              | 1                               |
| `course_strategy.approach_strategy`         | authored                       | authored                       | absent                          |
| Green perimeter vertex count                | 45                             | 45                             | 17                              |
| Pin-zone strategies (`green_slope_data.pin_strategy`) | full 9-zone object  | full 9-zone object             | **absent** (LiDAR-OSM gs schema has no `pin_strategy` or `green_slope_model` keys) |
| **Predicted leave**                         | "below the hole, center"       | "below the hole, center"       | "center green"                  |
| **Effective yardage**                       | 150 + 3 = 153 yd               | 150 yd                         | 150 yd                          |

### Scenario 3 — H6 tee shot (par 4, **steep downhill -73.3 ft**)

This is the iGolf-vs-LiDAR delta the brief calls out.

| Field used                                  | iGolf                                            | Manual                       | LiDAR-OSM                     |
|---------------------------------------------|--------------------------------------------------|------------------------------|-------------------------------|
| `terrain.tee_to_green_delta_ft`             | **-73.3 / steep_downhill** (huge club-down signal)| absent                       | absent (LiDAR's per-hole `net_delta_m` lives at `terrain_data['6']` and is **never read**) |
| Authored `course_strategy.tee_strategy`     | present                                          | present                      | absent                        |
| Fairway polygon                             | 43-pt                                            | 40-pt                        | 23-pt                         |
| **Predicted club**                          | club down ≥ 1 (e.g. driver→3W or 3W→hybrid)      | driver (no elev)             | driver (no elev)              |
| **Spoken commentary fingerprint**           | "steep downhill — take less club, ball will fly" | "fairway, driver"            | "fairway, driver"             |
| **Δ vs iGolf**                              | baseline                                          | club mismatch (no elevation) | club mismatch (no elevation)  |

### Scenario 4 — H8 approach from 130y (mild_uphill +5.9, **3 LiDAR bunkers**)

| Field used                            | iGolf            | Manual           | LiDAR-OSM                                                               |
|---------------------------------------|------------------|------------------|--------------------------------------------------------------------------|
| `bunkers`                             | 1                | 1                | **3**                                                                    |
| `terrain.tee_to_green_delta_ft`       | +5.9             | absent           | absent                                                                   |
| **Predicted hazard commentary**       | "front bunker right" | "front bunker right" | **richer hazard count (3)**, but engine only mentions nearest 1–2; the extra two LiDAR bunkers ARE consumed by `caddieDecisionEngine.findNearestHazard` |
| **Effective yardage**                 | 130 + 3 ≈ 133 yd | 130 yd           | 130 yd                                                                   |

### Scenario 5 — H3 putt (par 3 green, slope read)

| Field used                                                        | iGolf                                                | Manual                                  | LiDAR-OSM                                          |
|-------------------------------------------------------------------|------------------------------------------------------|-----------------------------------------|----------------------------------------------------|
| `green_slope_data.zones`                                          | 9-zone slope grid (`severity`, `slope_direction`)    | 9-zone slope grid                       | zones present, but with **different schema**       |
| `green_slope_data.green_slope_model.dominantBreakDirection`        | "back-to-front"                                      | "back-to-front"                         | **absent** (LiDAR uses `fall_direction` + `fall_line_azimuth_deg` instead) |
| `green_slope_data.pin_strategy[zone].bestMiss`                    | full per-zone strategies                              | full per-zone strategies                | **absent**                                         |
| `green_slope_data.green_insights.{falseFronts,collectionZones,…}` | full                                                 | full                                    | **absent** (LiDAR has only `false_front` boolean and `note`) |
| Putt yards-to-feet (3× rule)                                      | applied                                              | applied                                 | applied                                            |
| **Predicted putt commentary**                                     | "back-to-front, leave it below the hole"             | same                                    | "uphill / downhill" (from `dominant_slope_deg`) — **break direction & pin advice missing** |

## Where LiDAR-OSM produces silence or wrong output (gap list)

For each gap: which engine reads what, where the LiDAR-OSM payload puts
the equivalent data, and the file/function that would need a tiny adapter.

| # | Symptom (LiDAR-OSM)                                                          | Engine consumer (file:fn)                                                                                  | LiDAR-OSM source key                                          | Cause                                                   |
|--:|------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|---------------------------------------------------------|
| 1 | **No elevation effect on any hole** (H1 +39.9, H6 -73.3, H9 -49.7 all → 0)  | `strategyEngine.ts:989` reads `opts.holeInfo.terrain.tee_to_green_delta_ft`; `shotDecisionEngine.ts:343` same; `useElevation.ts` consumes `parseTerrainGrid(courses.terrain_data)` (single grid only) | `terrain_data['<hole>'].net_delta_m` (per-hole, in metres)    | No adapter for per-hole / metric LiDAR terrain payload  |
| 2 | **Per-tee yardages dropped** (LiDAR has Black/Blue/White, runtime gets `null`) | `GooseSimulationRunner.tsx:900` and `OnCourseView.tsx:795` read `holeInfo.yards`                          | `hole_data[i].yardages.{black,blue,white}` and `course_intelligence.scorecard.holes[i].yardages` | No mapping from `yardages` object → `holeInfo.yards` numeric |
| 3 | **Course rating / slope rating absent** in any UI/voice copy                 | (unconsumed in deterministic engines today; iGolf row has them but they're not surfaced)                   | `course_intelligence.scorecard.{course_rating,slope_rating}` (LiDAR has them under `pipeline.scorecard`) | Not yet wired anywhere for any source                   |
| 4 | **No authored tee/approach strategy** for any hole                           | `strategyEngine.ts:754` (`extractHoleTypeContext`); `shotDecisionEngine.ts:905, 1040`                       | n/a — LiDAR row has no `course_strategy` per hole              | Authored layer was never produced (LiDAR ingest is geometry-only) |
| 5 | **Pin-zone strategy missing** (no "best miss / avoid / approach" per zone)   | `caddieDecisionEngine.ts` reads `greenSlope.pin_strategy[zone]`; `GreenIntelligencePanel.tsx`               | `green_slope_data['<hole>'].zones[zoneKey]` exists but with different keys (`fall_direction`, `dominant_slope_deg`); no `pin_strategy` block | Schema mismatch; no green-slope adapter for LiDAR payload |
| 6 | **Dominant break direction missing** in putt commentary                     | `greenIntelligenceEngine.ts` reads `green_slope_model.dominantBreakDirection`; `caddieVoiceFormatter` uses it | `green_slope_data['<hole>'].fall_direction` + `fall_line_azimuth_deg` | Field-name & shape mismatch                            |
| 7 | **Tee-shot corridors unused** (LiDAR has 9 CHM-raycast corridors)            | No consumer found in `src/`                                                                                | `course_intelligence.tee_shot_corridors`                       | Field exists but no engine reads it                     |
| 8 | **Centerline elevation profile unused**                                      | iGolf path uses `terrain.centerline_profile_ft`; runtime reads it as part of `holeInfo.terrain` only       | `terrain_data['<hole>'].fairway_centerline_profile`            | Wrong location (top-level vs per-hole `terrain` block)  |
| 9 | **Sparse fairway polygons distort `in_fairway` checks**                     | `landingZoneGenerator.scanHoleLandingZonesFromData` and `caddieDecisionEngine` polygon tests               | `hole_data[i].fairway_polygon` (e.g. H3 has 0 vertices, H4 has 38 vs iGolf 96) | Geometry density is lower; H3 is empty, which will degrade landing-zone scoring |
| 10| **`green_slope_data` is an object, not array** (already patched in UI loader) | `SimulatedRound.tsx:507` (now defensive)                                                                  | `green_slope_data` keyed by hole number                        | Recently fixed (object→array normalization). Engines still need an adapter for the field-key mismatch (#5, #6) |

## Summary table: variance by hole

| Hole | iGolf-vs-LiDAR material delta? | Where it shows up                                                       |
|-----:|--------------------------------|--------------------------------------------------------------------------|
|  1   | yes                            | +39.9 ft uphill ignored; authored tee strategy absent                    |
|  2   | yes                            | +42.4 ft uphill ignored; authored tee strategy absent                    |
|  3   | yes                            | mild downhill ignored; **fairway polygon empty** in LiDAR row            |
|  4   | yes                            | +6.5 ft ignored; authored strategy_options[1] absent                     |
|  5   | partial                        | -4.5 ft ignored; LiDAR adds 1 extra bunker (consumed)                    |
|  6   | **major**                      | -73.3 ft steep downhill **completely absent** — biggest club-selection delta |
|  7   | yes                            | +13 ft ignored; LiDAR adds 2 bunkers (consumed)                          |
|  8   | partial                        | +5.9 ft ignored; LiDAR adds 2 extra bunkers (consumed)                   |
|  9   | **major**                      | -49.7 ft steep downhill ignored                                          |

## Root-cause grouping (no fixes applied — report only)

- **A. Terrain shape mismatch** drives gaps #1 and #8. The runtime
  `GooseTerrainGrid` contract assumes a single grid; LiDAR persists
  per-hole metric summaries. A `terrainAdapterLidarOsm.ts` parallel to
  `terrainAdapterIgolf.ts` would resolve both, plus make
  `holeInfo.terrain.tee_to_green_delta_ft` populate from
  `terrain_data['<hole>'].net_delta_m * 3.28084`.
- **B. Green-slope schema mismatch** drives gaps #5 and #6. A
  `greenSlopeAdapterLidarOsm` would map `fall_direction` →
  `green_slope_model.dominantBreakDirection` and synthesize
  `pin_strategy` from `zones` + `fall_line_azimuth_deg`.
- **C. Authored layer absence** drives gap #4. This is by design for
  LiDAR-only ingest; the deterministic geometry fallbacks already
  handle it, but commentary will be terser.
- **D. Yardage / scorecard plumbing** drives gaps #2 and #3. A small
  selector that maps `hole.yardages.<active_tee>` → `holeInfo.yards`
  closes #2; #3 needs a UI surface, not engine work.
- **E. Geometry density** drives gap #9. Not a bug — a data-quality
  observation. H3's empty fairway polygon will degrade landing-zone
  output regardless of any engine change.

## Files that would need touching to close the gaps (reference only — NOT modified)

- `src/lib/terrainService.ts` (new adapter entry point)
- `src/lib/terrainAdapterLidarOsm.ts` (NEW)
- `src/lib/greenIntelligenceEngine.ts` (alt schema branch)
- `src/lib/courseSourceResolver.ts` (route `manual:auto` → LiDAR adapters)
- `src/pages/SimulatedRound.tsx` (yardage selector for `holeInfo.yards`)
- `src/components/simulation/GooseSimulationRunner.tsx` (same)
