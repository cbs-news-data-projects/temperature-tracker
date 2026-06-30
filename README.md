# temperature-tracker

Data journalism project.

## Setup

```bash
uv sync                  # base packages
uv sync --extra viz      # add extras as needed (see below)
uv run jupyter lab
```

## Package extras

Base install: pandas, numpy, pyarrow, requests, python-dotenv, jupyterlab, nbconvert.
Pull in more with `uv sync --extra <name>` (combine with repeated `--extra` flags):

| Extra | Contents | For |
|---|---|---|
| `viz` | matplotlib, seaborn, plotly, altair, ipywidgets | exploratory charts |
| `geo` | geopandas, folium, censusdis | mapping, spatial joins, census |
| `data` | polars, duckdb | fast tables + SQL (pyarrow is in base) |
| `scraping` | beautifulsoup4, httpx, lxml, playwright | scraping (run `playwright install` after) |
| `io` | openpyxl, pyyaml | Excel + YAML |
| `datawrapper` | datawrapper | publish charts |

List them anytime: `uv run python -c "import tomllib;print(*tomllib.load(open('pyproject.toml','rb'))['project']['optional-dependencies'])"`

## Structure

- `data/raw/` — original source data, never modified
- `data/processed/` — cleaned, export-ready data
- `data/documentation/` — data dictionaries, source notes, methodology
- `notebooks/` — analysis (research only)
- `scripts/` — data fetch / acquisition
- `utils/`, `config.py` — shared helpers and paths

Copy `.env.example` to `.env` for API keys and settings.
