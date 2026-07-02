# Woolworths NZ - Reverse Engineering Handover

Status: Paused — store locations sourced via Nominatim; awaiting per-store price scoping validation

## API Endpoints

- Base URL: `https://www.woolworths.co.nz`
- Product search: `GET /api/v1/products?target=search&search=<query>&inStockProductsOnly=false&size=<n>`
- Cart: `POST /api/v1/trolleys/my/items`, `GET /api/v1/trolleys/my`, `DELETE /api/v1/trolleys/my/items`
- Pagination constants: `ITEMS_PER_PAGE = [24, 48, 120]`, `MINIMUM_PAGE_SIZE = 24`

## Authentication

- No guest token. Requires real account + Camoufox browser login.
- Session cookies reused for ~weeks.
- XSRF-TOKEN cookie required as `x-xsrf-token` header on POST/DELETE.
- Akamai blocks plain scripts for login; Camoufox used for auth only.

## Store Data

- **Source**: OpenStreetMap/Nominatim via `scripts/woolworths/stores_fetch.py`
- **Schema**: `osm_place_id`, `name`, `address`, `city`, `region`, `latitude`, `longitude`
- **Coverage**: targeting ~180 NZ stores; deduplicated on `(latitude, longitude)`
- **Crawl etiquette**: 1 req/sec + `User-Agent: NZMealCostOptimizer/1.0 (research project)`
- No public store enumeration API found; internal Woolworths numeric IDs visible in UI bundles but not yet mapped.

## Critical Blocker

- Per-store pricing unconfirmed. The search endpoint has no documented `storeId` parameter.
- Pricing may be global unless a separate "select store" call scopes the session.
- Must be verified experimentally before integration.

## Next Steps

1. Implement `WoolworthsAPI` class (auth, product search).
2. Reverse-engineer store-select mechanism (if it exists).
3. Confirm search is store-scoped by testing with two store contexts.
4. Integrate into `prototype.py` for multi-chain comparison once confirmed.
