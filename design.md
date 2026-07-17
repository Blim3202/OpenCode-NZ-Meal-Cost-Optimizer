# Technical Design

## Architecture Overview

```
User input (address + dish)
  → Geocode address to lat/lon
  → Haversine filter (stores within 5 km)
  → Dish name → ingredient list (DISH_INGREDIENTS map)
  → Foodstuffs mobile API: search each ingredient at each nearby store
  → Aggregate prices, compare totals, display cheapest
```

## Foodstuffs Mobile API

Base URL: `https://api-prod.prod.fsniwaikato.kiwi/prod`

### PAKnSAVE Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/mobile/user/login/guest` | POST | Guest auth. Body: `{"banner": "PNS"}` |
| `/mobile/store/physical` | GET | List all 60 stores (needs auth headers) |
| `/mobile/ecomm-products/PNS/{storeId}/search?q={query}` | POST | Search products. Body: `[]` |

### PAKnSAVE Auth Flow

1. POST to `/mobile/user/login/guest` with `{"banner": "PNS"}` and `User-Agent: PAKnSAVEApp/4.32.0`
2. Response contains `access_token` (valid 1800s / 30 min)
3. All subsequent requests need both headers:
   - `Authorization: Bearer {token}`
   - `access_token: {token}`
4. Token is auto-refreshed by `PaknSaveAPI._ensure_token()` when expired

### PAKnSAVE Product Search Response

```json
{
  "totalHits": 10,
  "page": 1,
  "numberOfPages": 1,
  "products": [
    {
      "name": "NZ Beef Mince",
      "brand": "Pams",
      "price": 1899,        // cents
      "units": "kg",
      "productId": "...",
      "categories": [...],
      "productImageUrls": [...]
    }
  ]
}
```

- **Prices are in cents** — divide by 100 for display.
- Results sorted by relevance, not price. Always take `products[0]` (most relevant).
- `cloudscraper` is NOT needed for API calls — no Cloudflare on the API domain.

### PAKnSAVE Store Data Sources

1. **Mobile API** (`/mobile/store/physical`): 60 stores, precise coords, accurate names. Returns `{"stores": [...]}`.
2. **CSV fallback** (`data/paknsave_stores.csv`): pre-built from `/store-finder` page's `__NEXT_DATA__`. Same `store_id` UUIDs as API.
3. **Build process** (`scripts/paknsave/fetch_stores.py`): single fetch of `/store-finder` extracts `contentstackStores` (GUIDs) and `store_finder.regionStoreGroupings` (names, addresses, coordinates) — joined on the shared `url` field.

## Store Building Pipeline

```
fetch_stores.py
  → GET /store-finder → parse __NEXT_DATA__
  → Extract contentstackStores: url → store_id (GUID) map
  → Extract store_finder.regionStoreGroupings: title, address, lat/lon per store
  → Join on url field → DataFrame → data/paknsave_stores.csv
```

No geocoding required — coordinates are provided directly by the page source.

## Store Distance

- Haversine formula calculates great-circle distance between user lat/lon and each store's coordinates
- Default radius: 5 km
- Stores sorted by distance ascending

## Ingredient Mapping

- `DISH_INGREDIENTS` dict in `scripts/prototype.py` (and notebook cell 4)
- 21 dishes, each mapping to a list of search query strings
- Unknown dishes fall through: the dish name itself becomes the single search query
- No NLP/LLM parsing — entirely hand-curated

### Supported Dishes (21)

| Dish | Ingredients |
|---|---|
| spaghetti bolognese | beef mince, spaghetti pasta, canned tomatoes, onion, carrot, garlic, mixed herbs |
| chicken stir fry | chicken breast, stir fry vegetables, soy sauce, rice noodles |
| beef stir fry | beef strips, stir fry vegetables, soy sauce, rice noodles |
| roast lamb | lamb roast, potato, carrot, broccoli, stock |
| chicken curry | chicken thigh, curry paste, coconut milk, rice, onion |
| beef curry | diced beef, curry paste, coconut milk, rice, onion |
| fish and chips | fish fillet, potato, oil |
| nachos | beef mince, tortilla chips, cheese, beans, sour cream |
| pumpkin soup | pumpkin, onion, cream, stock, bread |
| tacos | beef mince, taco shells, lettuce, tomato, cheese, sour cream |
| lamb chops | lamb chops, potato, mint sauce |
| butter chicken | chicken thigh, butter chicken sauce, rice, cream |
| lasagne | beef mince, lasagne sheets, cheese, canned tomatoes, milk, butter, flour |
| shepherd's pie | beef mince, potato, carrot, peas, stock |
| pizza | pizza base, pizza sauce, cheese, pepperoni |
| vegie stir fry | stir fry vegetables, tofu, soy sauce, rice noodles, garlic |
| frittata | eggs, potato, onion, cheese, milk |
| pancakes | flour, eggs, milk, sugar, butter |
| chicken soup | chicken breast, carrot, onion, celery, stock, pasta |
| tomato pasta | pasta, canned tomatoes, garlic, olive oil, mixed herbs, cheese |
| chicken katsu | chicken breast, flour, eggs, bread, rice, katsu sauce |

