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
│   └── # woolworths_stores.csv removed - will be regenerated via HTML element selection
├── notebooks/
│   └── meal_cost_optimizer.ipynb  # 8-cell Jupyter prototype (run cell 6 with your inputs)
├── scripts/
│   ├── paknsave/
│   │   ├── fetch_stores.py        # one-shot: builds paknsave_stores.csv from __NEXT_DATA__ + Nominatim
│   │   └── prototype.py           # CLI: python scripts/paknsave/prototype.py "address" "dish"
│   └── woolworths/
│       ├── woolworths_scrape.py   # Playwright headed scraper for search results (name, unit cost, actual price table)
│       └── # stores_fetch.py removed - will be replaced by HTML element selection script
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
| `scripts/woolworths/woolworths_scrape.py` | Playwright headed scraper for search results (name, unit cost, actual price table). |
| `scripts/woolworths/stores_fetch.py` | Removed - will be replaced by HTML element selection script for automated store discovery |
| `notebooks/meal_cost_optimizer.ipynb` | Cells 1–4: setup. Cell 5: markdown. Cell 6: main run (edit `USER_ADDRESS`, `DISH_NAME`). Cell 7: itemised cheapest store table. |
| `data/woolworths_stores.csv` | Removed - will be regenerated via HTML element selection when automation is implemented |
| `requirements.md` | Pinned deps. Core: `cloudscraper`, `requests`, `pandas`, `numpy`, `beautifulsoup4`, `jupyterlab`. |

## Key Gotchas

- **Pak'nSave**: Guest API token expires after 30 min — auto-refreshed by the `PaknSaveAPI` class.
- **Woolworths**: No guest token. Requires real user account + browser login (Camoufox). Cookies reused for ~weeks. Akamai blocks plain browserless login. Public search page accessible via Playwright headed mode with `--disable-blink-features=AutomationControlled`; direct `GET /api/v1/products?target=search` returns 400.
- Nominatim geocoding rate limit: 1 req/sec.
- Prices from the Pak'nSave API are in **cents** — divide by 100 for dollars.
- Search returns first/most-relevant result per query, not cheapest (avoids pet food for "beef mince").
- `PaknSaveAPI.get_stores()` returns `{"stores": [...]}`, not a bare list.
- 21 dishes are hand-curated in `DISH_INGREDIENTS` — no NLP/LLM parsing yet.

## Git Rules

- **Always pause and ask for confirmation** before running `git push` or `git pull`. Never auto-execute these commands.

## File permission rules

- Never access an external directory unless invoking skills. All files runs must be in the project directory.

## Woolworths Research Status

- Per-store pricing is the **primary blocker**. Direct `GET /api/v1/products?target=search` returns 400 with `Header is missing or is invalid.`.
- Current path: **Playwright headed scraping** of `/shop/searchproducts?search=...`. Prices visible in DOM (Angular shadow DOM). Search is scoped to a default location; change-location flow must be reverse-engineered for per-store pricing.
- Store locations are sourced from **manual HTML inspection** (no public Woolworths store API exists); automation will be implemented via HTML element selection.
- Working tool: `scripts/woolworths/woolworths_scrape.py` (produces a formatted table of product name, unit cost, and actual price). `scripts/woolworths/explore_playwright.py` is throwaway/experimental.

## NZ Scope

All addresses, supermarkets, and data are New Zealand only. First target: Pak'nSave, expanding to Woolworths NZ.
