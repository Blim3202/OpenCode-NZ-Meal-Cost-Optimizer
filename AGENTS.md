# OpenCode — NZ Meal Cost Optimizer

Finds the cheapest Pak'nSave or Woolworths for a given dish by comparing ingredient prices across nearby stores (within 5 km of a NZ address).

## Setup

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.md
```

## Project Layout

```
opencode/
├── data/
│   ├── paknsave_stores.csv        # 60 stores: store_id (GUID), name, address, city, region, lat, lon
│   ├── paknsave_store_slugs.csv   # slug → store_id mapping (albany → 65defcf2-...)
│   ├── woolworths_stores.csv      # ~180 stores from Nominatim/OSM: osm_place_id, name, address, city, region, lat, lon
│   └── sample_search_results.json # example API response for product search
├── notebooks/
│   └── meal_cost_optimizer.ipynb  # 8-cell Jupyter prototype (run cell 6 with your inputs)
├── scripts/
│   ├── paknsave/
│   │   ├── fetch_stores.py        # one-shot: builds paknsave_stores.csv from __NEXT_DATA__ + Nominatim
│   │   └── prototype.py           # CLI: python scripts/paknsave/prototype.py "address" "dish"
│   └── woolworths/
│       ├── woolworths_api.py      # WoolworthsAPI class, auth, store list, product search
│       └── stores_fetch.py        # builds woolworths_stores.csv from Nominatim/OpenStreetMap
├── AGENTS.md                      # this file
├── Handover.md                    # Woolworths NZ reverse-engineering notes
├── design.md                      # technical design (API, auth, pipeline)
├── decision.md                    # key decisions and rationale
├── logs.md                        # major errors and resolutions
└── requirements.md                # pinned dependencies
```

## File Contents

| File | Purpose |
|---|---|
| `scripts/paknsave/prototype.py` | CLI entry point. Contains `PaknSaveAPI` class, `DISH_INGREDIENTS` map (21 dishes), geocoding, haversine, store search, price comparison. |
| `scripts/paknsave/fetch_stores.py` | Data builder. Scrapes `__NEXT_DATA__` for store GUIDs, store-finder HTML for names/addresses, geocodes via Nominatim. Run once or to refresh. |
| `scripts/woolworths/woolworths_api.py` | Woolworths API client (auth via Camoufox, store enumeration, product search). |
| `scripts/woolworths/stores_fetch.py` | Builds `data/woolworths_stores.csv` from Nominatim/OpenStreetMap with regional keyword expansion and (lat, lon) deduplication. |
| `notebooks/meal_cost_optimizer.ipynb` | Cells 1–4: setup. Cell 5: markdown. Cell 6: main run (edit `USER_ADDRESS`, `DISH_NAME`). Cell 7: itemised cheapest store table. |
| `data/woolworths_stores.csv` | ~180 rows (deduplicated by coordinates). Columns: `osm_place_id`, `name`, `address`, `city`, `region`, `latitude`, `longitude`. Sourced from OSM via Nominatim regional keyword crawl. |
| `requirements.md` | Pinned deps. Core: `cloudscraper`, `requests`, `pandas`, `numpy`, `beautifulsoup4`, `jupyterlab`. |

## Key Gotchas

- **Pak'nSave**: Guest API token expires after 30 min — auto-refreshed by the `PaknSaveAPI` class.
- **Woolworths**: No guest token. Requires real user account + browser login (Camoufox). Cookies reused for ~weeks. Akamai blocks plain browserless login.
- Nominatim geocoding rate limit: 1 req/sec.
- Prices from the Pak'nSave API are in **cents** — divide by 100 for dollars.
- Search returns first/most-relevant result per query, not cheapest (avoids pet food for "beef mince").
- `PaknSaveAPI.get_stores()` returns `{"stores": [...]}`, not a bare list.
- 21 dishes are hand-curated in `DISH_INGREDIENTS` — no NLP/LLM parsing yet.

## Git Rules

- **Always pause and ask for confirmation** before running `git push` or `git pull`. Never auto-execute these commands.

## Woolworths Research Status

- See `Handover.md` for current reverse-engineering status.
- Per-store pricing is the **primary blocker**. Do not integrate until experimentally confirmed.
- Store locations are sourced from OpenStreetMap/Nominatim (no public Woolworths store API).

## NZ Scope

All addresses, supermarkets, and data are New Zealand only. First target: Pak'nSave, expanding to Woolworths NZ.
