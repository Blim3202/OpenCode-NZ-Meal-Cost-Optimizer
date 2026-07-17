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
│   ├── paknsave_stores.csv            # 60 stores: store_id (GUID), name, address, city, region, lat, lon
│   ├── paknsave_store_slugs.csv       # slug → store_id mapping (albany → 65defcf2-...)
│   ├── woolworths_stores.csv          # Merged Woolworths store list with lat/lon
│   ├── woolworths_store_choices.csv   # Woolworths pickup location IDs (from pickup-addresses API)
│   ├── woolworths_store_choices.json  # Same data as CSV, JSON format
│   ├── woolworths_store_data.csv      # Woolworths store details from CDX API
│   ├── woolworths_store_data.json     # Store details with extra1 (fulfilmentStoreId), extra2 (pickupAddressId)
│   ├── store_id_mapping.json          # Playwright-captured fulfilmentStoreId/areaId for 3 stores
│   ├── part2_cookies.json             # Playwright-captured full cookie jars (Greymouth, Glenfield, baseline)
│   └── latest_results.csv             # Last optimizer output
├── notebooks/
│   ├── PaknSave_meal_cost_optimizer.ipynb   # 8-cell Jupyter prototype (run cell 6 with your inputs)
│   └── Woolworths_meal_cost_optimizer.ipynb # Woolworths Jupyter pipeline
├── scripts/
│   ├── paknsave/
│   │   ├── fetch_stores.py            # One-shot: builds paknsave_stores.csv from __NEXT_DATA__
│   │   └── PaknSave_prototype.py      # CLI: python scripts/paknsave/PaknSave_prototype.py "address" "dish"
│   └── woolworths/
│       ├── woolworths_api.py          # Cookie-based API module: session, store context, product search
│       ├── woolworths_optimizer.py    # API-based optimizer: geocode, stores, pricing, cost comparison
│       ├── woolworths_scrape.py       # Playwright headed scraper for search results (legacy)
│       ├── ChangeStore.py             # Playwright store selection via modal (reference)
│       ├── explore_woolworths_api_part1.py  # Phase 1: black-box API probing, dasFilter taxonomy
│       ├── explore_woolworths_api_part2.py  # Phase 2: URL-param seeding, Playwright cookie injection
│       ├── explore_woolworths_api_part3.py  # Phase 3: shell validation, cw-lrkswrdjp deep-dive
│       ├── explore_woolworths_api_part4.py  # Phase 4: programmatic cookie construction, price validation
│       ├── Get_woolworths_store_API_data.py # Fetches store details from CDX API
│       ├── Get_woolworths_store_choices.py  # Fetches pickup store list from API
│       ├── Merge_woolworths_stores.py       # Merges store choices and location data
│       └── facet_tree_tree.py               # DasFilter hierarchy exploration
├── AGENTS.md                           # This file
├── Woolworths_API.md                   # Full /api/v1 endpoint documentation (1290+ lines)
├── exploration_plan.md                 # Detailed per-store pricing findings and implementation checklist
├── compaction.md                       # Session-by-session progress record
├── Handover.md                         # Woolworths NZ reverse-engineering notes (legacy)
├── design.md                           # Technical design (API, auth, pipeline)
├── decision.md                         # Key decisions and rationale
├── logs.md                             # Major errors and resolutions
├── requirements.md                     # Pinned dependencies
└── README.md                           # Project readme
```

## File Contents

| File | Purpose |
|---|---|
| `scripts/paknsave/PaknSave_prototype.py` | CLI entry point. Contains `PaknSaveAPI` class, `DISH_INGREDIENTS` map (21 dishes), geocoding, haversine, store search, price comparison. |
| `scripts/paknsave/fetch_stores.py` | Data builder. Scrapes `__NEXT_DATA__` for store GUIDs, store-finder HTML for names/addresses, geocodes via Nominatim. Run once or to refresh. |
| `scripts/woolworths/woolworths_api.py` | Cookie-based Woolworths API module. `create_session()`, `set_store_context()`, `search_products()`, `find_cheapest()`, `get_nearby_stores()`, `geocode()`. Constructs `cw-lrkswrdjp` cookie from `extra1` in store data — no Playwright needed at runtime. |
| `scripts/woolworths/woolworths_optimizer.py` | API-based optimizer. Geocodes address, finds nearby stores, searches each ingredient at each store via API with per-store pricing, compares totals. 21 dishes supported. |
| `scripts/woolworths/woolworths_scrape.py` | Playwright headed scraper for search results (name, unit cost, actual price). Legacy — replaced by API-based approach. |
| `scripts/woolworths/ChangeStore.py` | Playwright store selection via modal URL. Reference implementation for browser-based store switching. |
| `scripts/woolworths/explore_woolworths_api_part{1-4}.py` | API exploration scripts. Phase 1: endpoint enumeration. Phase 2: cookie injection. Phase 3: cw-lrkswrdjp deep-dive. Phase 4: programmatic construction. |
| `scripts/woolworths/Get_woolworths_store_API_data.py` | Fetches Woolworths store location data from CDX API (`api.cdx.nz`). |
| `scripts/woolworths/Get_woolworths_store_choices.py` | Fetches Woolworths store dropdown choices from `pickup-addresses` API. |
| `scripts/woolworths/Merge_woolworths_stores.py` | Joins Woolworths choices and data via common ID. |
| `notebooks/PaknSave_meal_cost_optimizer.ipynb` | Pak'nSave prototype. |
| `notebooks/Woolworths_meal_cost_optimizer.ipynb` | Woolworths pipeline, utilizes `woolworths_optimizer.py`. |
| `data/woolworths_store_data.json` | Store details with `extra1` (=fulfilmentStoreId) and `extra2` (=pickupAddressId). Key data source for cookie construction. |
| `data/store_id_mapping.json` | Playwright-captured `fulfilmentStoreId`/`areaId` mapping for 3 stores (Greymouth, Glenfield, Birkenhead). |
| `requirements.md` | Pinned deps. Core: `cloudscraper`, `requests`, `pandas`, `numpy`, `beautifulsoup4`, `playwright`, `jupyterlab`. |

## Key Gotchas

### Pak'nSave
- Guest API token expires after 30 min — auto-refreshed by the `PaknSaveAPI` class.
- Prices from the Pak'nSave API are in **cents** — divide by 100 for dollars.
- `PaknSaveAPI.get_stores()` returns `{"stores": [...]}`, not a bare list.
- Nominatim geocoding rate limit: 1 req/sec.

### Woolworths
- **Per-store pricing via cookie injection**: The `cw-lrkswrdjp` cookie controls store context. Construct it as `dm-Pickup,f-{fulfilmentStoreId},s-38` where `fulfilmentStoreId` = `extra1` from `woolworths_store_data.json`. See `Woolworths_API.md` section 8 for full details.
- **Fresh session required per store**: Reusing a `requests.Session` causes the server's `Set-Cookie` to overwrite the injected `cw-lrkswrdjp`. Create a new session (with `GET /`) for each store.
- **`fulfilmentStoreId` != `pickupAddressId`**: These are different numbers. Use `extra1` from `woolworths_store_data.json` for the cookie.
- **`areaId` is optional**: The cookie works with just `dm-Pickup,f-{fulfilmentStoreId}`. The `a-` and `s-` fields are not required.
- **`s-38` is constant**: Confirmed across all tested stores. Safe to hardcode.
- **x-requested-with header mandatory**: Omitting it returns HTTP 400. The literal string `"??"` works.
- **Session seeding**: A single `GET /` with browser-like headers establishes cookies. No login needed for public endpoints.
- **Playwright headless=False required**: If you do use Playwright, the site blocks headless Chromium.
- Search returns first/most-relevant result per query, not cheapest (avoids pet food for "beef mince").
- 21 dishes are hand-curated in `DISH_INGREDIENTS` — no NLP/LLM parsing yet.

## Woolworths Research Status

- **Per-store pricing CONFIRMED**: The `cw-lrkswrdjp` cookie controls store context. Different stores return different prices (e.g., Greymouth Milk 3L = $7.15, Glenfield = $7.33). 21/21 products show price differences between stores.
- **Playwright NOT needed at runtime**: The `cw-lrkswrdjp` cookie can be constructed from `extra1` in `woolworths_store_data.json` (verified 3/3 stores). No browser automation needed for product search or store switching.
- **`woolworths_api.py` module built and tested**: End-to-end pipeline working — geocode address, find nearby stores, inject per-store cookies, search products, compare costs. See `scripts/woolworths/woolworths_api.py`.
- **Fresh session per store required**: The server's `Set-Cookie` response overwrites injected cookies on reused sessions. Each store needs a fresh `requests.Session`.
- **All 67 cookies unnecessary**: Only `cw-lrkswrdjp` carries store context. The other 66 cookies (session_state, RT, Akamai, analytics, ads) are not needed for API calls.
- **`areaId` not in any data source**: The `a-field` in the cookie is optional and would require Playwright to capture per-store. Not needed for per-store pricing.
- **Full API documentation**: `Woolworths_API.md` (1290+ lines) covers all endpoints, cookie architecture, and production usage.

## NZ Scope

All addresses, supermarkets, and data are New Zealand only. First target: Pak'nSave, expanding to Woolworths NZ.

## Git Rules

- **Always pause and ask for confirmation** before running `git push` or `git pull`. Never auto-execute these commands.

## File permission rules

- **Never access an external directory unless invoking skills**. All files runs must be in the project directory.
