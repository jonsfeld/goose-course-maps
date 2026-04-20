# Roosevelt Golf Course — notes

9-hole par-33 municipal course in Griffith Park, Los Angeles.

**Status:** scaffolded, no data fetched yet.

## Pending lookups (Phase A)

- [ ] Verify exact address / coordinates
- [ ] Architect + year opened
- [ ] Most recent renovation
- [ ] Grass types (tee / fairway / rough / green)
- [ ] Scorecard: par, handicap index, yardages per tee set
- [ ] Total yardages per tee set + course rating / slope
- [ ] Source URLs for each lookup (store here for provenance)

## Pending data pulls (Phase A)

- [ ] USGS 3DEP 1m DEM tile for course bbox
- [ ] USGS LPC raw `.laz` tiles for course bbox
- [ ] NAIP or ESRI high-res aerial imagery for course bbox

## Files in this directory

Once populated, expect:
- `scorecard.md` — scorecard + handicaps with source URLs
- `architect_lookup.md` — provenance notes on metadata lookups
- `bbox.geojson` — precise course footprint polygon used for data fetching
