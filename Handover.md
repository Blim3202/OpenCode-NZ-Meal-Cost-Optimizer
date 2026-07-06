# Woolworths NZ - Reverse Engineering Handover

Status: Breakthrough in store identification. Store selection dropdown choices matched with location API data via common ID.

## Current Findings

- **Homepage & search page accessible via Playwright** (both headed and direct navigation modes return 200).
- **Search interaction works**: input `input[type="search"]` accepts text and navigates to `https://www.woolworths.co.nz/shop/searchproducts?search=<term>`.
- **412 products rendered** for `milk` query inside Angular shadow DOM components (`product-stamp-grid > div.product-entry`).
- **Prices visible** as plain text in the DOM — no authentication required to view search results.
- Pricing appears global within a detected location context (page shows: "You're seeing information for the Glenfield area"). Change-location flow is the next scoping experiment.
- **Direct async API call** `GET /api/v1/products?target=search&search=...` returns `400 Header is missing or is invalid.` — explored briefly and abandoned.

## Implemented

- **Playwright scraper built**: `scripts/woolworths/woolworths_scrape.py` combines the standalone headed navigation (previously in `explore_playwright.py`) with live DOM product extraction.
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
- Breakthrough: Joined Woolworths store dropdown choices and location data using a common ID. We will now implement store selection through HTML element interaction using this matched data.

## Next Steps
1. Filter the merged Woolworths stores (woolworths_stores.csv) within a 5km radius.
2. Automate store selection in ChangeStore.py by using the matched store ID to select the correct store in the dropdown.
3. Test woolworths_scrape.py with the new store location and verify price changes.
4. Verify that store selection persists and affects search results/scopes.
5. Integrate Playwright-based WoolworthsAPI into Woolworths_prototype.py once location scoping is validated.
