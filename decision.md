# Key Decisions

## 1. Pak'nSave first, expand later

Chose Pak'nSave as initial target because their mobile API is accessible (no auth walls beyond guest token). Other NZ supermarkets (New World, Woolworths) can be added by replicating the API pattern for their platforms.

## 2. Foodstuffs mobile API over website scraping

The Pak'nSave website is a Next.js app on Vercel with Cloudflare protection and a .NET backend (`CommonApi`). Direct website scraping is blocked. The mobile API (`api-prod.prod.fsniwaikato.kiwi`) has no Cloudflare and accepts guest tokens — far more reliable.

## 3. cloudscraper for website requests, plain requests for API

`cloudscraper` is used when hitting `paknsave.co.nz` (Cloudflare-protected). The mobile API domain has no Cloudflare, so `cloudscraper` works but isn't strictly necessary there. Both scripts use `cloudscraper` for consistency.

## 4. Guest token auth (no user accounts)

No login required — guest token obtained via POST with `{"banner": "PNS"}`. Token lasts 30 min and is auto-refreshed. Avoids needing to handle user credentials.

## 5. First/most-relevant result, not cheapest

Product search returns results sorted by relevance. Taking the cheapest would return pet food or bulk items for queries like "beef mince". Using `products[0]` gives the most practical match.

## 6. Hand-curated ingredient lists

21 dishes with manually defined ingredient lists. No NLP/LLM parsing because:
- Keeps the prototype simple and deterministic
- Avoids API costs or model dependencies
- Ingredient queries need to be specific to Pak'nSave's product naming

## 7. 5 km search radius

Auckland CBD has only 1 Pak'nSave within 5 km. East Auckland (Botany/Manukau) has 3. The 5 km default balances convenience with store coverage. Adjustable via `MAX_DISTANCE_KM`.

## 8. Pak'nSave Store data from __NEXT_DATA__ (single fetch)

All store data is now obtained from a single fetch of the `/store-finder` page's `__NEXT_DATA__`:
- **`contentstackStores`**: maps URL paths to store GUIDs (60 stores)
- **`store_finder.regionStoreGroupings`**: provides store name, address, and latitude/longitude

The two datasets are joined on the shared `url` field. This eliminated the need for both the separate homepage fetch and the Nominatim geocoding step.

## 9. Nominatim for Pak'nSave Store geocoding (retired)

Geocoding is no longer needed — the `/store-finder` page's `__NEXT_DATA__` includes latitude/longitude directly from the `contactDetails` field, with higher precision than Nominatim returns. The Nominatim rate limit (1 req/sec), dedicated `User-Agent`, and `time.sleep` delay were all removed.

## 10. Jupyter notebook as primary interface

Chosen for easy experimentation — user can edit inputs and re-run cells without touching the terminal. CLI (`prototype.py`) available as alternative.

## 11. API-based Woolworths store discovery
Woolworths store locations are manually identified via a discovered JSON API (`https://api.cdx.nz/site-location/api/v1/sites`). This replaces manual HTML inspection and provides complete, structured, and filterable store data.

## 12. Automated store discovery
Store locations are now fetched and converted to CSV automatically using `scripts/woolworths/Get_woolworths_store_API_data.py`. This approach provides complete coverage and allows for automated filtering based on distance.

## 13. Playwright headed scraping over direct API for Woolworths

Initial testing of `GET /api/v1/products?target=search&search=milk` returned `400 Header is missing or is invalid.` — the documented endpoint is not usable without a verified authenticated session context. Playwright (headed Chromium) can load the public search results page and read rendered prices from Angular shadow DOM (`product-stamp-grid > div.product-entry`). Headless mode is unstable due to Akamai, so headed mode with `--disable-blink-features=AutomationControlled` is required. Successfully navigated to the Woolworths website and located the store selection dropdown.

**Update (resolved):** The `target=search` endpoint **does** work without authentication — the `400` was caused by a missing `x-requested-with: ??` header, not by missing session context. A single `GET /` seeds cookies, and the API can be called with `requests.Session`. Playwright is NOT needed at runtime for any API operation. The `cw-lrkswrdjp` cookie can be constructed from `extra1` in `woolworths_store_data.json` and injected into a `requests.Session` for per-store pricing. Playwright was only needed for the initial exploration/discovery phase.

