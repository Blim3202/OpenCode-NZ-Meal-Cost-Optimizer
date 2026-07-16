# Major Errors & Resolutions

## 1. Loose Garlic pricing ($40+/kg)

**Symptom**: Searching "garlic" returns "Loose Garlic" priced at $39.99/kg, making a single bulb appear extremely expensive.

**Cause**: The API returns per-kg pricing for loose items. The first result is loose garlic, not pre-packaged crushed garlic.

**Resolution**: Accept that some items have misleading per-kg pricing. The crushed garlic jar ($2.29) is a more practical result and sometimes appears instead. This is a known limitation.

## 2. PAKnSAVE store slug matching failures

**Symptom**: Some stores didn't match between the store-finder page slugs and the `__NEXT_DATA__` GUIDs.

**Cause**: Slug generation from store names doesn't always match the URL slugs on the website (e.g., apostrophes, "MINI" prefix, "-city" suffix).

**Resolution**: Hardcoded fallback mappings in `fetch_stores.py` for known mismatches (e.g., Henderson → "alderman-drive-henderson"). Not fully automated — manual verification needed for new stores.

## 3. Nominatim geocoding returning None

**Symptom**: `geocode()` returns `(None, None)` for some addresses.

**Cause**: Nominatim doesn't recognize the address format, or the address is too vague.

**Resolution**: The `fetch_stores.py` script has a fallback that tries `"Pak'nSave {name}, New Zealand"` as an alternative query. For user addresses, they need to provide a recognizable NZ address.

## 4. Woolworths `/api/v1/sites` and sibling endpoints return 404

**Symptom**: Attempted to enumerate Woolworths NZ stores via `/api/v1/sites`, `/api/v1/stores`, and `/api/store-finder`. All returned 404 or empty responses.

**Cause**: The Angular SPA store-finder is JavaScript-rendered; no public JSON API exists for a full store list.

**Resolution**: Abandoned public API enumeration. Switched to OpenStreetMap/Nominatim as store location source. Succeeded by Log 10 (Woolworths API Discovery).

## 5. Initial Woolworths keyword search insufficient

**Symptom**: Initial nationwide-only keyword queries (`Woolworths New Zealand`, `Countdown New Zealand`, etc.) returned ~50 stores, well below the expected ~180 NZ stores.

**Cause**: Many OSM entries are only tagged with local-area names and don't surface under broad national keywords.

**Resolution**: We are no longer using Nominatim for Woolworths store locations. Instead, we have extracted all (pickup location) stores through inspecting the HTML elements. This approach provides complete coverage of all NZ Woolworths stores. Succeeded by Log 10 (Woolworths API Discovery).

## 6. Woolworths store-finder URL pattern not yet integrated

**Symptom**: Internal numeric store IDs are visible in the Angular SPA store-finder URL pattern (`/store-finder/{id}/{city}/{slug}`), but there is no public API to map these to coordinates or names.

**Cause**: Internal IDs are client-side routing only; no JSON endpoint exposes the mapping.

**Resolution**: We are no longer using Nominatim for Woolworths store locations. Instead, we have extracted all (pickup location) stores through inspecting the HTML elements. This approach provides complete coverage of all NZ Woolworths stores. Succeeded by Log 10 (Woolworths API Discovery).

## 7. Woolworths direct product search API unusable (`400 Header is missing or is invalid.`)

**Symptom**: Calling `GET /api/v1/products?target=search&search=milk&inStockProductsOnly=false&size=24` from both outside the browser and via Playwright's `page.request` returns HTTP 400 with `{"message":"One or more errors occurred","errors":[{"field":"Header","message":"Header is missing or is invalid."}]}`.

**Cause**: The endpoint requires a non-empty `x-requested-with` header (any string, including `??` or `XMLHttpRequest`). The original testing omitted this header entirely, causing the 400. A single `GET /` to seed cookies is also sufficient — no Playwright session or authenticated state is needed.

**Resolution**: The API is fully functional with `requests.Session` when the `x-requested-with: ??` header is included. Full endpoint documentation in `Woolworths_API.md`. The Playwright scraping layer remains useful only for store-context switching (which requires browser cookies), not for product search.

## 8. Headless Playwright blocked on Woolworths (`ERR_HTTP2_PROTOCOL_ERROR`)

**Symptom**: Running `page.goto("https://www.woolworths.co.nz/")` with `headless=True` and `--disable-blink-features=AutomationControlled` raised `net::ERR_HTTP2_PROTOCOL_ERROR`.

**Cause**: Site/Akamai blocks headless/automation fingerprints despite standard disguise arguments.

