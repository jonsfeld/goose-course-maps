# goose-course-maps

High-fidelity golf course mappings for the Goose AI caddie.

Each course is a `MAP.md` — a single, self-contained document combining
course metadata, hole geometry, LiDAR-derived terrain, green slope data,
tree-corridor analysis, and (optionally) human-authored strategy zones.
See [SCHEMA.md](./SCHEMA.md) for the full format spec.

## Pipeline overview

```
satellite imagery  ─┐
                    ├─▶  QGIS / Python  ─▶  map.auto.md   (Pass 1, full-auto)
LiDAR DEM + LPC   ─┘                        map.human.md  (Pass 2, human-in-loop)
                                            variance_report.md
```

- **Pass 1 (auto):** scripted data pull, vision-model / segmentation polygon tracing, deterministic terrain derivation, assembled MAP.md. Fast, good enough to test against the Goose runtime.
- **Pass 2 (human):** surgical human corrections in QGIS on the layers where Pass 1 is weakest (fringe, first cut, OB, obstructive tree flagging) + human-authored strategy.
- **Variance report:** IoU + boundary-distance deltas per layer, so the difference between "what automation can do" and "what humans add" is measurable.

## Repo layout

```
goose-course-maps/
├── README.md            # this file
├── SCHEMA.md            # MAP.md format spec — the source of truth
├── courses/
│   └── <course_slug>/
│       ├── map.auto.md
│       ├── map.human.md
│       ├── sources/     # raw downloads (gitignored, too large)
│       ├── derived/     # intermediate rasters (slope, hillshade, CHM)
│       └── notes/       # scorecard, architect lookups, source URLs
├── templates/
│   └── map.template.md  # blank MAP.md mirroring SCHEMA.md
├── tools/               # Phase 2 Python CLI (not yet implemented)
└── docs/                # design notes, variance-report methodology
```

## Current state

- Schema: draft v0.1 in [SCHEMA.md](./SCHEMA.md)
- First course: **Roosevelt Golf Course** (Griffith Park, LA) — 9 holes, par 33
- Pipeline code: not yet written (next step after schema signoff)

## Relationship to Goose app

This repo produces the course-data artifacts the Goose runtime consumes. Field names in MAP.md mirror the existing Goose Supabase `courses` table shape (`tee`, `green_center`, `green_perimeter`, `fairway_polygon`, `water_hazards`, `bunkers`, `out_of_bounds`, `green_slope_data`, `terrain_data`) so MAP.md deserializes cleanly without adapter code. New enrichment fields (first cut, fringe, tree corridor, 0.5m green elevation grid) are additive and optional — they don't break existing courses.
