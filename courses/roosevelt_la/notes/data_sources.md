# Roosevelt Golf Course — Geospatial Data Sources

**Target bbox for queries (Roosevelt footprint with margin):** -118.305, 34.120, -118.290, 34.133 (WGS84)
**Centroid:** 34.1265, -118.2967
**UTM Zone:** 11N (NAD83(2011))
**Compiled:** 2026-04-20
**Queries performed against:** TNM Access API (`https://tnmaccess.nationalmap.gov/api/v1/products`)

---

## 1. USGS 3DEP 1-meter bare-earth DEM

**Primary dataset (current):** `CA_LosAngeles_B23`
- **Publish date:** 2025-08-11 (per TNM Access) — matches the user's expected "CA_LosAngeles" B23 vintage; distinct from "CA_CaliforniaGaps_B23."
- **Source lidar collection (from LPC):** CA_LosAngeles_1_B23, lidar collected **2023-01-08 through 2024-01-07** (see LPC section below).
- **Resolution:** 1 m, bare-earth, GeoTIFF (32-bit float).
- **Project coverage (from OpenTopography):** ~11,536 km² across LA region; central-LA tiles include Griffith Park.
- **Tiles intersecting the Roosevelt bbox (2 tiles, full coverage):**
  | Tile | URL | Size |
  |------|-----|------|
  | `USGS_1M_11_x37y378_CA_LosAngeles_B23` (bbox −118.410 to −118.300, 34.063 to 34.154) | https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/Projects/CA_LosAngeles_B23/TIFF/USGS_1M_11_x37y378_CA_LosAngeles_B23.tif | **345.8 MB** (362,376,232 bytes) |
  | `USGS_1M_11_x38y378_CA_LosAngeles_B23` (bbox −118.302 to −118.192, 34.064 to 34.155) | https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/Projects/CA_LosAngeles_B23/TIFF/USGS_1M_11_x38y378_CA_LosAngeles_B23.tif | **344.9 MB** (361,662,348 bytes) |
- **Total download for DEM coverage:** ~690 MB for 2 full 10km × 10km tiles. The Roosevelt course spans the western edge of the `x38y378` tile and the eastern edge of the `x37y378` tile, so both are needed.

**Previous vintage (still available, lower density):** `CA_LosAngeles_2016`
- **Publish date:** 2020-03-30.
- **Lidar collection:** 2016.
- **Tiles:** `USGS_one_meter_x37y378_CA_LosAngeles_2016.tif` and `USGS_one_meter_x38y378_CA_LosAngeles_2016.tif` (same tile grid as above).
- **URLs:**
  - https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/Projects/CA_LosAngeles_2016/TIFF/USGS_one_meter_x37y378_CA_LosAngeles_2016.tif
  - https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/Projects/CA_LosAngeles_2016/TIFF/USGS_one_meter_x38y378_CA_LosAngeles_2016.tif
- **File sizes:** TNM Access did not populate `sizeInBytes` for these two tiles; estimated 250–350 MB each by comparison with the B23 tiles over the same footprint.

**Not covering Roosevelt (important negatives):**
- `CA_LAPostWildfire_Eaton` (publish 2025-09-17, acquired 2025-01-21 to -22) — bbox −118.193 to −117.998 / 34.154 to 34.254 — **east of Roosevelt, does not cover Griffith Park.** [A]
- `CA_LAPostWildfire_Palisades` (publish 2025-09-17, acquired 2025-01-21) — bbox −118.710 to −118.420 / 34.000 to 34.140 — **west of Roosevelt, does not cover Griffith Park.** [A]
- `CA_CaliforniaGaps_B23` — not returned by TNM Access for the Roosevelt bbox. The "gaps" project fills non-urban holes in statewide coverage, so central LA being excluded is consistent. Not used.
- `CA_SoCal_Wildfires_2018` — not returned by TNM Access for the Roosevelt bbox. Not used.

