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

**Resolution**: Abandoned public API enumeration. Switched to OpenStreetMap/Nominatim as store location source.

## 5. Initial Woolworths keyword search insufficient

**Symptom**: Initial nationwide-only keyword queries (`Woolworths New Zealand`, `Countdown New Zealand`, etc.) returned ~50 stores, well below the expected ~180 NZ stores.

**Cause**: Many OSM entries are only tagged with local-area names and don't surface under broad national keywords.

**Resolution**: Expanded `scripts/woolworths/stores_fetch.py` to use per-region keyword patterns (`{region} Woolworths`, `Countdown {region}`, etc.) to maximise coverage.

## 6. Woolworths store-finder URL pattern not yet integrated

**Symptom**: Internal numeric store IDs are visible in the Angular SPA store-finder URL pattern (`/store-finder/{id}/{city}/{slug}`), but there is no public API to map these to coordinates or names.

**Cause**: Internal IDs are client-side routing only; no JSON endpoint exposes the mapping.

**Resolution**: Not yet resolved. Internal IDs remain unmapped to OSM place IDs. Using Nominatim coordinates for now; internal IDs may be needed later if per-store pricing is confirmed.

## 7. Woolworths direct product search API unusable (`400 Header is missing or is invalid.`)

**Symptom**: Calling `GET /api/v1/products?target=search&search=milk&inStockProductsOnly=false&size=24` from both outside the browser and via Playwright's `page.request` returns HTTP 400 with `{"message":"One or more errors occurred","errors":[{"field":"Header","message":"Header is missing or is invalid."}]}`.

**Cause**: The `target=search` endpoint requires a session/header context established by prior authenticated or scoped requests that Playwright's direct request does not provide.

**Resolution**: Abandoned direct REST pathway for search. Site uses client-side Angular rendering (`product-stamp-grid`) and search results appear under `/shop/searchproducts?search=...` without login. Pivoted to Playwright headed scraping from the rendered page, reading Angular shadow DOM instead of JSON API.

## 8. Headless Playwright blocked on Woolworths (`ERR_HTTP2_PROTOCOL_ERROR`)

**Symptom**: Running `page.goto("https://www.woolworths.co.nz/")` with `headless=True` and `--disable-blink-features=AutomationControlled` raised `net::ERR_HTTP2_PROTOCOL_ERROR`.

**Cause**: Site/Akamai blocks headless/automation fingerprints despite standard disguise arguments.

**Resolution**: Use headed mode with `headless=False` and standard user-agent/locale/timezone settings. Search and DOM extraction work reliably in this configuration.
