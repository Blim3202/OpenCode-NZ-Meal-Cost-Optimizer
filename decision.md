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

## 8. Store GUIDs from __NEXT_DATA__

Store GUIDs are extracted from the `contentstackStores` array in the homepage's `__NEXT_DATA__` script tag. This gives all 60 stores with their Contentstack UIDs, which map to the API's `store_id` values.

## 9. Nominatim for geocoding

Free, no API key needed, sufficient accuracy for NZ addresses. Rate limit of 1 req/sec is acceptable for a prototype. Could be swapped for Google Geocoding if higher accuracy or speed is needed.

## 10. Jupyter notebook as primary interface

Chosen for easy experimentation — user can edit inputs and re-run cells without touching the terminal. CLI (`prototype.py`) available as alternative.

## 11. API-based Woolworths store discovery
Woolworths store locations are identified via a discovered JSON API (`https://api.cdx.nz/site-location/api/v1/sites`). This replaces manual HTML inspection and provides complete, structured, and filterable store data.

## 12. Automated store discovery
Store locations are now fetched and converted to CSV automatically using `scripts/woolworths/Extract_woolworths_API_JSON.py`. This approach provides complete coverage and allows for automated filtering based on distance.

## 13. Playwright headed scraping over direct API for Woolworths

Initial testing of `GET /api/v1/products?target=search&search=milk` returned `400 Header is missing or is invalid.` — the documented endpoint is not usable without a verified authenticated session context. Playwright (headed Chromium) can load the public search results page and read rendered prices from Angular shadow DOM (`product-stamp-grid > div.product-entry`). Headless mode is unstable due to Akamai, so headed mode with `--disable-blink-features=AutomationControlled` is required. Successfully navigated to the Woolworths website and located the store selection dropdown.
