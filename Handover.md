# Woolworths NZ - Reverse Engineering Handover

Status: Breakthrough in store identification and automated selection. Store selection dropdown choices matched with location API data via common ID, and direct URL-based modal interaction implemented.

## Current Findings

- **Homepage & search page accessible via Playwright** (both headed and direct navigation modes return 200).
- **Store selection automated**: Direct navigation to `https://www.woolworths.co.nz/bookatimeslot/(hww-modal:change-pick-up-store)` allows reliable store selection via the modal.
- **Search interaction works**: input `input[type="search"]` accepts text and navigates to `https://www.woolworths.co.nz/shop/searchproducts?search=<term>`.
- **412 products rendered** for `milk` query inside Angular shadow DOM components (`product-stamp-grid > div.product-entry`).
- **Prices visible** as plain text in the DOM — no authentication required to view search results.
- Pricing updates based on the selected store. Needs to be fullt tested
- **Direct async API call** `GET /api/v1/products?target=search&search=...` returns `400 Header is missing or is invalid.` — explored briefly and abandoned.

## Implemented

- **Playwright scraper built**: `scripts/woolworths/woolworths_scrape.py` combines the standalone headed navigation with live DOM product extraction.
- **Store selection automated**: `scripts/woolworths/ChangeStore.py` uses direct modal navigation to reliably set the store context.
- **Product extraction pattern confirmed** from rendered search HTML:
  - Name: `h3[id$="-title"]`
  - Unit cost: `[id$="-unitPrice"] .cupPrice` (e.g. `$3.02 / 1L`)
  - Actual price: `[id$="-price"]` `aria-label` or inner text (e.g. `$6.04 each.`)
- Script saves full rendered HTML to `.Temp/woolworths_search_full.html` for offline inspection and prints a formatted table of up to 20 results.

## Authentication

- **No guest token for search**. Public search results page does not require login.
- **XSRF-TOKEN** cookie exists after homepage load and is used on some protected endpoints (e.g., `/api/v1/trolleys/my`), but search page is unauthenticated.
- Akamai guardrails present; headed Chromium with `--disable-blink-features=AutomationControlled` is required. Headless mode is unstable for Playwright on this site.

## Store Data

- **Source**: Discovered Woolworths site-location API (`https://api.cdx.nz/site-location/api/v1/sites`)
- **Schema**: JSON based on API response
- **Coverage**: All NZ Woolworths stores via API
- **Collection**: Automated collection via API request in `scripts/woolworths/Extract_woolworths_API_JSON.py`

## Architecture Decision

The experimental path is **Playwright-headed scraping** rather than the previously doctored direct REST pathway. Rationale:
- Search endpoint `target=search` is blocked/header-gated without a verified session context
- Search results are rendered client-side from Angular components, which Playwright can read via shadow DOM
- Breakthrough: Joined Woolworths store dropdown choices and location data using a common ID and implemented direct URL modal interaction for store selection.

## Jupyter Integration

- **Integrated Pipeline**: The pipeline is fully integrated into `notebooks/Woolworths_meal_cost_optimizer.ipynb`.
- **Standalone Scraping**: To circumvent Windows `NotImplementedError` regarding `asyncio` subprocesses in Jupyter, the scraper runs as an independent process via `subprocess.Popen`.
- **Results Handling**: Data is saved to `data/latest_results.csv` by the scraper, which is subsequently ingested by the notebook's `analyze_results` function for formatted calculation and display.

## Next Steps
1. Filter the merged Woolworths stores (woolworths_stores.csv) within a 5km radius.
2. Integrate Playwright-based Woolworths store selection and scraping into the new `notebooks/Woolworths_meal_cost_optimizer.ipynb`.
3. Verify that store selection persists and affects search results/scopes within the notebook.
4. Integrate Playwright-based WoolworthsAPI into woolworths optimiszer notebook once processes validated.
