"""
Sample data-fetch script.

Run locally with `uv run python scripts/fetch.py`, or on a schedule via
.github/workflows/fetch.yml. Writes raw, untouched source data to data/raw/ —
cleaning and transformation belong in notebooks, not here.

Replace the body with your real source (API, file download, scrape).
"""

import os

import requests

from config import RAW_DATA_DIR

# Pull secrets from the environment (.env locally, GitHub Actions secrets in CI).
API_KEY = os.getenv("DATA_API_KEY")


def fetch() -> None:
    url = "https://example.com/data.csv"
    params = {"api_key": API_KEY} if API_KEY else {}

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()

    out_path = RAW_DATA_DIR / "source.csv"
    out_path.write_bytes(resp.content)
    print(f"✅ Wrote {out_path} ({len(resp.content):,} bytes)")


if __name__ == "__main__":
    fetch()
