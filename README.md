# NZ Meal Cost Optimizer

Finds the cheapest Pak'nSave, New World, or Woolworths for a given dish by comparing ingredient prices across nearby stores (within 5 km of a NZ address).

## How It Works

1. Geocode address to lat/lon (Nominatim)
2. Filter stores within 5 km (Haversine)
3. Map dish to ingredients (21 hand-curated dishes)
4. Search each ingredient at each store via API
5. Compare totals, display cheapest

## Supported Stores

| Store | API | Stores | Per-Store Pricing | Status |
|-------|-----|--------|-------------------|--------|
| Pak'nSave | Edge API (two-pass) | 57 | Yes | Production-ready |
| New World | Edge API (two-pass) | 148 | Yes | Production-ready |
| Woolworths | REST API (cookie injection) | 183 | Yes | Production-ready |

## Quick Start

```powershell
# Setup
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run optimizer
python scripts/paknsave/PaknSave_prototype.py "Botany, Auckland" "spaghetti bolognese"
python scripts/newworld/NewWorld_prototype.py "Botany, Auckland" "spaghetti bolognese"
python scripts/woolworths/woolworths_optimizer.py "Botany, Auckland" "spaghetti bolognese"
```

## Architecture

### Pak'nSave / New World (Edge API Two-Pass Pipeline)

Both use the same Foodstuffs backend with identical API structure:

```
GET website → POST get-current-user → JWT token
  → FOR EACH store:
    → FOR EACH ingredient:
      PASS 1: POST /search/products/query/index/products-index
        → Extract productIDs with relevance matches
      PASS 2: POST /search/paginated/products (with filters)
        → Returns per-store pricing
```

**Key differences:**
- Pak'nSave: 57 stores, requires pet food filtering via `category1`
- New World: 148 stores, no pet food filtering needed

### Woolworths (Cookie-Based)

```
GET / → session cookies
  → Construct cw-lrkswrdjp cookie from store data
  → FOR EACH store:
    → Fresh session per store (required)
    → Search /api/v1/products?target=search
```

## Project Structure

```
opencode/
├── data/
│   ├── paknsave_stores.csv           # 60 stores (mobile API)
│   ├── newworld_stores.csv           # 149 stores (mobile API)
│   └── woolworths_store_data.csv     # 183 stores
├── scripts/
│   ├── paknsave/
│   │   ├── PaknSave_prototype.py     # CLI optimizer
│   │   ├── fetch_stores.py           # Build store data
│   │   └── Exploration/              # Edge API development
│   ├── newworld/
│   │   ├── NewWorld_prototype.py     # CLI optimizer
│   │   ├── fetch_stores.py           # Build store data
│   │   └── Exploration/              # Edge API development
│   └── woolworths/
│       ├── woolworths_optimizer.py   # CLI optimizer
│       ├── woolworths_api.py         # API module
│       └── Exploration/              # API development
├── notebooks/                        # Jupyter prototypes
├── PaknSave_API.md                   # Pak'nSave API docs
├── NewWorld_API.md                   # New World API docs
├── Woolworths_API.md                 # Woolworths API docs
├── design.md                         # Technical design
├── decision.md                       # Key decisions
└── logs.md                           # Error log
```

## Dish Coverage

21 hand-curated dishes with mapped ingredients:

| Dish | Ingredients |
|------|-------------|
| Spaghetti Bolognese | beef mince, spaghetti pasta, canned tomatoes, onion, carrot, garlic, mixed herbs |
| Butter Chicken | chicken breast, butter chicken sauce, rice, cream, onion |
| Chicken Stir Fry | chicken breast, stir fry vegetables, soy sauce, rice noodles |
| Fish and Chips | fish fillets, potatoes, flour, oil |
| Pumpkin Soup | pumpkin, onion, cream, stock, bread |
| ... | (17 more dishes) |

Full list in `design.md` or `DISH_INGREDIENTS` in prototype scripts.

## API Reference

### PaknSave Edge API

- **Base URL**: `https://api-prod.paknsave.co.nz/v1/edge`
- **Auth**: Website JWT (`fs-user-token` cookie)
- **Store context**: `eCom_STORE_ID`, `STORE_ID_V2`, `Region` cookies
- **Endpoints**: See `PaknSave_API.md` section 6

### New World Edge API

- **Base URL**: `https://api-prod.newworld.co.nz/v1/edge`
- **Auth**: Website JWT (`fs-user-token` cookie)
- **Store context**: `eCom_STORE_ID`, `STORE_ID_V2`, `Region` cookies
- **Endpoints**: See `NewWorld_API.md` section 6

### Woolworths API

- **Base URL**: `https://www.woolworths.co.nz`
- **Auth**: Session cookies (no login required)
- **Store context**: `cw-lrkswrdjp` cookie (constructed from store data)
- **Endpoints**: See `Woolworths_API.md`

## Limitations

- **Unit sizes**: Prices shown for full units (e.g., whole kg of mince)
- **Garlic pricing**: Loose garlic is per-kg ($40+); crushed garlic jar ($2-3) returned instead
- **Store density**: Auckland CBD has 1 store within 5 km; East Auckland has 3
- **Woolworths sessions**: Each store requires a fresh `requests.Session`
- **Search relevance**: Generic terms may return unrelated products; be specific

## Disclaimer

This is an experimental, personal project. Not affiliated with or endorsed by Pak'nSave, New World, Woolworths, or any supermarket chain. Functionality depends on API stability; endpoints may change without notice.