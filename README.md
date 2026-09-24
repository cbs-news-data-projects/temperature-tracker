# temperature-tracker — NDFD heat-forecast data pipeline

Fetches NOAA/National Weather Service **NDFD** forecasts three times a day,
reformats them into map-ready GeoJSON, and publishes them via GitHub Pages.

**This repo is the data engine — it produces data, not a map.** The public-facing
map lives in the graphics-rig (`cbs-news-data-projects/graphics-rig` →
`projects/2026/heat-tracker`, deployed at
`projects.cbsnews.com/projects/2026/heat-tracker/`) and fetches this repo's
published GeoJSON at runtime.

## Architecture

Three decoupled stages that talk only through files:

| Stage | Does | Code | Writes |
|---|---|---|---|
| **Fetch** | download NDFD GRIB2 (CONUS + AK + HI) | `scripts/fetch_ndfd.py` | `data/raw/*.bin` (not committed) |
| **Reformat** | decode → slim, map-ready GeoJSON | `scripts/build_heat.py` + `utils/heat.py` | `data/processed/*.geojson` (committed) |
| **Publish** | deploy the GeoJSON to Pages | `deploy` job in `heat-data.yml` | `cbs-news-data.github.io/temperature-tracker/data/…` |

Consumers only ever read the published URLs — presentation can change anywhere
without touching this pipeline.

## Data contract: relied on downstream for published live-tracking graphic

- **The six files always reformatted from raw data and published.** The graphics-rig map fetches
  these output files at runtime (`HeatMap.svelte`). **Do not rename, drop or stop publishing.**

  | File | Measure | Powers (in published map) |
  |---|---|---|
  | `heat_counties.geojson` | high temp | county choropleth + day thumbnails |
  | `heat_points.geojson` | high temp | "Places" dots + city search |
  | `feelslike_counties.geojson` | feels-like | county choropleth |
  | `feelslike_points.geojson` | feels-like | dots + search |
  | `warmnight_counties.geojson` | overnight low | county choropleth |
  | `warmnight_points.geojson` | overnight low | dots + search |

- **URLs:** `https://cbs-news-data.github.io/temperature-tracker/data/{heat,feelslike,warmnight}_{points,counties}.geojson`
- **Cadence:** refreshed 3× daily (9:23 / 15:23 / 0:23 UTC + deploy + CDN; GitHub
  cron runs 15–75 min late). Consumers should fetch with `cache: "no-cache"`.
- **Points features:** `properties = { name_state, day1..dayN }` — whole-°F ints
  or `null` (no data); N varies (typically 6–7). Coords, 4 decimals.
- **Counties features:** `properties = { GEOID, NAMELSAD, day1..dayN }` —
  `NAMELSAD` is the full legal name ("Cook County", "Orleans Parish",
  "Anchorage Municipality").
- **Metadata (both points and counties files):** `metadata.days[]` maps `dayN` to
  `seq`, `fcst_date` (the date the value describes), `valid_utc`; apt products add
  `n_hours` + `valid_start_utc` (thin-bucket flagging). `metadata.issued_utc` =
  when NWS generated the forecast.
- **Semantics to preserve:** label days off `fcst_date`, never the
  `dayN` index ("today" expires mid-day); warm-night `fcst_date` = the evening the
  night begins; feels-like is NWS apparent temperature (heat index categories apply
  to it, not raw temperature); hide `null`s.
- **CORS:** GitHub Pages serves `Access-Control-Allow-Origin: *`.

## Population exposure estimate (`feelslike_exposure.json`, `warmnight_exposure.json`) — not part of the contract above

