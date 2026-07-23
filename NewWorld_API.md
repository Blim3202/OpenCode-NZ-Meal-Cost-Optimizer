# New World / Foodstuffs North Island Mobile API Documentation

**API origin:** `api-prod.prod.fsniwaikato.kiwi` — despite the "FSNI" (Foodstuffs North
Island) domain name, this API covers **all New World stores nationwide** including
both North Island (101 stores) and South Island (48 stores). It also works for
Pak'nSave with `banner: "PNS"`.

[Confirmed working](scripts/newworld/NewWorld_prototype.py): Auckland CBD stores
(Metro Auckland, Newmarket, Devonport, Remuera, Mt Albert, Point Chevalier,
Eastridge, Mt Roskill, Birkenhead, Stonefields, Shore City, Milford, New Lynn),
plus stores nationwide (Christchurch, Dunedin, Wellington, Nelson, etc.) all return
valid per-store pricing through the mobile API.

---

## 1. How This Documentation Was Discovered

The New World mobile API was first publicly documented by **[Arefu](https://github.com/Arefu)**
through reverse engineering the Foodstuffs Android app. Key sources:

- **[Foodstuffs PNS&NW Android App OpenAPI.yaml](https://github.com/Arefu/PaknSave/blob/main/_docs/Foodstuffs%20PNS%26NW%20Android%20App%20OpenAPI.yaml)** —
  Full OpenAPI 3.0.4 spec of the Foodstuffs North Island API, covering auth, stores,
  product search, cart, categories, and previous purchases.
- **[PaknSave.txt](https://gist.github.com/Arefu/b12d83a5dffb6573a1b1907044ad8de4)** —
  Early endpoint enumeration including the legacy `CommonApi` web endpoints and a
  PowerShell PoC for store listing and product exports.
- **[Arefu's GitHub profile](https://github.com/Arefu)** — Additional research on
  Foodstuffs API internals.

This document builds on Arefu's discovery to document every confirmed endpoint,
parameter, response shape, and edge case encountered during integration into this
project's meal cost optimizer. Where responses differ between the OpenAPI spec and
observed behaviour, both are noted.

The New World API is **identical in structure to the Pak'nSave API** — the only
differences are the `banner` value (`"MNW"` vs `"PNS"`) and the `User-Agent` header
(`NewWorldApp/4.32.0` vs `PAKnSAVEApp/4.32.0`). See [PaknSave_API.md](PaknSave_API.md)
for the full Pak'nSave documentation.

---

## 2. Base URL and Host

```
Base URL:   https://api-prod.prod.fsniwaikato.kiwi/prod
Pre-prod:   https://api-preprod.test.fsniwaikato.kiwi
QA:         https://api-qa.test.fsniwaikato.kiwi
Backend:    fsniwaikato.kiwi  (Foodstuffs North Island)
```

All endpoints below are relative to `/prod`.

---

## 3. Required Request Headers

### 3.1 Authentication Endpoint

The guest login endpoint requires only:

```
User-Agent:    NewWorldApp/4.32.0
Content-Type:  application/json
```

### 3.2 Authenticated Endpoints

After obtaining an `access_token`, all subsequent requests need both:

```
Authorization:  Bearer {token}
access_token:   {token}
User-Agent:     NewWorldApp/4.32.0
Content-Type:   application/json
```

**Note:** The `access_token` header is duplicated intentionally — the API inspects
both `Authorization` and the custom `access_token` header. Omitting either can
cause 401 errors.

---

## 4. Authentication Flow

### 4.1 Guest Login

New World uses a simple bearer-token auth model, identical to Pak'nSave. No user
account, no password, no OAuth — just a `POST` with a banner identifier:

```
POST /mobile/user/login/guest
```

#### Request body

```json
{"banner": "MNW"}
```

`banner` values:

| Value | Brand |
|-------|-------|
| `"PNS"` | Pak'nSave |
| `"MNW"` | New World |

If the body is omitted entirely, a New World token is returned by default.

#### Response (HTTP 200)

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer",
  "refresh_token": "eyJhbGciOiJSUzI1NiIs...",
  "expires_in": 1800,
  "scope": "openid email profile phone all offline_access"
}
```

| Field | Type | Notes |
|-------|------|-------|
| `access_token` | `string` | JWT bearer token, valid for 1800 seconds (30 minutes) |
| `refresh_token` | `string` | Used to obtain a new access_token without re-logging in |
| `expires_in` | `int` | Token TTL in seconds |
| `scope` | `string` | Rights granted to this token |

#### Token auto-refresh

The `NewWorldAPI` class in this project automatically refreshes expired tokens:

```python
class NewWorldAPI:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        self._token = None

    def _ensure_token(self):
        if self._token:
            return
        r = self.scraper.post(
            f"{BASE}/mobile/user/login/guest",
            json={"banner": "MNW"},
            headers={"User-Agent": "NewWorldApp/4.32.0", "Content-Type": "application/json"},
        )
        r.raise_for_status()
        data = r.json()
        self._token = data["access_token"]
        self._auth = {
            "Authorization": f"Bearer {self._token}",
            "access_token": self._token,
            "User-Agent": "NewWorldApp/4.32.0",
            "Content-Type": "application/json",
        }
```

The token expiry is 30 minutes. `_ensure_token()` is called on every API call —
if the token is already set, the call is a no-op. For long-running sessions, the
`refresh_token` endpoint (section 4.2) can be used.

### 4.2 Token Refresh

```
POST /mobile/v1/users/login/refreshtoken
```

#### Request headers

```
User-Agent: NewWorldApp/4.32.0
```

#### Request body

```json
{"refresh_token": "eyJhbGciOiJSUzI1NiIs..."}
```

#### Response (HTTP 200)

```json
{
  "accessToken": "eyJhbGciOiJSUzI1NiIs...",
  "refreshToken": "eyJhbGciOiJSUzI1NiIs..."
}
```

#### Response (HTTP 401 — expired/invalid)

```json
{
  "fields": null,
  "status": 401,
  "message": "Refresh token expired or invalid",
  "code": "NOT_SUPPORTED"
}
```

The refresh token approach is not currently used by this project — a new guest
login is issued instead when the token expires (which is simpler and avoids
refresh-token lifecycle management).

---

## 5. Confirmed Working Endpoints

### 5.1 `GET /mobile/store/physical`

Returns all physical stores for the banner encoded in the access token. This is the
primary source of store metadata: names, precise coordinates, addresses, opening hours,
and service flags.

**HTTP 200** — requires auth headers.

#### Response structure

Returns an object with a single `"stores"` key containing an array:

```json
{
  "stores": [
    {
      "id": "773ad0a0-024e-46c5-a94b-df1cf86d25cc",
      "name": "New World Albany",
      "banner": "MNW",
      "address": "219 Don McKinnon Drive, Albany, Auckland 0632",
      "clickAndCollect": true,
      "delivery": true,
      "latitude": -36.728207,
      "longitude": 174.710519,
      "openingHours": [ ... ],
      "phone": "09-441 8838",
      "localPhone": "09-441 8838",
      "linkDetails": { ... },
      "physicalStoreCode": "NW01",
      "region": "NI",
      "salesOrgId": "20",
      "onboardingMode": false,
      "defaultCollectType": "CONCIERGE",
      "expressTimeslots": true,
      "expressProductLimit": 35,
      "onlineActive": true,
      "physicalActive": true,
      "servicesAndFacilities": [ ... ],
      "physicalAddress": { ... },
      "deliverySubscriptionProperties": { ... }
    },
    ...
  ]
}
```

#### Key fields

| Field | Type | Notes |
|-------|------|-------|
| `id` | `string` (UUID) | Store identifier — used in all product/search endpoints |
| `name` | `string` | Full store name, e.g. `"New World Albany"` |
| `banner` | `string` | `"PNS"` or `"MNW"` |
| `address` | `string` | Full street address |
| `latitude` | `float` | Precise store latitude (not geocoded) |
| `longitude` | `float` | Precise store longitude (not geocoded) |
| `clickAndCollect` | `bool` | Supports click & collect |
| `delivery` | `bool` | Supports home delivery |
| `onlineActive` | `bool` | Available for online ordering |
| `physicalActive` | `bool` | Physical store open |
| `region` | `string` | `"NI"` (North Island) or `"SI"` (South Island) |
| `salesOrgId` | `string` | Sales organisation identifier |
| `defaultCollectType` | `string` | `"CONCIERGE"`, `"COUNTER"`, or `"LOCKER"` |
| `openingHours` | `array` | Daily opening/closing times |
| `physicalAddress` | `object` | Structured address fields (streetName, cityName, regionName, etc.) |

#### Store count

149 stores are currently returned for `banner="MNW"`. Each store has a UUID-style
`id` (e.g., `773ad0a0-024e-46c5-a94b-df1cf86d25cc`).

#### Usage in this project

```python
api = NewWorldAPI()
stores = api.get_stores()  # returns {id: store_dict}
```

The CSV at `data/newworld_stores.csv` is pre-built from the mobile API + store-finder
page, containing the same `store_id` UUIDs with name, address, lat, lon, url, and
service flags for all 149 stores.

### 5.2 `POST /mobile/ecomm-products/{banner}/{storeId}/search?q={query}`

The primary product search endpoint. Returns relevant products for a given query at a
specific store, **with per-store pricing**.

**HTTP 200** — requires auth headers.

#### Path parameters

| Parameter | Type | Example |
|-----------|------|---------|
| `banner` | `string` | `"MNW"` |
| `storeId` | `string` (UUID) | `"773ad0a0-024e-46c5-a94b-df1cf86d25cc"` |

#### Query parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | `string` | (required) | Search query, e.g. `"beef mince"` |
| `sortOrder` | `string` | (relevance) | Sort by relevance or price |
| `searchingTobacco` | `bool` | `false` | If the search is for tobacco products |
| `disableAdsOverride` | `bool` | `false` | Disable ad insertion in results |

#### Request body

Send an empty JSON array:

```json
[]
```

The body is required but can be empty — it's used internally for filter state
(e.g., dietary/lifestyle filters). An empty array means "no filters".

#### Response structure

```json
{
  "tobaccoFiltered": false,
  "totalHits": 10,
  "hitsPerPage": 20,
  "numberOfPages": 1,
  "page": 1,
  "products": [
    {
      "productId": "c9b5f8e2-...",
      "brand": "Pams",
      "name": "NZ Beef Mince",
      "units": "kg",
      "categories": ["Meat & Poultry", "Beef", "Mince"],
      "price": 1899,
      "unitPrice": "$18.99/kg",
      "productImageUrls": {
        "100": "https://...",
        "200": "https://...",
        "400": "https://...",
        "500": "https://..."
      },
      "decalCode": "club",
      "decalImageUrl": "https://...",
      "availableInStore": true,
      "availableInOnline": true,
      "tobaccoFlag": false,
      "liquorFlag": false,
      "saleType": "standard",
      "algoliaAnalytics": {
        "searchQueryID": "abc123",
        "searchPosition": 1
      },
      "boughtBefore": false,
      "badgeSmallUrl": null,
      "badgeMediumUrl": null,
      "badgeLargeUrl": null
    },
    ...
  ],
  "filters": {
    "Deals": {},
    "Dietary & lifestyle": {},
    "Categories": {
      "Meat & Poultry": 175,
      "Beef": 42,
      ...
    },
    "Brands": {
      "Pams": 5,
      ...
    }
  }
}
```

#### Product fields

| Field | Type | Notes |
|-------|------|-------|
| `productId` | `string` (UUID) | Unique product identifier across all stores |
| `name` | `string` | Product display name |
| `brand` | `string` | Brand name (e.g. `"Pams"`, `"Value"`) |
| `price` | `integer` | **Price in cents** — divide by 100 for dollars |
| `units` | `string` | Unit of sale: `"kg"`, `"L"`, `"400g"`, `"12pk"`, `"each"` |
| `unitPrice` | `string` | Formatted unit price string, e.g. `"$18.99/kg"` |
| `categories` | `array[string]` | Hierarchical category path, e.g. `["Meat & Poultry", "Beef", "Mince"]` |
| `availableInOnline` | `bool` | Can be ordered online |
| `availableInStore` | `bool` | In stock at this store |
| `saleType` | `string` | `"standard"`, `"special"`, `"club"` |
| `tobaccoFlag` | `bool` | Is a tobacco product |
| `liquorFlag` | `bool` | Is an alcohol product |

#### Price handling

**Critical: prices are in cents.** Always divide `price` by 100:

```python
price_dollars = product["price"] / 100
```

#### Per-store pricing

Each `{storeId}` returns independent prices for the same product. For example,
searching "standard milk" at New World Albany vs New World Newmarket may return
different `price` values for the same `productId`. This is the foundation of the
meal cost optimizer.

#### Pagination

| Field | Description |
|-------|-------------|
| `page` | Current page (1-indexed) |
| `hitsPerPage` | Items per page (default 20) |
| `numberOfPages` | Total page count |
| `totalHits` | Total matching products |

All results are returned in a single page for typical ingredient searches
(which usually return 1-20 results).

#### Specifying sort order

Add `sortOrder` to the query string:

```
POST .../search?q=beef+mince&sortOrder=PriceAsc
```

`sortOrder` values are not fully documented but known to accept `"PriceAsc"`.

### 5.3 `POST /mobile/ecomm-products/{banner}/{storeId}/specials`

Returns products currently on special at a specific store. Supports filtering by
deal category.

**HTTP 200** — requires auth headers.

#### Path parameters

| Parameter | Type | Notes |
|-----------|------|-------|
| `banner` | `string` | `"PNS"` or `"MNW"` |
| `storeId` | `string` (UUID) | Store identifier |

#### Query parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `sortOrder` | `string` | Sort order for results |

#### Request body

An array of filter objects. Each object has a `title` (filter group name) and
`items` (array of filter values). An empty array returns all specials:

```json
[]
```

To filter by deal category:

```json
[
  {
    "title": "Deals",
    "items": ["Super Specials"]
  }
]
```

#### Response structure

Same product array format as search/specials.

#### Known deal types (observed)

| Filter value | Description |
|-------------|-------------|
| `"Super Specials"` | Deep-discount limited-time deals |
| `"Weekly Specials"` | Standard weekly catalogue specials |

### 5.4 `GET /mobile/v1/products/category`

Returns the hierarchical product category tree for a specific store.

**HTTP 200** — requires auth headers.

#### Query parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `storeId` | `string` (UUID) | Store identifier |
| `banner` | `string` | `"PNS"` or `"MNW"` |
| `region` | `string` | Region code (e.g. `"NI"`) |

#### Response structure

Same category tree format as Pak'nSave.

### 5.5 `GET /mobile/v1/products/category` (Browse by category path)

Returns products for a specific category path within a store.

Same parameters and response format as Pak'nSave.

---

## 6. Endpoints That Do NOT Work (New World Edge API)

The New World website at `www.newworld.co.nz` exposes an Edge API at
`api-prod.newworld.co.nz`. This API requires JWT bearer token authentication
that cannot be obtained without proper credentials.

| Endpoint | Method | Status |
|----------|--------|--------|
| `https://api-prod.newworld.co.nz/v1/edge/store/physical` | GET | **401** — `Failed to Resolve Variable : policy(JWT-VerifyRetailEdgeToken) variable(null)` |

**Why the mobile API is preferred:**

1. **No JWT auth required** — mobile API uses simple guest token (banner-based)
2. **Same data coverage** — all 149 New World stores with coordinates and IDs
3. **Per-store pricing** — mobile API returns prices per-store natively
4. **More data per product** — mobile API returns `productImageUrls`, `unitPrice`,
   `algoliaAnalytics`, `brand`, `availableInOnline`, flag fields

The Edge API was tested with various header combinations (`x-requested-with`,
`x-api-key`, `referer`, `accept`) — all failed with 401. It requires a JWT token
that is only available through authenticated sessions (user login).

---

## 7. Per-Store Pricing

### 7.1 How It Works

The New World mobile API provides **true per-store pricing**. Each store has its own
price list for every product identified by its unique `productId`. When you search
for "beef mince" at store A vs store B, the prices returned are that store's current
prices.

This is in contrast to the Woolworths API, which requires cookie injection for
per-store pricing — New World (like Pak'nSave) encodes the store context directly
in the URL path:

```
POST /mobile/ecomm-products/MNW/{storeId}/search?q=beef+mince
```

No special headers, cookies, or session setup beyond the bearer token is needed.

### 7.2 Observed Price Variation

Price differences between nearby stores are common. For example, a search for
"spaghetti bolognese" ingredients across 13 Auckland stores showed:

| Store | Total Cost | Distance |
|-------|-----------|----------|
| New World Shore City | $23.53 | 7.4 km |
| New World Metro Auckland | $49.13 | 0.9 km |
| New World Newmarket | $63.63 | 2.3 km |
| New World Milford | $63.63 | 9.1 km |
| New World Birkenhead | $78.03 | 6.6 km |
| New World Stonefields | $86.63 | 7.3 km |

Differences of $0.10-$0.50 per item between nearby stores are typical. For example:
- Beef mince: $9.49 (Shore City) vs $26.99 (Metro Auckland)
- Garlic: $4.49 (Shore City) vs $52.99 (Stonefields)

**Note: this simple calculation has differences due to per-store availibility rather than per-store pricing.**

### 7.3 Why This Matters

The meal cost optimizer finds the cheapest total for an entire recipe by searching
each ingredient at each nearby store and comparing totals. Without per-store pricing,
this comparison would be meaningless.

---

## 8. Store Data Sources

### 8.1 Primary: Mobile API (`GET /mobile/store/physical`)

149 stores with precise coordinates. This is the most accurate source and provides
all data needed for the optimizer (store_id, name, address, lat/lon, banner,
clickAndCollect, delivery).

```python
api = NewWorldAPI()
api_stores = api.get_stores()  # returns {id: store_dict}
```

### 8.2 CSV (`data/newworld_stores.csv`)

Pre-built from the mobile API + store-finder page, containing the same `store_id`
UUIDs with name, address, lat, lon, url, and service flags for all 149 stores.

```csv
store_id,name,url,address,latitude,longitude,banner,click_and_collect,delivery
773ad0a0-...,New World Albany,/upper-north-island/auckland/albany,"219 Don McKinnon Drive...",-36.728207,174.710519,MNW,True,True
```

### 8.3 Store URLs from Store-Finder Page

The store-finder page at `https://www.newworld.co.nz/store-finder` provides URL
slugs for 150 stores (142 match the API). The `__NEXT_DATA__` JSON path is:

```
data.props.pageProps.page.page_content.content_blocks[1].store_finder.regionStoreGroupings
```

→ `northIsland`/`southIsland` → `groups` → `stores` → each with `title`, `url`, `address`

### 8.4 Build Pipeline (`scripts/newworld/fetch_stores.py`)

```
fetch_stores.py
  → POST /mobile/user/login/guest (banner: "MNW")
  → GET /mobile/store/physical → 149 stores with UUID, name, address, lat/lon, banner
  → GET https://www.newworld.co.nz/store-finder → parse __NEXT_DATA__
  → Extract store_finder.regionStoreGroupings: title, url, address per store
  → Join on name (strip "New World " prefix) → DataFrame → data/newworld_stores.csv
```

No geocoding required — coordinates are provided directly by the mobile API.

---

## 9. Production Architecture

### 9.1 How to Search Products by Store

```python
import cloudscraper
import math
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', 'data'))

BASE = "https://api-prod.prod.fsniwaikato.kiwi/prod"

class NewWorldAPI:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        self._token = None

    def _ensure_token(self):
        if self._token:
            return
        r = self.scraper.post(
            f"{BASE}/mobile/user/login/guest",
            json={"banner": "MNW"},
            headers={"User-Agent": "NewWorldApp/4.32.0", "Content-Type": "application/json"},
        )
        r.raise_for_status()
        self._token = r.json()["access_token"]
        self._auth = {
            "Authorization": f"Bearer {self._token}",
            "access_token": self._token,
            "User-Agent": "NewWorldApp/4.32.0",
            "Content-Type": "application/json",
        }

    def search_products(self, store_id: str, query: str):
        self._ensure_token()
        r = self.scraper.post(
            f"{BASE}/mobile/ecomm-products/MNW/{store_id}/search?q={query}",
            headers=self._auth, json=[],
        )
        if r.status_code == 200:
            return r.json()
        return None

    def get_stores(self):
        self._ensure_token()
        r = self.scraper.get(f"{BASE}/mobile/store/physical", headers=self._auth)
        if r.status_code == 200:
            return {s["id"]: s for s in r.json()["stores"] if s.get("banner") == "MNW"}
        return {}
```

### 9.2 How to Find Nearby Stores and Compare Prices

```python
import pandas as pd
import requests

# Load store data
stores_csv = pd.read_csv(os.path.join(DATA_DIR, "newworld_stores.csv"))

# Geocode user address via Nominatim
def geocode(address):
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        headers={"User-Agent": "NZMealCostOptimizer/1.0"},
        params={"q": address, "format": "json", "limit": 1},
    )
    if r.status_code == 200 and r.json():
        loc = r.json()[0]
        return float(loc["lat"]), float(loc["lon"])
    return None, None

# Haversine distance
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))

# Filter stores within radius
def find_nearby(user_lat, user_lon, radius_km=5):
    df = stores_csv.copy()
    df["distance_km"] = df.apply(
        lambda r: haversine(user_lat, user_lon, r["latitude"], r["longitude"]),
        axis=1,
    )
    return df[df["distance_km"] <= radius_km].sort_values("distance_km")

# Search a single ingredient
def search_ingredient(api, store_id, ingredient):
    results = api.search_products(store_id, ingredient)
    if not results:
        return None
    products = results.get("products", [])
    if not products:
        return None
    p = products[0]
    price_cents = p.get("price")
    if price_cents is None or price_cents <= 0:
        return None
    return {
        "name": p["name"],
        "brand": p.get("brand", ""),
        "price": price_cents / 100,
        "units": p.get("units", ""),
    }

# Full pipeline
api = NewWorldAPI()
user_lat, user_lon = geocode("123 Queen Street, Auckland CBD, 1010")
nearby = find_nearby(user_lat, user_lon, radius_km=5)

for _, store in nearby.iterrows():
    store_id = store["store_id"]
    store_name = store["name"]
    total = 0.0
    print(f"--- {store_name} ---")
    for ingredient in ["beef mince", "spaghetti pasta", "canned tomatoes"]:
        result = search_ingredient(api, store_id, ingredient)
        if result:
            print(f"  {ingredient:25s} ${result['price']:.2f}  {result['name']}")
            total += result["price"]
        else:
            print(f"  {ingredient:25s}  NOT FOUND")
    print(f"  {'TOTAL':25s} ${total:.2f}\n")
```

### 9.3 Ingredient Search Strategy

The optimizer takes the **first (most relevant)** result per query. This avoids
irrelevant bulk items that might appear at lower prices (e.g., pet food for
"beef mince"). 21 dishes are hand-curated in `DISH_INGREDIENTS` — no NLP/LLM
parsing.

### 9.4 Architecture Diagram

```
newworld_stores.csv  (149 stores with UUID, name, lat, lon)
  |
  +---> haversine filter (user address → lat/lon → nearby stores within 5 km)
  |
  v
FOR EACH nearby store:
  1. NewWorldAPI().search_products(store_id, ingredient)
  2. products[0]["price"] / 100  →  price in dollars
  3. Sum across all ingredients
  |
  v
Compare totals → cheapest store
```

---

## 10. Supported Dishes (21)

| Dish | Ingredients |
|------|------------|
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
| lamb chops | lamb chops, potato, mint sauce, mixed vegetables |
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

Dishes are defined in `DISH_INGREDIENTS` in `scripts/newworld/NewWorld_prototype.py`.
Unknown dish names fall through — the dish name itself becomes the single search query.

---

## 11. CLI Usage

```powershell
python scripts/newworld/NewWorld_prototype.py "123 Queen Street, Auckland CBD, 1010" "spaghetti bolognese"
```

| Argument | Default | Description |
|----------|---------|-------------|
| `address` | `"123 Queen Street, Auckland CBD, 1010"` | NZ address to geocode |
| `dish` | `"spaghetti bolognese"` | Dish name from the supported list |

Output: per-store itemised prices, total cost comparison, and the cheapest store.

---

## 12. Summary of API Capabilities

| Capability | Available via API? | Method |
|-----------|-------------------|--------|
| Guest authentication | [OK] Yes | `POST /mobile/user/login/guest` |
| Token refresh | [OK] Yes | `POST /mobile/v1/users/login/refreshtoken` |
| List all physical stores (149) | [OK] Yes | `GET /mobile/store/physical` |
| Search products by keyword | [OK] Yes (per-store) | `POST .../search?q=<term>` |
| Browse products by category | [OK] Yes | `GET /mobile/v1/products/category` |
| Get store specials | [OK] Yes | `POST .../specials` |
| Get product categories | [OK] Yes | `GET /mobile/v1/products/category` |
| Per-store pricing | [OK] YES (native, no cookie tricks) | Store ID in URL path |
| View cart / trolley | [WARN] Requires user auth | `GET /mobile/cart` |
| View previous purchases | [WARN] Requires user auth | `POST /mobile/previousPurchases` |
| Get hierarchical category tree | [OK] Yes | `GET /mobile/v1/products/category?storeId=...` |
| App upgrade check | [OK] Yes | `POST /mobile/v1/upgrade` |
| Error code lookup | [OK] Yes | `GET /mobile/v1/error` |
| New World Edge API | [FAIL] JWT required | `https://api-prod.newworld.co.nz/v1/edge/store/physical` |

---

## 13. Key Gotchas

1. **Prices are in cents** — Always divide `price` by 100 for dollars. A `price` of
   `1899` means $18.99.
2. **Token expires after 30 minutes** — The `access_token` has `expires_in: 1800`.
   The `_ensure_token()` method auto-refreshes, but long-running scripts may need
   explicit refresh handling.
3. **Two header slots for the token** — The API inspects both `Authorization: Bearer`
   and the custom `access_token` header. Both must be set.
4. **Empty JSON body required** — The `search` endpoint requires `[]` as the request
   body. Omitting it or sending `null` may cause errors.
5. **Search returns relevance, not cheapest** — Results are sorted by relevance
   (Algolia-powered). Always take `products[0]` for the most relevant match.
6. **Per-store pricing is native** — Unlike Woolworths, no cookie tricks or fresh
   sessions are needed. The store ID is in the URL path.
7. **`cloudscraper` is NOT required for the API domain** — The mobile API domain
   (`api-prod.prod.fsniwaikato.kiwi`) has no Cloudflare protection. However, the
   website domain (`www.newworld.co.nz`) does. The project uses `cloudscraper` for
   consistency.
8. **The OpenAPI spec is not fully accurate** — `GET /mobile/store/physical` returns
   `{"stores": [...]}` not a bare array as the spec suggests. Actual response shapes
   were verified against live API calls.
9. **Nominatim rate limit: 1 req/sec** — Geocoding is done through Nominatim
   (OpenStreetMap) with a 1 request per second rate limit.
10. **Store names from web vs API** — The CSV store names may differ slightly from
    the API's store names (e.g., `"New World Albany"` vs `"New World Albany"` —
    casing and prefix differences). The API names are authoritative.
11. **149 stores total** — All New World stores nationwide. UUID format `store_id`
    strings are consistent across API and web data sources.
12. **New World Edge API requires JWT** — The `api-prod.newworld.co.nz/v1/edge/store/physical`
    endpoint returns 401 with JWT verification error. Not usable without proper auth.
13. **User-Agent must match banner** — Use `NewWorldApp/4.32.0` for New World
    (`banner: "MNW"`), not `PAKnSAVEApp/4.32.0`.
14. **7 stores missing URLs** — After merging mobile API data with store-finder page
    data, 7 stores have no URL match due to name mismatches (e.g., "Metro Auckland"
    vs "Metro Queen Street", macron differences for Tūrangi/Wanaka). URLs are only
    used for linking to the website, not for the API-based optimizer.
15. **1 store discrepancy** — The store-finder page has 150 stores; the mobile API
    returns 149. "Foodie Mart" (Mangere) appears in the API but not on the page.

---

## 14. Comparison: New World vs Pak'nSave vs Woolworths

| Feature | New World | Pak'nSave | Woolworths |
|---------|-----------|-----------|------------|
| Auth | Bearer token (guest login) | Bearer token (guest login) | Session cookies (no login) |
| Token/ session expiry | 30 min (auto-refreshable) | 30 min (auto-refreshable) | Indefinite (observed weeks) |
| Per-store pricing | Native (store ID in URL) | Native (store ID in URL) | Cookie injection (`cw-lrkswrdjp`) |
| Fresh session per store | Not required | Not required | Required (server resets cookies) |
| Product search | `POST` with JSON body | `POST` with JSON body | `GET` with query params |
| Prices in | Cents (integer) | Cents (integer) | Dollars (float) |
| Cloudflare | API domain: none, Website: Cloudflare | API domain: none, Website: Cloudflare | No Cloudflare on API |
| Store count | 149 | 60 | 183 (Woolworths NZ) |
| Auth complexity | Low (2 POST calls) | Low (2 POST calls) | Medium (cookie construction) |
| Banner value | `"MNW"` | `"PNS"` | N/A |
| User-Agent | `NewWorldApp/4.32.0` | `PAKnSAVEApp/4.32.0` | N/A |

---

## 15. Exploration Scripts

| Script | Purpose |
|--------|---------|
| `scripts/newworld/NewWorld_prototype.py` | CLI entry point: geocode, nearby stores, per-store search, cost comparison |
| `scripts/newworld/fetch_stores.py` | One-shot data builder: fetches stores from mobile API + store-finder page URLs |
| `scripts/paknsave/fetch_stores.py` | Reference: Pak'nSave store data builder (same API pattern) |

---

## 16. Files and Data Sources

| File | Purpose |
|------|---------|
| `NewWorld_API.md` | This document |
| `AGENTS.md` | Project overview, file structure, key gotchas |
| `design.md` | Technical design (API, auth, pipeline for both chains) |
| `data/newworld_stores.csv` | 149 stores: store_id (UUID), name, url, address, latitude, longitude, banner, click_and_collect, delivery |
| `scripts/newworld/NewWorld_prototype.py` | CLI optimizer with `NewWorldAPI` class, `DISH_INGREDIENTS`, geocoding, haversine |
| `scripts/newworld/fetch_stores.py` | Store data builder from mobile API + store-finder page |
| `PaknSave_API.md` | Full Pak'nSave API documentation (identical structure) |

---

## 17. Credits

This documentation builds on the foundational reverse-engineering work of
**[Arefu](https://github.com/Arefu)**, who first documented the Foodstuffs
mobile API endpoints:

- **[Foodstuffs PNS & NW Android App OpenAPI YAML](https://github.com/Arefu/PaknSave/blob/main/_docs/Foodstuffs%20PNS%26NW%20Android%20App%20OpenAPI.yaml)**
  — Full OpenAPI 3.0.4 spec from Arefu's [PaknSave GitHub repo](https://github.com/Arefu/PaknSave)
- **[FSNS_API.yaml Gist](https://gist.github.com/Arefu/b94ea1942c7fa898c2e473a75c5c67cf)**
  — Earlier OpenAPI spec covering authentication, stores, product search, cart, categories
- **[PaknSave.txt Gist](https://gist.github.com/Arefu/b12d83a5dffb6573a1b1907044ad8de4)**
  — Early endpoint enumeration including legacy `CommonApi` web endpoints
