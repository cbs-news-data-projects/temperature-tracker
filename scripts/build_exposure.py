#!/usr/bin/env python3
"""
build_exposure.py — post-process step: estimate population under dangerous heat.

Runs AFTER build_heat.py's "feelslike" product. Reads the
``feelslike_counties.geojson`` that step already wrote (day1..dayN NWS Heat
Index values per county, GEOID-keyed) and joins it against a static county
population reference to produce a day-by-day ESTIMATE of how many people live
in counties forecast to cross a Heat Index danger threshold.

This is deliberately a separate, decoupled script rather than a change to
build_heat.py:
  - build_heat.py's contract (GeoJSON schema, county percentile logic) is
    frozen and used by other consumers; this reads its *output*, so it can't
    break that contract.
  - It fails soft: if the population reference is missing, this step is
    skippable and every other product/output is unaffected.

ESTIMATE, not a headcount:
  - County day-values are the 95th-percentile grid cell in that county (see
    build_heat.py's accumulate_counties docstring), not an average — a large,
    climate-diverse county can cross a threshold from one hot corner while
    most residents don't. Flagging a county's *entire* population is a
    deliberate simplification for a rough, directional estimate, not a
    precise exposure model. Every output field name ends in "_est" and every
    consumer-facing label must say "estimated" for exactly this reason.
  - "Not population-weighted" was true of the base pipeline before this step;
    this step is what adds the (still rough) weighting on top, without
    touching the frozen GeoJSON contract.

Population reference (data/reference/county_population.csv):
  Two columns, GEOID (5-digit county FIPS, zero-padded, matching the GEOID
  property already in counties.geojson) and population (int). This is a
  static, ~yearly-refreshed reference file, the same pattern as
  counties.geojson and places.csv (see config.py) — NOT fetched at pipeline
  runtime.

  Source it from the Census Bureau Population Estimates Program (PEP) county
  totals. As of Vintage 2025 (released March 2026): download
  ``co-est2025-alldata.csv`` from
  ``www2.census.gov/programs-surveys/popest/datasets/2020-2025/counties/totals/``,
  build GEOID as zero-padded ``STATE`` + ``COUNTY``, and take ``population``
  from the ``POPESTIMATE2025`` column. Vintage/path/column all roll forward
  each year (2020-2025 -> 2020-2026, POPESTIMATE2025 -> POPESTIMATE2026, ...)
  — confirm the current filename on census.gov before downloading rather than
  trusting this comment. See README.md's "Population exposure estimate"
  section for the full write-up. A schema-only illustration lives at
  data/reference/example_county_population.csv (not real figures — don't use
  it as data).

Thresholds mirror HEAT_INDEX_BANDS in the graphics-rig embed's src/lib/heat.ts
(80 Caution / 90 Extreme Caution / 103 Danger / 125 Extreme Danger). Keep the
two in sync if those bands ever change; there is no shared source of truth
between the two repos.

Run: ``uv run python scripts/build_exposure.py`` (after
``build_heat.py --product feelslike``, needs the ``heat`` extra).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd  # noqa: E402

import config  # noqa: E402

# NWS Heat Index thresholds (°F) to report population estimates for.
# Keep in sync with HEAT_INDEX_BANDS in graphics-rig's src/lib/heat.ts.
THRESHOLDS_F = {
    "extreme_caution_pop_est": 90,
    "danger_pop_est": 103,
}


def load_population(path: Path) -> pd.Series:
    """GEOID (str, 5-digit) -> population (int)."""
    df = pd.read_csv(path, dtype={"GEOID": "string"})
    missing = {"GEOID", "population"} - set(df.columns)
    if missing:
        raise SystemExit(f"population reference missing columns: {missing}")
    df["GEOID"] = df["GEOID"].str.zfill(5)
    return df.set_index("GEOID")["population"]


def load_counties_geojson(path: Path) -> tuple[dict, list[dict], dict]:
    """-> (metadata, days, {GEOID: {dayKey: value_or_None}})."""
    gj = json.loads(path.read_text())
    meta = gj.get("metadata", {})
    days = meta.get("days", [])
    day_keys = [d["key"] for d in days]
    by_geoid: dict[str, dict] = {}
    for f in gj["features"]:
        props = f["properties"]
        geoid = str(props["GEOID"]).zfill(5)
        by_geoid[geoid] = {k: props.get(k) for k in day_keys}
    return meta, days, by_geoid


def estimate_exposure(days: list[dict], by_geoid: dict, population: pd.Series) -> tuple[list[dict], int]:
    """Per day, sum population of counties at/above each threshold.

    Counties present in the GeoJSON but missing from the population reference
    are skipped and counted, so coverage gaps are visible rather than silent.
    """
    missing_geoids: set[str] = set()
    results = []
    for d in days:
        key = d["key"]
        row = {"key": key, "fcst_date": d.get("fcst_date")}
        for field, threshold in THRESHOLDS_F.items():
            total = 0
            for geoid, vals in by_geoid.items():
                v = vals.get(key)
                if v is None or v < threshold:
                    continue
                pop = population.get(geoid)
                if pop is None:
                    missing_geoids.add(geoid)
                    continue
                total += int(pop)
            row[field] = total
        results.append(row)
    return results, len(missing_geoids)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--counties-geojson", default=None,
                     help="feelslike_counties.geojson to read "
                          "(default: <outdir>/feelslike_counties.geojson)")
    ap.add_argument("--population", default=str(config.REFERENCE_DIR / "county_population.csv"))
    ap.add_argument("--population-source-label", default="U.S. Census Bureau, "
                     "Population Estimates Program (see data/reference/county_population.csv)",
                     help="human-readable citation written into the output metadata")
    ap.add_argument("--outdir", default=str(config.PROCESSED_DATA_DIR))
    ap.add_argument("--outprefix", default="feelslike")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    counties_path = Path(args.counties_geojson) if args.counties_geojson \
        else outdir / f"{args.outprefix}_counties.geojson"
    population_path = Path(args.population)

    if not counties_path.exists():
        raise SystemExit(f"{counties_path} not found — run "
                          f"build_heat.py --product feelslike first")
    if not population_path.exists():
        print(f"skip: no population reference at {population_path} "
              f"(see README.md's \"Population exposure estimate\" section) — "
              f"exposure estimate not written")
        return 0

    meta, days, by_geoid = load_counties_geojson(counties_path)
    population = load_population(population_path)
    day_rows, n_missing = estimate_exposure(days, by_geoid, population)

    if n_missing:
        print(f"warning: {n_missing} counties in {counties_path.name} have no "
              f"population match — their residents are excluded from the estimate")

    out = {
        "metadata": {
            "element": "estimated population under NWS Heat Index thresholds",
            "population_source": args.population_source_label,
            "thresholds_f": THRESHOLDS_F,
            "counties_missing_population": n_missing,
            "days": days,
        },
        "days": day_rows,
    }
    if "issued_utc" in meta:
        out["metadata"]["issued_utc"] = meta["issued_utc"]

    out_path = outdir / f"{args.outprefix}_exposure.json"
    out_path.write_text(json.dumps(out))
    print(f"exposure: {len(day_rows)} day(s) -> {out_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
