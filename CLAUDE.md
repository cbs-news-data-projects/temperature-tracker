# Project guidance for Claude Code

Data journalism / analysis project created from `datascience-template`.

## Conventions

- **Environment:** managed by `uv`. Run code with `uv run …`; add a one-off
  package with `uv add …`, or pull a bundle with `uv sync --extra <name>`:
  - `viz` — matplotlib, seaborn, plotly, altair, ipywidgets (exploratory charts)
  - `geo` — geopandas, folium, censusdis (mapping, spatial joins, census)
  - `data` — polars, duckdb (fast tables + SQL; pyarrow is already in base)
  - `scraping` — beautifulsoup4, httpx, lxml, playwright (run `playwright install` after)
  - `io` — openpyxl, pyyaml (Excel + YAML)
  - `datawrapper` — datawrapper (publish charts)
  - Base (always installed): pandas, numpy, pyarrow, requests, python-dotenv,
    jupyterlab, nbconvert, ipykernel
- **Data flow:** `data/raw/` is immutable source data — load it, never overwrite it.
  Cleaned output goes to `data/processed/`. Data dictionaries and source/method
  notes go in `data/documentation/`.
- **Notebooks** in `notebooks/` are for research and exploration only. Anything
  published gets exported (CSV/JSON via `quick_export_for_web`, or to Datawrapper).
- **Scripts** in `scripts/` handle data fetch/acquisition (API, download, scrape).
- **Helpers:** `from utils import …` for analysis/journalism helpers; `import config`
  for paths and settings. Importing `utils` puts the project root on the path.
- **Secrets** live in `.env` (git-ignored), loaded by `config.py`. Never commit them.

## Editorial

Findings must trace to a verifiable source. Fact-check numbers with
`data_fact_check(df)` before publishing. See the global CBS News editorial
standards in `~/.claude/CLAUDE.md`.
