# Roosevelt GC — Course Layout (from operator diagram)

**Source:** Official Roosevelt Municipal GC course layout diagram (stylized, not-to-scale plan view shown in user chat 2026-04-20).

**Authoritative claims (counts + topology):**

- **9 holes total.** Par 33.
- **9 greens.** Exactly. Any automated tracing returning ≠ 9 is wrong.
- **9 tees.** One tee marker per hole on the reference (assumed default/back tee).
- **Starter Shack** at the southwest corner of the property — anchors hole 1 tee and hole 9 green near the clubhouse/parking area.
- **Bunkers visible in the diagram:** concentrated on holes 4, 5, 8 — roughly 15–20 total across the course.

**Relative positions (from diagram, as orientation for NAIP correlation):**

| Hole | Rough location on diagram | Approx routing |
|---|---|---|
| 1 | Left side, runs north from starter shack | Short, N-S, tee south / green north |
| 2 | Upper-left, long fairway running roughly W-to-E | Long dogleg; green on right |
| 3 | Top-center, points north | North-pointing dogleg; green at northernmost extent of course |
| 4 | Middle of property, W-to-E | Bunkers flank fairway; green on right |
| 5 | Middle, angled diagonal | Dogleg with multiple bunkers |
| 6 | Right (east) side | Long hole running roughly N-S on east flank |
| 7 | Lower-right, short | Short horizontal; green on right side |
| 8 | Lower-center, angled toward clubhouse | Long dogleg with bunkers; green on left (back toward starter) |
| 9 | Bottom-center-left, runs toward starter | Short, returns to near starter shack |

**How we'll use this:**

- Ground truth for "how many greens exist" (9, not my classifier's 15).
- Guide for visually identifying each hole's green on the NAIP.
- Source of `hole_id` assignment for downstream features.
- Cross-check on bunker count after tracing.

**What this diagram cannot do:**

- It's stylized / artistic, NOT geo-accurate. Shapes are not polygon-accurate. We do NOT georeference it directly — instead we use it as a reading guide next to the real NAIP.
