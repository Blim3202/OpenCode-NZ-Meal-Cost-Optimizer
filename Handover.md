# Woolworths NZ - Reverse Engineering Handover

Status: Experimenting with Playwright (headed Chromium) to scrape search results page. Direct API pathway abandoned.

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

- **Source**: Manual HTML inspection of Woolworths website (no public store enumeration API exists)
- **Schema**: To be determined based on HTML element selection for store discovery
- **Coverage**: All NZ Woolworths stores identified through manual inspection
- **Collection etiquette**: Manual inspection completed; automated collection will be implemented via HTML element selection with appropriate rate limiting
- - No public store enumeration API found; internal Woolworths numeric IDs visible in UI bundles but not yet mapped

## Architecture Decision

The experimental path is **Playwright-headed scraping** rather than the previously doctored direct REST pathway. Rationale:
- Search endpoint `target=search` is blocked/header-gated without a verified session context
- Search results are rendered client-side from Angular components, which Playwright can read via shadow DOM
- Per-store scoping approach changed: Instead of reversing the change-location flow, we have identified the store selection dropdown through manual inspection and will implement store selection directly through HTML element interaction

## Next Steps

1. Implement store selection functionality by interacting with the identified store selection dropdown on the Woolworths website
2. Verify that store selection persists and affects search results/scopes
3. Confirm whether search scope/cookies persist across runs without re-login
4. Integrate Playwright-based WoolworthsAPI into prototype.py once location scoping is validated
5. Replace/upstream the temporary woolworths_scrape.py extractor once the data shape is stable