**Recommendation for Step A2:** pull the two `CA_LosAngeles_B23` 1m DEM tiles (≈690 MB total). That is the newest, highest-density bare-earth product covering Roosevelt. Keep the 2016 tiles as a fallback for differencing/validation.

---

## 2. USGS 3DEP Lidar Point Cloud (raw LAZ)

**Primary collection (current):** `USGS LPC CA LosAngeles B23` — files staged under S3 path `StagedProducts/Elevation/LPC/Projects/CA_LosAngeles_B23/CA_LosAngeles_1_B23/LAZ/`.
- **Publish date:** 2025-06-13.
- **Collection dates:** 2023-01-08 to 2024-01-07 (per OpenTopography metadata for CA_LosAngeles_1_B23).
- **Point density:** 18.80 pts/m² (OpenTopography).
- **Format:** LAZ 1.4, Classified (ASPRS classes incl. Class 2 ground).
- **Tile grid:** ~1 km × 1 km UTM 11N tiles, tile IDs like `11SLT038000377600` (E/N in hundreds of meters).
- **Tiles intersecting the Roosevelt bbox (6 tiles, current B23 vintage):**
  | Tile | Bbox (lon/lat) | Size |
  |------|-----------------|------|
  | `11SLT037900377600` | −118.312 to −118.301, 34.118 to 34.127 | **108.1 MB** |
  | `11SLT037900377700` | −118.312 to −118.301, 34.127 to 34.136 | **148.4 MB** |
  | `11SLT038000377600` | −118.301 to −118.290, 34.118 to 34.127 | **131.4 MB** |
  | `11SLT038000377700` | −118.301 to −118.290, 34.127 to 34.136 | **163.0 MB** |
  | `11SLT038100377600` | −118.290 to −118.280, 34.118 to 34.127 | **172.2 MB** |
  | `11SLT038100377700` | −118.291 to −118.280, 34.127 to 34.136 | **166.7 MB** |
- **Total for B23 LPC coverage:** ~889.7 MB for 6 tiles.
- **URL pattern:**
  ```
  https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/CA_LosAngeles_B23/CA_LosAngeles_1_B23/LAZ/USGS_LPC_CA_LosAngeles_B23_<TILE_ID>.laz
  ```
- **Full URL list (copy-paste ready for Step A2):**
  - https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/CA_LosAngeles_B23/CA_LosAngeles_1_B23/LAZ/USGS_LPC_CA_LosAngeles_B23_11SLT037900377600.laz
  - https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/CA_LosAngeles_B23/CA_LosAngeles_1_B23/LAZ/USGS_LPC_CA_LosAngeles_B23_11SLT037900377700.laz
  - https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/CA_LosAngeles_B23/CA_LosAngeles_1_B23/LAZ/USGS_LPC_CA_LosAngeles_B23_11SLT038000377600.laz
  - https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/CA_LosAngeles_B23/CA_LosAngeles_1_B23/LAZ/USGS_LPC_CA_LosAngeles_B23_11SLT038000377700.laz
  - https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/CA_LosAngeles_B23/CA_LosAngeles_1_B23/LAZ/USGS_LPC_CA_LosAngeles_B23_11SLT038100377600.laz
  - https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/CA_LosAngeles_B23/CA_LosAngeles_1_B23/LAZ/USGS_LPC_CA_LosAngeles_B23_11SLT038100377700.laz

**Previous collection (fallback):** `USGS LPC CA LosAngeles 2016 LAS 2018`
- **Publish date:** 2018-07-19.
- **Collection year:** 2016.
- **Tile grid:** different (LA County Regional Lidar L4 tile scheme, ~0.75 km × 0.75 km).
- **Tiles intersecting the Roosevelt bbox (4 tiles):**
  | Tile | Bbox | Size |
  |------|------|------|
  | `L4_6466_1863c` | −118.306 to −118.297, 34.119 to 34.126 | **17.5 MB** |
  | `L4_6466_1868d` | −118.306 to −118.297, 34.126 to 34.133 | **14.7 MB** |
  | `L4_6471_1863b` | −118.297 to −118.288, 34.119 to 34.126 | **15.4 MB** |
  | `L4_6471_1868a` | −118.297 to −118.288, 34.126 to 34.133 | **16.0 MB** |
