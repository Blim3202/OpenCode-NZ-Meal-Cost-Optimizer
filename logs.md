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

**Resolution**: The API is fully functional with `requests.Session` when the `x-requested-with: ??` header is included. Playwright is NOT needed at runtime for any API operation. Per-store pricing is achieved via `cw-lrkswrdjp` cookie injection (see Log #16). Full endpoint documentation in `Woolworths_API.md`.

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
- `fulfilmentStoreId`, `pickupStoreId`, and 9 other store-context parameters all return HTTP 200 but **do not change prices** — pricing appeared global at this stage.
- 19 POST store-switch endpoints all return 404 — no API path exists for programmatic store context changes.
- Full documentation written to `Woolworths_API.md`.

**Update**: Per-store pricing was later discovered via `cw-lrkswrdjp` cookie injection (see Logs #16-#20). The query-parameter approach was a dead end, but the cookie approach works.

## 16. Playwright Cookie Injection Produces Per-Store Pricing

**Symptom**: Needed to determine if per-store pricing exists at all, or if Woolworths truly uses a global price list.

**Cause**: Previous testing (Log #15) only tested query parameters, not cookie-based store context. The `cw-lrkswrdjp` cookie carries store context but was not tested.

**Resolution**: Built `explore_woolworths_api_part2.py`. Captured full Playwright cookie jars for Greymouth and Glenfield after selecting each store in the change-pick-up-store modal. Injected the full 67-cookie jar into `requests.Session` via `session.cookies.set()`. Searched "milk" at both stores:
- Greymouth: Woolworths Milk Standard 3L = **$7.15** [OK]
- Glenfield: Woolworths Milk Standard 3L = **$7.33** [OK]
- Price difference: $0.18 confirmed

Also tested URL-param seeding (`?pickupStoreId=764300`), session_state-only injection, and RT-only injection — all failed. Only the full cookie jar (or the `cw-lrkswrdjp` cookie specifically) works.

## 17. `cw-lrkswrdjp` Is the Sole Per-Store Cookie

**Symptom**: Needed to determine which of the 67 Playwright cookies controls store context, to avoid depending on the full jar.

**Cause**: The full 67-cookie jar works, but capturing and injecting all cookies is fragile and complex. Identifying the single required cookie would simplify the architecture.

**Resolution**: Built `explore_woolworths_api_part3.py`. Systematically isolated cookies:
- Injecting only `session_state` (Optimizely): both stores return $7.33 (wrong) [FAIL]
- Injecting only `RT` (Adobe Analytics): both stores return $7.33 (wrong) [FAIL]
- Injecting only `cw-lrkswrdjp`: both stores return correct prices ($7.15 / $7.33) [OK]

The `cw-lrkswrdjp` cookie format is `dm-Pickup,f-{fulfilmentStoreId},a-{areaId},s-{site}`. The `a-` and `s-` fields are optional — `dm-Pickup,f-{fulfilmentStoreId}` alone works.

## 18. Cookie Construction from `extra1` — No Playwright Needed

**Symptom**: Needed a way to construct `cw-lrkswrdjp` cookies for all 183 stores without running Playwright for each one.

**Cause**: The `fulfilmentStoreId` used in the cookie is NOT the same as `pickupAddressId` (the public store ID). These are different numbers with no formulaic relationship. Without a mapping, Playwright would be needed to capture each store's `fulfilmentStoreId`.

**Resolution**: Discovered that `extra1` in `woolworths_store_data.json` (fetched from CDX store locator API) IS the `fulfilmentStoreId`. Verified across 3 stores:
- Greymouth: extra1=9009, cookie f-field=9009 [OK]
- Glenfield: extra1=9443, cookie f-field=9443 [OK]
- Birkenhead: extra1=9101, cookie f-field=9101 [OK]

Cookie construction: `dm-Pickup,f-{extra1},s-38`. This works for all 183 stores without any Playwright.

## 19. Fresh Session Per Store Required

**Symptom**: When testing the cookie injection across multiple Auckland stores, all stores returned the same `fulfilmentStoreId` (9250) instead of their individual IDs.

**Cause**: The server's `Set-Cookie` response from `GET /` includes a `cw-lrkswrdjp` cookie with the default store. When `session.cookies.set()` is called to inject a different value, the next request triggers the server to overwrite it with its own value. The injected cookie is effectively ignored on reused sessions.

**Resolution**: Create a fresh `requests.Session` for each store. Each session gets its own `GET /` to seed cookies, then the `cw-lrkswrdjp` is injected before the server can overwrite it. Tested with 5 Auckland stores — all returned correct unique `fulfilmentStoreId`s (9250, 9045, 9500, 9405, 9544). Implemented in `woolworths_optimizer.py`.

## 20. End-to-End Optimizer Test — Per-Store Pricing Working

**Symptom**: Needed to verify the complete pipeline works: geocode, find stores, inject cookies, search products, compare costs.

**Cause**: After building `woolworths_api.py` and refactoring `woolworths_optimizer.py`, needed end-to-end validation.

**Resolution**: Ran optimizer with "123 Queen Street, Auckland CBD" and "spaghetti bolognese":
- Found 9 stores within 5 km with unique fulfilmentStoreIds
- Searched 7 ingredients at each store (63 API calls total)
- Per-store price differences visible:
  - Garlic: $2.50 (Newmarket) to $2.70 (most stores) — different products at different prices
  - Total cost: Newmarket $18.60 (cheapest), most others $18.80
  - Pipeline working: geocode → nearby stores → fresh session per store → cookie injection → product search → cost comparison
  - No Playwright needed at runtime — pure `requests` + constructed cookies

## 21. New World store-finder page `__NEXT_DATA__` structure changed

**Symptom**: The `fetch_stores.py` script for New World couldn't find `store_finder.regionStoreGroupings` in the `__NEXT_DATA__` JSON.

**Cause**: The `__NEXT_DATA__` structure changed from Pak'nSave's layout. New World's store-finder nests `store_finder` inside `page.page_content.content_blocks[1]` instead of at the top level of `pageProps`.

**Resolution**: Updated the JSON path to `data.props.pageProps.page.page_content.content_blocks[1].store_finder.regionStoreGroupings`. Verified the structure has `northIsland` and `southIsland` keys, each containing `groups` with `stores` arrays (each store has `title`, `url`, `address`).

## 22. New World Edge API — store listing works with mobile token, NO product search

**Symptom**: `GET https://api-prod.newworld.co.nz/v1/edge/store/physical` returned HTTP 401 with `{"fault":{"faultstring":"Failed to Resolve Variable : policy(JWT-VerifyRetailEdgeToken) variable(null)"}}` when tested without proper authentication.

**Cause**: The Edge API is behind an Apigee gateway with a `JWT-VerifyRetailEdgeToken` policy that validates JWT tokens. The error occurs when no valid JWT is provided.

**Discovery**: The Foodstuffs mobile API guest token (a JWT from `online-customer` IdP) **is accepted by the Edge API** when both headers are provided:
- `Authorization: Bearer {token}`
- `access_token: {token}`

The mobile token works because both APIs share the same IdP (`iss: "online-customer"`).

**However**: The Edge API has **NO product search endpoints** — all tested endpoints return 404:
- `/v1/edge/products/search`, `/v1/edge/products`, `/v1/edge/ecomm-products/*`, `/v1/edge/search`, `/v1/edge/categories`

**Resolution**: The Edge API cannot replace the mobile API for the meal cost optimizer. Store listing works, but product search (essential for per-store pricing) does not exist. Continue using the Foodstuffs mobile API (`api-prod.prod.fsniwaikato.kiwi/prod`) for all New World operations.

**Exploration scripts**: `scripts/newworld/Exploration/explore_edge_api.py`, `explore_edge_api2.py`, `explore_edge_api3.py`, `explore_edge_api4.py`, `explore_edge_api5.py`
**Documentation**: `scripts/newworld/Exploration/EDGE_API_FINDINGS.md`

## 23. New World mobile API requires `NewWorldApp/4.32.0` User-Agent

**Symptom**: The Foodstuffs mobile API worked for Pak'nSave (`banner: "PNS"`) but failed for New World (`banner: "MNW"`) with the same `PAKnSAVEApp/4.32.0` User-Agent.

**Cause**: The mobile API validates the User-Agent against the banner. New World requests require `NewWorldApp/4.32.0` (analogous to `PAKnSAVEApp/4.32.0` for Pak'nSave).

**Resolution**: Used `User-Agent: NewWorldApp/4.32.0` for all New World API requests. Guest login: `POST /mobile/user/login/guest` with `json={"banner": "MNW"}`.

## 24. 22 New World stores missing coordinates via Nominatim

**Symptom**: The initial `fetch_stores.py` used Nominatim geocoding on store-finder page addresses. Of 150 stores, 22 were missing coordinates (Eastridge, Howick, Kumeu, Te Atatu, Victoria Park, Aokautere, Broadway, Foxton, Masterton, Brookfield, Mt Maunganui, Tūrangi, Karori, Newlands, Silverstream, Stokes Valley, Whitby, Bishopdale, Ferry Road, Ilam, Nelson City, Greymouth).

**Cause**: Nominatim could not resolve these addresses — either too vague, non-standard formatting, or missing from OSM data.

**Resolution**: Switched to the Foodstuffs mobile API (`GET /mobile/store/physical`) which provides latitude/longitude directly for all 149 stores. Eliminated the Nominatim geocoding step entirely.

## 25. 7 New World stores missing URLs (name mismatch between API and page)

**Symptom**: After merging mobile API data (149 stores with coordinates/IDs) with store-finder page data (150 stores with URLs), 7 stores had no URL match.

**Cause**: Store names differ between the mobile API and the store-finder page:
- "Foodie Mart" (API) — not on the page (different entity)
- "New World Metro Auckland" (API) vs "Metro Queen Street" (page)
- "New World Metro Willis St" (API) vs "Willis Street Metro" (page)
- "New World Mount Maunganui" (API) vs "Mt Maunganui" (page)
- "New World Shore City" (API) vs "Metro Shore City" (page)
- "New World Turangi" (API) vs "Tūrangi" (page — macron difference)
- "New World Wanaka" (API) vs "Wānaka" (page — macron difference)

**Resolution**: Accepted the 7 missing URLs. URLs are only used for linking to the store page on the website — not needed for the API-based optimizer. Could be fixed with fuzzy string matching (e.g., `fuzzywuzzy`) but is low priority.

## 26. New World store count discrepancy (149 API vs 150 page)

**Symptom**: The mobile API returns 149 stores; the store-finder page lists 150.

**Cause**: "Foodie Mart" (35 Landing Drive, Mangere) appears in the mobile API but not on the store-finder page. It may be a different entity or temporarily excluded from the page.

**Resolution**: Used the mobile API as the authoritative source (149 stores). The extra page store ("Te Atatu") is also not in the API. This store is set to open on 11/08/2026, suggesting that the API is currently filtered out not populated yet for this store.

(End of file)
