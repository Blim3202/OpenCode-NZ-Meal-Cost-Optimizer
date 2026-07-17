Goal
- Build and refine the NZ Meal Cost Optimizer project, currently focused on exploring and documenting the Woolworths NZ backend API (/api/v1) to determine whether Playwright scraping can be replaced with direct API calls.
Constraints & Preferences
- Ignore hidden files (.Temp, .ignore, .venv, .test) in wakeup skill calls
- Always pause and ask for confirmation before git push or git pull
- Never access external directories unless invoking skills
- All runs must be in the project directory
- Only commit relevant changes; no unstaged/uncommitted additions
- User prefers concise plans with no excessive text
- New doc files go at project root level
Progress
Done
- Created explore_woolworths_api.py — black-box probing of /api/v1 endpoints (renamed from test_woolworths_api.py)
- Confirmed GET /api/v1/products?target=search works with unauthenticated session (just GET / to seed cookies + x-requested-with: ?? header)
- Confirmed GET /api/v1/products?target=browse returns full 10K-item catalogue with sort options (PriceAsc, PriceDesc, CUPAsc)
- Confirmed GET /api/v1/shell returns navigation taxonomy, context.fulfilment, and context.shopper
- Confirmed GET /api/v1/addresses/pickup-addresses returns store list (3 keys: id, name, address only)
- Confirmed target=browse&dasFilter=Department;;<slug>;false works for department-level filtering
- Confirmed prices are global — fulfilmentStoreId, pickupStoreId, and 8 other store-context params accepted but produce zero price changes
- Confirmed no POST endpoint for programmatic store switching (19 paths tested, all 404)
- Built complete dasFacet hierarchy: 14 departments, all aisles with IDs and product counts
- Created Woolworths_API.md (850 lines) — full API documentation at project root
- Updated AGENTS.md: corrected file structure/filenames, updated key gotchas, updated Woolworths Research Status
- Updated decision.md: added revision note to Decision #13 (Playwright scraping is now redundant)
- Updated logs.md: corrected Log #7 (API does work), added new Log #9 (API exploration)
In Progress
- No current active task — awaiting user direction on next steps
Blocked
- target=browse dasFilter does NOT support aisle-level or shelf-level narrowing (accepted but ignored)
- No programmatic way to set store context — Playwright still required for ChangeStore.py cookie-based switching
- context.fulfilment.fulfilmentStoreId: 9171 is a delivery-area ID, not in pickup-addresses list — two separate ID namespaces
Key Decisions
- Woolworths API uses shop.countdown.co.nz backend (Countdown/Woolworths NZ shared platform)
- x-requested-with: ?? is the literal required header value (not a placeholder)
- Session seeding: single GET / with browser UA is sufficient — no login, no Playwright needed for search
- Woolworths prices are global per-store — optimizer only needs one search per ingredient, not per store
- Playwright store-switching layer is still required for correctness (availability context), but price retrieval can use requests directly
- dasFilter syntax: Department;;meat-poultry;false (semicolon-delimited, key;;value;boolean)
Next Steps
- Decide whether to refactor Woolworths pipeline to use JSON API instead of Playwright scraping
- Investigate whether browser cookies from ChangeStore.py can be captured and injected into requests.Session for store-context switching without Playwright
- Expand DISH_INGREDIENTS in Woolworths pipeline to match Pak'nSave's 21 dishes
- Fix known bugs: browser.close() inside loop in woolworths_optimizer.py:196, head(2) hardcoded in woolworths_optimizer.py:175
Critical Context
- Backend hostname shop.countdown.co.nz appears in all 404 error messages — confirmed shared infrastructure
- context.fulfilment default: fulfilmentStoreId=9171, method=Courier, pickupAddressId=0, address=Glenfield
- Product price schema: item.price.salePrice (current price), item.price.originalPrice, item.price.isSpecial, item.price.isClubPrice
- target=browse without dasFilter returns totalItems=10000 with dasFacets containing all 14 departments
- target=browse with department dasFilter returns aisle-level facets but aisle chaining doesn't narrow results
- All shelfResponses are empty ([]) at department level — shelf data not exposed via API
- Store records from pickup-addresses have only 3 keys — no siteDataId, externalId, or bridge fields to cross-reference with woolworths_stores.csv
Relevant Files
- Woolworths_API.md: Full API documentation — all tested endpoints, parameters, response schemas, dasFacet hierarchy, per-store pricing findings
- AGENTS.md: Project overview with corrected file structure and Woolworths Research Status
- decision.md: Revised Decision #13 re: Playwright vs API
- logs.md: Corrected Log #7, added Log #9
- scripts/woolworths/explore_woolworths_api.py: API exploration script (formerly test_woolworths_api.py)
- scripts/woolworths/woolworths_optimizer.py: Main async Woolworths optimizer (has known bugs)
- scripts/woolworths/woolworths_scrape.py: Playwright headed scraper
- scripts/woolworths/ChangeStore.py: Playwright store selection (cookie-based)
- scripts/paknsave/PaknSave_prototype.py: Fully working Pak'nSave CLI
- data/woolworths_stores.csv: Merged Woolworths store list (172 stores)
- data/woolworths_store_choices.csv / .json: Woolworths pickup location IDs
- data/woolworths_store_data.csv / .json: Woolworths lat/lon data