- **Total:** ~63.6 MB for 4 tiles (much smaller because ~7 pts/m² vs B23's ~18.8 pts/m²).
- **URL pattern:**
  ```
  https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/USGS_LPC_CA_LosAngeles_2016_LAS_2018/laz/USGS_LPC_CA_LosAngeles_2016_<TILE_ID>_LAS_2018.laz
  ```

**Recommendation for Step A2:** use the `CA_LosAngeles_B23` 6-tile set (~890 MB) — it is ~3× denser than 2016 and reflects post-renovation (2019) course geometry. The 2016 set is useful only for differencing against the renovation.

---

## 3. NAIP aerial imagery

**Status: no NAIP tile downloads found via TNM Access for the Roosevelt bbox on 2026-04-20.**

Queries attempted against `https://tnmaccess.nationalmap.gov/api/v1/products`:
- `datasets=Imagery - NAIP (1 meter to .5 foot)` → 0 items
- `datasets=NAIP Plus` → 0 items
- `datasets=USDA National Agriculture Imagery Program (NAIP)` → 0 items
- `q=NAIP` → 0 items
- `q=orthoimagery` → only US Topo geoPDFs (Burbank 2022-01-19, Hollywood 2022-01-03), not true orthoimagery.

This is **not** because NAIP has no coverage of LA — NAIP flies California on its normal cycle. It is because TNM Access no longer surfaces NAIP as per-tile downloads (NAIP distribution moved primarily to the USDA NRCS Data Gateway and to hosted ImageServer services). The published USGS FAQ and Esri/ArcGIS Living Atlas confirm the 3-year flight cadence but do not provide per-tile URLs through TNM for this bbox.

**Working options for Step A2 imagery:**

1. **USGS NAIP ImageServer (live tile export, no download-per-tile):**
   - Service: https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer
   - Service copyright last updated 2025-01-09 per service metadata.
   - Pixel size ~0.3 m; 4-band (RGB+NIR). Web Mercator (EPSG:3857).
   - Export a Roosevelt-sized clip via `exportImage?bbox=<xmin>,<ymin>,<xmax>,<ymax>&bboxSR=4326&format=tiff&size=<w>,<h>&f=image`. A 2k × 2k GeoTIFF over the course bbox is ~15–25 MB.
   - Note this mosaic blends acquisition years; use the `Year` raster attribute to filter to the latest image if we need a single-vintage capture.

2. **USDA NRCS Geospatial Data Gateway (per-county ZIPs):**
   - Entry point: https://datagateway.nrcs.usda.gov/GDGHome_DirectDownLoad.aspx
   - County-level NAIP bundles for Los Angeles County are large (tens of GB). Not appropriate for Step A2 unless we script a per-DOQQ download.
   - NAIP quarter-quad (DOQQ) tiles are ~3.75' × 3.75'; the Griffith Park DOQQ is ~180–250 MB at 60 cm 4-band.

3. **Esri ArcGIS Living Atlas NAIP:**
   - https://naip-usdaonline.hub.arcgis.com/ — browsable and time-sliced (through 2023 confirmed, 2024 listed in Living Atlas blog).
   - Not a per-file download; use for visualization only.

4. **NAIP Image Dates Data Hub:**
   - https://naip-image-dates-usdaonline.hub.arcgis.com/ — use to determine the exact acquisition date of the NAIP frame covering Roosevelt before Step A2.

**Vintage expectation for LA, per USGS FAQ [B] and NAIP storymap [C]:** California is on the normal 3-year cycle with recent flights in 2020, 2022, 2024. 2024 is the most recent California-wide NAIP; 2025 would typically cover the non-California tranche. Treat "latest NAIP for Griffith Park = 2024" as the working assumption but verify via the NAIP Image Dates Hub in Step A2.

**Estimated size for a course-sized clip:** 15–60 MB as a ~2000×2000 GeoTIFF pulled from the ImageServer; ~180–250 MB if we pull the full DOQQ.

---

## 4. Satellite basemap alternatives

- **Mapbox Satellite / Satellite Streets:** tile service at `https://api.mapbox.com/styles/v1/mapbox/satellite-v9/tiles/{z}/{x}/{y}` (requires access token). Highest native LOD over LA is ~0.3 m from Maxar. Good for product rendering, not ground-truth measurement. [D]
- **Esri World Imagery:** `https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`. Free for non-commercial/attribution use. LA coverage is Maxar ~0.3 m. [E]
- **Google Maps Static / Satellite:** terms of service prohibit offline caching of tiles for downstream derivative products. Not recommended as a Goose data source.
- **Sentinel-2 (free, 10 m multispectral):** via AWS `sentinel-s2-l2a` bucket or Microsoft Planetary Computer. Too coarse for hole-level mapping (turf features are sub-meter) but useful for seasonal turf/NDVI checks.

For Goose's Step A2 we should rely on **USGS NAIP ImageServer** or the `CA_LosAngeles_B23` derived products for anything requiring absolute georeference; use Mapbox/Esri only for human-viewable basemaps.

---

## Appendix — footnotes and sources

- [A] NOAA InPort — *2025 USGS Lidar DEM: Los Angeles Post-Wildfire, CA.* https://www.fisheries.noaa.gov/inport/item/77762
- [B] USGS FAQ — *How often is orthoimagery in The National Map updated...* https://www.usgs.gov/faqs/how-often-orthoimagery-national-map-updated-and-what-are-acquisition-dates
- [C] NAIP Storymap — *National Agriculture Imagery Program (NAIP) 2002-2024.* https://storymaps.arcgis.com/stories/35c27c0e3f10406f91625c68e89cda0e
- [D] Mapbox Satellite style documentation. https://docs.mapbox.com/api/maps/styles/
- [E] Esri World Imagery service metadata. https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer

**TNM Access API queries used (for reproducibility):**
- `GET https://tnmaccess.nationalmap.gov/api/v1/products?datasets=Digital%20Elevation%20Model%20(DEM)%201%20meter&bbox=-118.305,34.12,-118.29,34.133&prodFormats=GeoTIFF`
- `GET https://tnmaccess.nationalmap.gov/api/v1/products?datasets=Lidar%20Point%20Cloud%20(LPC)&bbox=-118.305,34.12,-118.29,34.133&prodFormats=LAS,LAZ`
- `GET https://tnmaccess.nationalmap.gov/api/v1/products?datasets=Imagery%20-%20NAIP%20(1%20meter%20to%20.5%20foot)&bbox=-118.31,34.115,-118.285,34.14`

**Related USGS catalogs:**
- OpenTopography — CA_LosAngeles_1_B23 dataset page: https://portal.opentopography.org/usgsDataset?dsid=CA_LosAngeles_1_B23
- USGS — 2025 Post-Wildfire Lidar LA: https://www.usgs.gov/3d-elevation-program/science/2025-post-wildfire-lidar-data-los-angeles-ca
- USGS Science Data Catalog — 1m DEM collection: https://data.usgs.gov/datacatalog/data/USGS:77ae0551-c61e-4979-aedd-d797abdcde0e
- USGS Science Data Catalog — LPC collection: https://data.usgs.gov/datacatalog/data/USGS:b7e353d2-325f-4fc6-8d95-01254705638a

**Rough totals for Step A2 budgeting:**
- DEM (primary): ~690 MB (2 tiles × ~345 MB)
- LPC (primary): ~890 MB (6 tiles, 108–172 MB each)
- NAIP clip: 15–60 MB if pulled from ImageServer
- **Step A2 download budget: ≈ 1.6 GB for B23-only primary products, or ≈ 2.3 GB if we also pull 2016 LPC for differencing.**
