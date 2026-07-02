"""Fetch Woolworths NZ store locations from OpenStreetMap/Nominatim.

Process:
   1. Query Nominatim for Woolworths/Countdown supermarkets in New Zealand,
      stratified by region to maximise coverage.
   2. Respect Nominatim rate limits (1 req/sec) with a custom User-Agent.
   3. Filter out non-supermarket entries (pharmacy, e-store, distribution centre).
   4. Normalise city and region from the raw OSM display_name.
   5. De-duplicate and save the cleaned dataset to data/woolworths_stores.csv.

Why Nominatim:
  - Woolworths NZ does not expose a public store-listing API.
  - The Angular SPA store-finder loads locations dynamically, but no public JSON endpoint
    for all stores was found during reverse-engineering.
  - OpenStreetMap has ~180 Woolworths/Countdown-branded supermarkets mapped in NZ,
    with usable lat/lon coordinates.

Crawl etiquette:
  - All requests sleep 1.1 seconds between them (Nominatim terms recommend 1 req/sec).
  - Custom User-Agent identifies the project for transparency.

Usage:
    python scripts/woolworths/stores_fetch.py
"""

import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests
import unicodedata

sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "NZMealCostOptimizer/1.0 (research project)"}
RATE_LIMIT_SECONDS = 1.1

NZ_REGIONS = {
    "Auckland",
    "Waikato",
    "Bay of Plenty",
    "Gisborne",
    "Hawke's Bay",
    "Taranaki",
    "Manawatu-Whanganui",
    "Wellington",
    "Nelson",
    "Marlborough",
    "Tasman",
    "Canterbury",
    "Otago",
    "Southland",
}

EXCLUDE_KEYWORDS = ("pharmacy", "e-store", "distribution centre", "metro", "petrol", "fuel")


def _strip_diacritics(value: str) -> str:
    """Normalise a string by stripping diacritics for comparison."""
    nfkd = unicodedata.normalize("NFD", value)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _parse_region_city(display_name: str):
    """Parse region and a useful city/suburb tag from an OSM display_name.

    Typical display_name:
      Woolworths, 65, Greville Road, Pinehill, Upper Harbour, Auckland, 0632, New Zealand / Aotearoa

    After stripping the leading 'Woolworths' token, the remaining comma-separated parts
    roughly follow:
      house_number, road, suburb, local_board_city, region, postcode, country
    """
    addr_clean = re.sub(
        r"^(?:Woolworths(?: supermarket)?,?\s*)+", "", display_name, flags=re.I
    )
    parts = [p.strip() for p in addr_clean.split(",")]
    parts = [p for p in parts if p and p not in ("New Zealand", "Aotearoa", "New Zealand / Aotearoa")]
    norm_parts = [_strip_diacritics(p) for p in parts]

    region_norm = {_strip_diacritics(r) for r in NZ_REGIONS}
    region = ""
    region_idx = -1
    for i in range(len(parts) - 1, -1, -1):
        if norm_parts[i] in region_norm:
            region = parts[i]
            region_idx = i
            break

    city = parts[region_idx - 1] if region_idx > 0 else ""
    return city, region


def _query_nominatim(keyword: str):
    """Query Nominatim once for a keyword and return raw rows."""
    params = {
        "q": keyword,
        "format": "json",
        "limit": 50,
        "countrycodes": "nz",
        "bounded": "0",
        "addressdetails": "1",
        "dedupe": "1",
    }
    resp = requests.get(
        NOMINATIM_ENDPOINT,
        headers=HEADERS,
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_stores() -> pd.DataFrame:
    """Return a cleaned dataframe of Woolworths NZ supermarket locations.

    Strategy
    --------
    1. A short list of nationwide brand keywords is queried first to seed the
       deduplication set.
    2. The search is then expanded region by region using targeted keywords so
       that stores listed with only a local-area name are discovered.
    """
    brand_keywords = [
        "Woolworths New Zealand",
        "Countdown New Zealand",
        "Woolworths supermarket New Zealand",
        "Countdown supermarket New Zealand",
        "Woolworths supermarket NZ",
        "Countdown supermarket NZ",
        "Supermarket Woolworths New Zealand",
        "Supermarket Countdown New Zealand",
    ]

    regional_keywords = [
        "{region} Woolworths",
        "{region} Countdown",
        "Woolworths {region}",
        "Countdown {region}",
        "Woolworths {region} New Zealand",
        "Countdown {region} New Zealand",
    ]

    seen = set()
    rows = []

    def _process_results(results, keyword_label):
        new_count = 0
        for item in results:
            place_id = item.get("place_id")
            if place_id in seen:
                continue
            seen.add(place_id)

            raw_name = (item.get("name") or "").strip()
            if any(ex in raw_name.lower() for ex in EXCLUDE_KEYWORDS):
                continue

            lat = item.get("lat")
            lon = item.get("lon")
            display_name = item.get("display_name", "")
            city, region = _parse_region_city(display_name)

            rows.append(
                {
                    "osm_place_id": place_id,
                    "name": raw_name if raw_name else "Woolworths",
                    "address": display_name,
                    "city": city,
                    "region": region,
                    "latitude": float(lat) if lat is not None else None,
                    "longitude": float(lon) if lon is not None else None,
                }
            )
            new_count += 1
        print(f"    added {new_count} new (total unique so far: {len(rows)})")

    # Phase 1: nationwide brand queries
    print("Phase 1 — nationwide brand queries...")
    for kw in brand_keywords:
        print(f"  [{kw}]")
        try:
            results = _query_nominatim(kw)
            print(f"    returned {len(results)}")
        except Exception as exc:
            print(f"    skipped ({exc})")
            time.sleep(RATE_LIMIT_SECONDS)
            continue
        _process_results(results, kw)
        time.sleep(RATE_LIMIT_SECONDS)

    # Phase 2: per-region queries
    print("\nPhase 2 — per-region queries...")
    for region in sorted(NZ_REGIONS):
        print(f"  [{region}]")
        for pattern in regional_keywords:
            kw = pattern.format(region=region)
            print(f"    [{kw}]")
            try:
                results = _query_nominatim(kw)
                print(f"      returned {len(results)}")
            except Exception as exc:
                print(f"      skipped ({exc})")
                time.sleep(RATE_LIMIT_SECONDS)
                continue
            _process_results(results, kw)
            time.sleep(RATE_LIMIT_SECONDS)

    df = pd.DataFrame(rows)
    print(f"\nTotal unique stores found: {len(df)}")
    return df


def main():
    df = fetch_stores()
    if df.empty:
        raise SystemExit("No stores found.")

    out_path = DATA_DIR / "woolworths_stores.csv"
    df.to_csv(out_path, index=False)

    df_valid = df.dropna(subset=["latitude", "longitude"])
    print(f"Saved to: {out_path}")
    print(f"Total rows : {len(df)}")
    print(f"Geocoded  : {len(df_valid)}")
    print(f"Missing    : {len(df) - len(df_valid)}")
    print()

    before_dedup = len(df_valid)
    df_deduped = df_valid.drop_duplicates(subset=["latitude", "longitude"], keep="first")
    removed = before_dedup - len(df_deduped)
    if removed:
        df_deduped.to_csv(out_path, index=False)
        print(f"Removed {removed} duplicate(s) by (latitude, longitude)")
        print(f"Final rows : {len(df_deduped)}")
    else:
        print("No duplicate coordinates found.")
    print()
    print(df_deduped[["name", "city", "region", "latitude", "longitude"]].head(20).to_string(index=False))


if __name__ == "__main__":
    main()
