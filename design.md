# Technical Design

## Architecture Overview

```
User input (address + dish)
  → Nominatim geocode (lat/lon)
  → Haversine filter (stores within 5 km)
  → Dish name → ingredient list (DISH_INGREDIENTS map)
  → Foodstuffs mobile API: search each ingredient at each nearby store
  → Aggregate prices, compare totals, display cheapest
```

## Foodstuffs Mobile API

Base URL: `https://api-prod.prod.fsniwaikato.kiwi/prod`

### Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/mobile/user/login/guest` | POST | Guest auth. Body: `{"banner": "PNS"}` |
| `/mobile/store/physical` | GET | List all 60 stores (needs auth headers) |
| `/mobile/ecomm-products/PNS/{storeId}/search?q={query}` | POST | Search products. Body: `[]` |

### Auth Flow

1. POST to `/mobile/user/login/guest` with `{"banner": "PNS"}` and `User-Agent: PAKnSAVEApp/4.32.0`
2. Response contains `access_token` (valid 1800s / 30 min)
3. All subsequent requests need both headers:
   - `Authorization: Bearer {token}`
   - `access_token: {token}`
4. Token is auto-refreshed by `PaknSaveAPI._ensure_token()` when expired

### Product Search Response

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

### Store Data Sources

1. **Mobile API** (`/mobile/store/physical`): 60 stores, precise coords, accurate names. Returns `{"stores": [...]}`.
2. **CSV fallback** (`data/paknsave_stores.csv`): pre-built from `__NEXT_DATA__` + Nominatim geocoding. Same `store_id` UUIDs as API.
3. **Slug mapping** (`data/paknsave_store_slugs.csv`): maps URL slugs to store GUIDs (from `__NEXT_DATA__` contentstackStores).

## Geocoding

- **Provider**: Nominatim (OpenStreetMap) — free, no API key
- **Rate limit**: 1 request/second
- **Endpoint**: `https://nominatim.openstreetmap.org/search?q={address}&format=json&limit=1`
- **User-Agent**: `NZMealCostOptimizer/1.0` (required by Nominatim ToS)

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
python scripts/prototype.py "Botany Town Centre, Auckland" "spaghetti bolognese"
```

Args: `[address] [dish name]`. Defaults to "123 Queen Street, Auckland CBD" and "spaghetti bolognese".

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