## 14. Joined Woolworths store datasets via common ID

Successfully linked store names (from dropdown choices API) with latitude/longitude (from location API) using a common ID. This allows for accurate store identification and filtering by distance, resolving previous name-matching issues.

## 15. Direct Store Selection via URL
Chose to use `https://www.woolworths.co.nz/bookatimeslot/(hww-modal:change-pick-up-store)` to bypass complex dropdown navigation and directly trigger the store selection modal, enabling reliable automated store selection.

## 16. Jupyter/Windows Async Workaround
Use `subprocess.Popen` for scraping to bypass `NotImplementedError` in Jupyter's event loop (Windows Proactor policy conflict).

## 17. Robust Pathing
Use absolute path construction (`os.path.abspath`) with `__file__` or `os.getcwd()` for all file access, preventing `FileNotFoundError` in sub-scripts.

## 18. Woolworths API `x-requested-with: ??` header

The `GET /api/v1/products?target=search` endpoint requires the literal header `x-requested-with: ??` (or any non-empty string including `XMLHttpRequest`). Without this header, all API calls return HTTP 400. Discovered via black-box probing of the `/api/v1` surface + existing github repositories. This header was the sole blocker that previously made the API appear unusable.

## 19. Woolworths per-store pricing — cookie injection, not query params

`fulfilmentStoreId` and `pickupStoreId` query parameters on `/api/v1/products` are accepted (HTTP 200) but **do not change prices**. Per-store pricing is controlled by the `cw-lrkswrdjp` cookie, which encodes `dm-Pickup,f-{fulfilmentStoreId},a-{areaId},s-{site}`. The cookie can be constructed from `extra1` in `woolworths_store_data.json` (verified 3/3 stores). Different stores return different prices (e.g., Greymouth Milk 3L = $7.15, Glenfield = $7.33). The optimizer must search each ingredient at each nearby store with a fresh session per store.

## 20. `cw-lrkswrdjp` is the sole per-store cookie

Of the 67 cookies captured from Playwright, only `cw-lrkswrdjp` carries store context. The other 66 cookies (session_state, RT, Akamai, analytics, ads) were systematically isolated and proven irrelevant — injecting them alone does not change pricing. The full 67-cookie jar produces the same result as injecting just `cw-lrkswrdjp`. This was verified in `explore_woolworths_api_part2.py` (session_state-only and RT-only tests) and `explore_woolworths_api_part3.py` (cookie-only injection).

## 21. `extra1` in `woolworths_store_data.json` = `fulfilmentStoreId`

The `extra1` field from the CDX store locator API (`api.cdx.nz`) is the `fulfilmentStoreId` used in the `cw-lrkswrdjp` cookie. Verified across 3 stores:

| Store | extra1 | fulfilmentStoreId (from cookie) | Match |
|-------|--------|--------------------------------|-------|
| Greymouth | 9009 | 9009 | [OK] |
| Glenfield | 9443 | 9443 | [OK] |
| Birkenhead | 9101 | 9101 | [OK] |

This means Playwright is NOT needed even for initial mapping capture — the cookie can be constructed for all 183 stores directly from the data file. The `extra2` field is the `pickupAddressId` (different number).

## 22. Fresh session required per store

The server's `Set-Cookie` response from `GET /` overwrites any injected `cw-lrkswrdjp` cookie when reusing a `requests.Session`. Tested by injecting cookies for 3 Auckland stores into the same session — only the first store's context was respected. Creating a fresh session (new `GET /`) for each store fixes this. This is implemented in `woolworths_optimizer.py`.

## 23. `areaId` is optional in the cookie

The `a-{areaId}` field in `cw-lrkswrdjp` is not required for per-store pricing. Tested in `explore_woolworths_api_part3.py` Step 3c:
- `dm-Pickup,f-9009,a-0,s-38` works (areaId=0)
- `dm-Pickup,f-9009,a-224` works (no s-field)
- `dm-Pickup,f-9009` works (minimum viable)

The `areaId` is NOT available from any API endpoint and would require Playwright to capture per-store. Since it's optional, this is not a blocker.

## 24. `s-38` is constant across all tested stores

The `s-{site}` field in `cw-lrkswrdjp` is `38` for Greymouth, Glenfield, and Birkenhead. Safe to hardcode in cookie construction.