`scripts/build_exposure.py --product feelslike|warmnight` (mirrors
`build_heat.py`'s `--product` flag) runs after the matching `build_heat.py`
product and joins its `<prefix>_counties.geojson` against a county
population reference (`data/reference/county_population.csv`, GEOID →
population; sourced from the Census Bureau's Population Estimates Program —
see the script's docstring for the current vintage/URL) to estimate how many
people live in counties forecast to cross a heat-danger threshold each day.

- **It's an estimate, not a headcount.** `feelslike` county values are the
  95th-percentile (hottest) grid cell; `warmnight` county values are the
  5th-percentile (coolest) grid cell — neither is an average, so a large,
  climate-diverse county can cross a threshold from one extreme corner while
  most residents don't. (For `warmnight` this cuts conservative, not lenient:
  a county only counts once even its coolest corner stays at/above the
  threshold.) Counting a county's *entire* population when it crosses is
  still a deliberate, directional simplification. Every field name ends
  `_est` (`extreme_caution_pop_est`, `danger_pop_est`, `warm_night_pop_est`)
  and anything user-facing must say "estimated."
- **Thresholds live in the data, not the front end.** Each file's
  `metadata.thresholds_f` carries the cutoff(s) used to build it. The
  graphics-rig embed reads the cutoff from there for reader-facing copy
  ("no overnight relief below 75°F tonight") — changing a threshold is a
  pipeline-only change, never hard-coded downstream.
- **`warm_night_pop_est` methodology.** Threshold: **75°F overnight apparent-
  temperature low**, fixed nationally — reviewed and signed off editorially
  (2026-09-24), not a default. Unlike the daytime figure, there's no NWS Heat
  Index category to inherit (that scale is defined on daytime apparent
  temperature; this repo's warm-night color bands were chosen for display,
  not risk), so this was researched independently:
  - NWS's own Excessive Heat Warning criteria repeatedly pair a daytime heat-
    index bar with an overnight-low condition, and 75°F recurs as that
    overnight component across offices in different climates — e.g. NWS
    Indianapolis (heat index ≥110°F **and** doesn't fall below 75°F for 48h,
    [weather.gov/ind/heatinfo](https://weather.gov/ind/heatinfo)), NWS
    Paducah (≥110°F for 2 days **and** lows ≥75°F,
    [weather.gov/pah](https://www.weather.gov/pah/hazardous_weather_heat)),
    and general Northeast-office criteria (≥105°F **and** lows don't drop
    below 75°F, per
    [ABC57's summary](https://abc57.com/news/excessive-heat-warning-criteria-082724)).
  - NWS/CDC **HeatRisk v2** folds overnight lows into its score but computes
    it relative to each location's own climatology and a locally-derived
    "minimum mortality temperature," not one fixed national number
    ([CDC/NWS collaboration](https://www.wpc.ncep.noaa.gov/heatrisk/cdc.html)).
  - The heat-mortality literature's dominant modern approach defines "hot
    nights" as a location-relative percentile (commonly the 95th percentile
    of that place's own historical daily minimum) specifically to capture
    acclimatization
    ([multicountry hot-nights study](https://www.sciencedirect.com/science/article/pii/S0160412025004702),
    [Nature Communications DLNM study](https://www.nature.com/articles/s41467-025-56067-7)).
  - **Known tradeoff, accepted for now:** a fixed 75°F cutoff overstates risk
    in the acclimated, air-conditioned arid Southwest — Phoenix/Tucson-area
    NWS criteria run closer to 80°F+
    ([AZDHS Heat Safety Resource Guide](https://www.azdhs.gov/documents/preparedness/epidemiology-disease-control/extreme-weather/heat/az-heat-safety-resource-guide.pdf)),
    so a flat 75°F would flag those counties on nearly every summer night —
    and understates it in northern cities where housing assumes cool nights.
    The literature-preferred fix is a per-county climatology-relative
    percentile, but that needs a new reference asset (e.g. NOAA Climate
    Normals) this repo doesn't have yet. Revisit if that becomes available.
- **Non-contractual.** Unlike the six files above, these can change shape or
  stop publishing without notice — they're derived convenience outputs, not
  relied on by the published map.
- **Fails soft.** No-ops (prints, exits 0) per product until
  `data/reference/county_population.csv` exists; a schema-only illustration
  (not real figures) lives at `data/reference/example_county_population.csv`.
- **URLs (when present):**
  `https://cbs-news-data.github.io/temperature-tracker/data/{feelslike,warmnight}_exposure.json`

## Products

| `--product` | element | what | prefix |
|---|---|---|---|
| `temp` | `maxt` | daytime **maximum temperature** (one grid/day, as NWS ships it) | `heat_*` |
| `feelslike` | `apt` | **daily-max apparent / "feels-like"** temp (hourly → per-cell daily max) | `feelslike_*` |
| `warmnight` | `apt` | **overnight-min** apparent temp (local 8pm–8am; using because sources advise it drives heat-wave mortality) | `warmnight_*` |

`apt` = NWS apparent temperature: heat index when hot, wind chill when cold,
plain air temp in between.

## Automation Summary

`.github/workflows/heat-data.yml` — three times daily; could be one or two after another month of testing:

- **`build-data` job** — fetch, build all three products (each place/county routed
  to its own sector grid: AK→alaska, HI→hawaii, else CONUS), estimate population
  exposure off the `feelslike` and `warmnight` outputs, rebase and commit
  `data/processed` + `data/reference`, stage GeoJSON (+ the exposure estimates,
  if present) for deploy.
- **`deploy` job** — publish the GeoJSON to GitHub Pages with an automatic retry
  (the Pages backend intermittently answers "Deployment failed, try again later";
  a failed attempt waits 3 minutes and retries). Delete this job and the
  fetch/commit pipeline is untouched.

## Command-line options

- `build_heat.py --product temp|feelslike|warmnight` · `--mode points|counties|both`
- `build_heat.py --csv` — also write analyst tables (tidy long + wide CSVs with
  full identifiers like `place_id`); on demand only, never committed.
- `build_heat.py --tz America/New_York` — apt products: the timezone whose
  calendar day/night defines each bucket (default `America/Chicago`).
- `build_heat.py --decimate N` — county zonal sampling stride (2 ≈ 5 km).
- `build_heat.py --county-pct P` — county value = tail percentile of its cells
  (default `0.95`; robust to a lone corrupt cell; `1.0` restores raw min/max).
- `make_reference.py --incorporated --min-sqmi 0.5` — thin the places universe.
- `fetch_ndfd.py --area conus,alaska,hawaii` — sectors (add `puertorico` if needed).
- `validate_live.py` — smoke-test the live GRIB decode (fill-value masking, hourly `apt`, date labels); run it after touching the decode path or upgrading pygrib/NDFD.
- `build_exposure.py --product feelslike|warmnight` — population exposure
  estimate (see above); no-ops without `data/reference/county_population.csv`.

## Editorial caveats (read before publishing anything from this data)

- **"Today" expires.** Once the window passes, NDFD drops it and `day1` becomes
  tomorrow. Always label from `fcst_date`.
- **Call it "apparent"/"feels-like," not "heat index"** below 80°F — heat index is
  only defined ≥80°F; the NWS Heat Index *categories* apply to feels-like only.
- **Warm-night date = the evening the night begins** (night of the 4th → labeled
  the 4th).
- **County values are near-extremes, not averages** — the 95th-percentile cell for
  temp/feelslike, 5th for warm nights (`--county-pct`); a tail percentile, not the
  single hottest/coolest cell, so one corrupt tiny-geography grid cell can't define a county. Not
  population-weighted — `feelslike_exposure.json` (see "Population exposure estimate" above)
  is the one exception, and even there it's a coarse, county-level *estimate*, not a
  headcount. Feels-like cells are also dropped when they exceed the same
  day's air-temp max by more than 25°F (a corrupt-cell guard; see `cap_apt_to_airtemp`).
- **Thin buckets** at the near/far ends rest on fewer hours (`n_hours` flags them).
- **One fixed timezone per build** (`--tz`), not per-cell solar time.
- **Whole °F only**; guard band −80…145°F kills unmasked GRIB fills at decode.
- **Nearest-cell sampling** for dots; coastal/mountain points can sit on a gradient.

## Original data sources

- NDFD GRIB2: `https://tgftp.nws.noaa.gov/SL.us008001/ST.opnl/DF.gr2/DC.ndfd/AR.{conus,alaska,hawaii}/VP.{001-003,004-007}/ds.{maxt,apt}.bin`
  (files are WMO-wrapped concatenated GRIB2 — they don't start with `GRIB`; pygrib reads them as-is)
- Reference geographies: Census 2024 Gazetteer places and 2023 cartographic-boundary
  counties (`make_reference.py`; NYC is split into its five boroughs, consolidated
  city-county names cleaned manually).