To add a dish: edit `DISH_INGREDIENTS` in `scripts/prototype.py` (or notebook cell 4).

## CLI Usage

```powershell
python scripts/paknsave/PaknSave_prototype.py "Botany Town Centre, Auckland" "spaghetti bolognese"
```

Args: `[address] [dish name]`. Defaults to "123 Queen Street, Auckland CBD" and "spaghetti bolognese".

## Woolworths API Architecture

### How It Works

```
User input (address + dish)
  → Geocode address to lat/lon (Nominatim)
  → Haversine filter (stores within 5 km from woolworths_store_data.json)
  → Dish name → ingredient list (DISH_INGREDIENTS map, 21 dishes)
  → FOR EACH nearby store:
      → Create fresh requests.Session + GET / to seed cookies
      → Inject cw-lrkswrdjp cookie (constructed from extra1)
      → Validate via /api/v1/shell (fulfilmentStoreId != 9171)
      → Search each ingredient via /api/v1/products?target=search
      → Collect per-store prices
  → Aggregate prices, compare totals, display cheapest
```

### Woolworths API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/shell` | GET | Navigation taxonomy, session context, fulfilment details |
| `/api/v1/products?target=search&search=<term>` | GET | Product search with prices |
| `/api/v1/products?target=browse&dasFilter=Department;;<slug>;false` | GET | Browse by department |
| `/api/v1/addresses/pickup-addresses` | GET | All pickup stores (id, name, address) |

### Required Headers

```
x-requested-with:  ??           <- literal string, not a placeholder
User-Agent:        Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...
Accept:            application/json, text/plain, */*
```

### Cookie-Based Store Context

The `cw-lrkswrdjp` cookie controls per-store pricing:
```
dm-Pickup,f-{fulfilmentStoreId},a-{areaId},s-38
```

- `fulfilmentStoreId` = `extra1` from `woolworths_store_data.json` (NOT the same as `pickupAddressId`)
- `areaId` is optional (cookie works without it)
- `s-38` is constant across all stores

### woolworths_api.py Module

```python
from woolworths_api import create_session, set_store_context, search_products, find_cheapest, get_nearby_stores, geocode

# Geocode address
lat, lon = geocode("123 Queen Street, Auckland")

# Find nearby stores
stores = get_nearby_stores(lat, lon, max_dist_km=5)

# Search with per-store pricing
for store in stores:
    session = create_session()  # fresh session per store (required!)
    set_store_context(session, store["pickupAddressId"])
    cheapest = find_cheapest(session, "beef mince")
    print(f"{store['name']}: ${cheapest['salePrice']}")
```

### Key Constraints

- **Fresh session per store**: The server's `Set-Cookie` response overwrites injected cookies on reused sessions
- **No login required**: Public API endpoints work with unauthenticated sessions
- **Search returns relevance, not cheapest**: Take first result for practical matches
- **21 hand-curated dishes**: No NLP/LLM parsing yet

## Notebook Usage

| Cells | What to do |
|---|---|
| 1–4 | **Setup** — run once. Loads dependencies, API client, geocoding helpers, ingredient list. |
| 5 | *Markdown instructions* — read only. |
| 6 | **Main run cell**. Edit `USER_ADDRESS` and `DISH_NAME` at the top, then run. |
| 7 | Displays cheapest store's itemised list in a formatted table. |

### Example

```
USER_ADDRESS = "Botany Town Centre, Auckland 2013"
DISH_NAME = "spaghetti bolognese"
```

Output:
- 3 stores found within 5 km (Botany, Highland Park, Ormiston)
- 7 ingredients searched at each store
- Cheapest: PAK'nSAVE Botany at $29.03

## Known Limitations

- **Unit sizes**: Prices shown for full units (e.g., whole kg of mince). A recipe may use less, so your actual cost is lower.
- **Garlic pricing**: Loose garlic is per-kg ($40+). Crushed garlic jar ($2–3) is more practical and sometimes returned instead.
- **Store density**: Auckland CBD has 1 store within 5 km. East Auckland (Botany/Manukau) has 3.
- **Woolworths fresh session per store**: Each nearby store requires a separate `requests.Session` — cannot reuse one session across stores.
- **Woolworths search relevance**: Generic terms like "garlic" or "mixed herbs" may return unrelated products (e.g., gravy mix for "herbs"). Ingredient queries need to be specific.
- **Woolworths per-store pricing differences are small for nearby stores**: Auckland stores show $0.00-$0.20 differences per ingredient. Differences are larger for distant stores (e.g., Greymouth vs Glenfield: $0.18 for 3L milk).