**Resolution**: Use headed mode with `headless=False` and standard user-agent/locale/timezone settings. Search and DOM extraction work reliably in this configuration.

## 9. Successful Woolworths Store Identification via Manual HTML Inspection

**Symptom**: Needed to obtain comprehensive Woolworths store locations for NZ to enable per-store pricing queries.

**Cause**: Previous Nominatim/OSM approach via stores_fetch.py was incomplete and required automation that wasn't yet implemented. Manual inspection approach was needed to identify all store locations.

**Resolution**: Successfully inspected Woolworths website HTML to identify all store locations. Determined that stores_fetch.py and woolworths_stores.csv can be deleted pending implementation of proper HTML element selection for automation. Successfully navigated to the store selection dropdown on the Woolworths website, ready to implement store selection functionality. Succeeded by Log 10 (Woolworths API Discovery).

## 10. Successful Woolworths Store Identification via API

**Symptom**: Needed a reliable, automated way to obtain comprehensive Woolworths store locations for NZ to enable per-store pricing queries.

**Cause**: Previous Nominatim/OSM approach was incomplete, and manual HTML inspection was unsustainable.

**Resolution**: Discovered the public Woolworths site-location API (`https://api.cdx.nz/site-location/api/v1/sites`). Implemented `scripts/woolworths/Extract_woolworths_API_JSON.py` to fetch, parse, and save this data to `data/woolworths_stores_API.json` and `data/woolworths_stores.csv`.

## 11. Breakthrough in Woolworths Store Identification and Data Joining

**Symptom**: Previous name-matching approach was unreliable for selecting stores within the dropdown.

**Cause**: Store names in dropdown choices didn't consistently match location API names.

**Resolution**: Successfully discovered that both datasets contain a common ID. Created `Get_woolworths_API_data.py`, `Get_woolworths_store_choices.py`, and `Merge_woolworths_stores.py` to fetch both sets and merge them into `data/woolworths_stores.csv`. This enables reliable store selection by ID.

## 12. Successful Automated Store Selection via URL

**Symptom**: Need reliable automated store selection to ensure pricing data reflects the correct user location.

**Cause**: Previous approaches (complex dropdown interactions) were fragile.

**Resolution**: Implemented `scripts/woolworths/ChangeStore.py` using direct navigation to the Woolworths store selection modal URL (`/bookatimeslot/(hww-modal:change-pick-up-store)`), which reliably allows programmatically setting the store context.

## 13. Jupyter `NotImplementedError` on Windows
**Symptom**: Playwright `async_playwright` failed in Jupyter notebook on Windows with `NotImplementedError` regarding subprocesses.
**Resolution**: Refactored the pipeline to offload the scraping to a standalone script (`scripts/woolworths/woolworths_optimizer.py`), triggered via `subprocess.Popen` from the notebook.

## 14. `FileNotFoundError` in Sub-modules
**Symptom**: `data/woolworths_stores.csv` wasn't found when running scripts via `subprocess` because the script CWD was different from the notebook CWD.
**Resolution**: Implemented robust absolute path construction in `woolworths_optimizer.py` using `os.path.abspath(os.path.dirname(__file__))`.

## 15. Woolworths API Exploration — Full `/api/v1` Surface Discovery

**Symptom**: Needed to determine if the Woolworths JSON API (`/api/v1/products`) could replace the Playwright DOM scraping layer for product price retrieval.

**Cause**: Previous testing (log #7) had concluded the API was unusable, but had not tested with the correct header or with a seeded session.

**Resolution**: Built `scripts/woolworths/explore_woolworths_api.py` and performed systematic black-box probing of the `/api/v1` surface. Key findings:
- `GET /api/v1/products?target=search` returns real product data with prices, just by seeding cookies with a single `GET /` — no login or Playwright required.
- `GET /api/v1/shell` returns the full navigation taxonomy and `context.fulfilment` object (default store: `fulfilmentStoreId: 9171`).
- `GET /api/v1/addresses/pickup-addresses` returns all pickup stores (only `id`, `name`, `address` keys — no bridge to lat/lon).
- `target=browse` with `dasFilter=Department;;<slug>;false` works for department-level filtering (14 departments, 100+ aisles mapped).
- Aisle-level `dasFilter` chaining is accepted but does not seem to narrow results.
- `fulfilmentStoreId`, `pickupStoreId`, and 9 other store-context parameters all return HTTP 200 but **do not change prices** — pricing is global to current knowledge.
- 19 POST store-switch endpoints all return 404 — no API path exists for programmatic store context changes.
- Full documentation written to `Woolworths_API.md`.
