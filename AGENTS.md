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
│   ├── woolworths_stores.csv      # Merged Woolworths store list (choices + locations)
│   ├── woolworths_store_choices.csv / .json  # Woolworths pickup location IDs
│   ├── woolworths_store_data.csv / .json     # Woolworths lat/lon via cdx.nz API
│   └── latest_results.csv         # Last Woolworths scraper output
├── notebooks/
│   ├── PaknSave_meal_cost_optimizer.ipynb  # 8-cell Jupyter prototype (run cell 6 with your inputs)
│   └── Woolworths_meal_cost_optimizer.ipynb # Woolworths Jupyter pipeline
├── scripts/
│   ├── paknsave/
│   │   ├── fetch_stores.py        # one-shot: builds paknsave_stores.csv from __NEXT_DATA__
│   │   └── PaknSave_prototype.py  # CLI: python scripts/paknsave/PaknSave_prototype.py "address" "dish"
│   └── woolworths/
│       ├── woolworths_scrape.py   # Playwright headed scraper for search results
│       ├── woolworths_optimizer.py # Main async optimizer (called from notebook via subprocess)
│       ├── Get_woolworths_store_API_data.py # Fetches Woolworths store location data from cdx.nz API
│       ├── Get_woolworths_store_choices.py # Fetches Woolworths store dropdown choices
│       ├── Merge_woolworths_stores.py      # Joins choices and data via common ID
│       ├── ChangeStore.py         # Work-in-progress: Playwright store selection
│       └── explore_woolworths_api.py # Black-box exploration of /api/v1 endpoints
├── AGENTS.md                      # this file
├── Woolworths_API.md              # /api/v1 endpoint documentation (all tested endpoints)
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
| `scripts/woolworths/woolworths_scrape.py` | Playwright headed scraper for search results (name, unit cost, actual price table). |
| `scripts/woolworths/woolworths_optimizer.py` | Main async optimizer. Imports from here into the notebook. |
| `scripts/woolworths/Get_woolworths_API_data.py` | Fetches Woolworths store location data from API. |
| `scripts/woolworths/Get_woolworths_store_choices.py` | Fetches Woolworths store dropdown choices from booking page. |
| `scripts/woolworths/Merge_woolworths_stores.py` | Joins Woolworths choices and data via common ID. |
| `scripts/woolworths/extract_all_stores.py` | Extracts all Woolworths stores from HTML elements. |
| `scripts/woolworths/changestore.py` | Work-in-progress: handles store selection dropdown (incomplete). |
| `notebooks/PaknSave_meal_cost_optimizer.ipynb` | Pak'nSave prototype. |
| `notebooks/Woolworths_meal_cost_optimizer.ipynb` | Woolworths pipeline, utilizes `woolworths_optimizer.py`. |
| `data/woolworths_all_stores.csv` | All Woolworths stores extracted from HTML elements. |
| `data/woolworths_stores.csv` | Regenerated via HTML element selection for 5km filtering. |
| `requirements.md` | Pinned deps. Core: `cloudscraper`, `requests`, `pandas`, `numpy`, `beautifulsoup4`, `jupyterlab`. |

## Key Gotchas

- **Pak'nSave**: Guest API token expires after 30 min — auto-refreshed by the `PaknSaveAPI` class.
- **Woolworths**: No guest token. Requires real user account + browser login (Camoufox). Cookies reused for ~weeks. Akamai blocks plain browserless login. Public search page accessible via Playwright headed mode with `--disable-blink-features=AutomationControlled`. JSON API (`/api/v1/products?target=search`) also works with `x-requested-with: ??` header — no login needed. Store-context switching still requires Playwright browser cookies.
- Nominatim geocoding rate limit: 1 req/sec.
- Prices from the Pak'nSave API are in **cents** — divide by 100 for dollars.
- Search returns first/most-relevant result per query, not cheapest (avoids pet food for "beef mince").
- `PaknSaveAPI.get_stores()` returns `{"stores": [...]}`, not a bare list.
- 21 dishes are hand-curated in `DISH_INGREDIENTS` — no NLP/LLM parsing yet.

## Woolworths Research Status

- **API exploration complete** (`Woolworths_API.md`): Confirmed that `GET /api/v1/products?target=search` works with unauthenticated session cookies (no Playwright needed for product search). Requires `x-requested-with: ??` header and a single `GET /` to seed cookies. Full endpoint documentation in `Woolworths_API.md`.
- **Pricing is global**: `fulfilmentStoreId` and `pickupStoreId` query parameters are accepted but do not change prices — Woolworths uses a single price list across all stores. This means the optimizer only needs one price search per ingredient, not one per store.
- **Store context still requires Playwright**: No POST endpoint exists for programmatic store switching. Browser cookies set via the Woolworths web UI are the only way to change fulfilment context.
- Pipeline integration complete: Automated store selection, scraping, and price analysis integrated into `notebooks/Woolworths_meal_cost_optimizer.ipynb`.
- Focus is now on verifying pipeline robustness, cookie persistence across store changes, and refining price scraping accuracy.

## NZ Scope

All addresses, supermarkets, and data are New Zealand only. First target: Pak'nSave, expanding to Woolworths NZ.

## Git Rules

- **Always pause and ask for confirmation** before running `git push` or `git pull`. Never auto-execute these commands.

## File permission rules

- **Never access an external directory unless invoking skills**. All files runs must be in the project directory.