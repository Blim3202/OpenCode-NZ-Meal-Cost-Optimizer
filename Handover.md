# Woolworths NZ - Reverse Engineering Handover

Status: Experimenting with Playwright (headed Chromium) to scrape search results page. Direct API pathway abandoned.

## Current Findings

- **Homepage & search page accessible via Playwright** (both headed and direct navigation modes return 200).
- **Search interaction works**: input `input[type="search"]` accepts text and navigates to `https://www.woolworths.co.nz/shop/searchproducts?search=<term>`.
- **412 products rendered** for `milk` query inside Angular shadow DOM components (`product-stamp-grid > div.product-entry`).
- **Prices visible** as plain text in the DOM — no authentication required to view search results.
- Pricing appears global within a detected location context (page shows: "You're seeing information for the Glenfield area"). Change-location flow is the next scoping experiment.
- **Direct async API call** `GET /api/v1/products?target=search&search=...` returns `400 Header is missing or is invalid.` — explored briefly and abandoned.

## Authentication

- **No guest token for search**. Public search results page does not require login.
- **XSRF-TOKEN** cookie exists after homepage load and is used on some protected endpoints (e.g., `/api/v1/trolleys/my`), but search page is unauthenticated.
- Akamai guardrails present; headed Chromium with `--disable-blink-features=AutomationControlled` is required. Headless mode is unstable for Playwright on this site.

## Store Data

- **Source**: OpenStreetMap/Nominatim via `scripts/woolworths/stores_fetch.py`
- **Schema**: `osm_place_id`, `name`, `address`, `city`, `region`, `latitude`, `longitude`
- **Coverage**: targeting ~180 NZ stores; deduplicated on `(latitude, longitude)`
- **Crawl etiquette**: 1 req/sec + `User-Agent: NZMealCostOptimizer/1.0 (research project)`
- No public store enumeration API found; internal Woolworths numeric IDs visible in UI bundles but not yet mapped.

## Architecture Decision

The experimental path is **Playwright-headed scraping** rather than the previously doctored direct REST pathway. Rationale:
- Search endpoint `target=search` is blocked/header-gated without a verified session context.
- Search results are rendered client-side from Angular components, which Playwright can read via shadow DOM.
- Per-store scoping can be tested by interacting with the website’s change-location flow before each search.

## Next Steps

1. Reverse-engineer the **change-location flow** to scope results to a specific store or delivery area.
2. Confirm whether search scope persists/cookies persist across runs without re-login.
3. Extract price and product metadata robustly from `product-stamp-grid` shadow DOM.
4. Integrate Playwright-based `WoolworthsAPI` into `prototype.py` once location scoping is validated.
