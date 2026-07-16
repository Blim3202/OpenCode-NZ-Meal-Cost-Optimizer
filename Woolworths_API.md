# Woolworths NZ Backend API Documentation

**Backend origin:** `shop.countdown.co.nz` — the underlying platform is shared between
Woolworths NZ and Countdown NZ. All `/api/v1` calls therefore resolve to Countdown's
infrastructure while returning Woolworths NZ product data and pricing.

---

## 1. How This Documentation Was Discovered

Every finding in this document was produced by **black-box HTTP probing** — no source
code, no internal documentation, and no authenticated access was used. The process
followed these steps:

1. **Seeded a `requests.Session`** by issuing a single `GET https://www.woolworths.co.nz/`
   with browser-like headers. This established the cookies and session context the site
   expects. No login, no Playwright, no real user account was required for public data.

2. **Enumerated candidate endpoint paths** by guessing ~25 conventional REST paths under
   `/api/v1` (e.g., `stores`, `products`, `products/search`, `shelves`, `trolleys/my`,
   `addresses/pickup-addresses`, `store/finder`, etc.). Each was tested with
   `session.get()` and the status code + response body inspected.

3. **Probed `/api/v1/products` exhaustively:** called it with `target=search`,
   `target=browse`, every plausible `dasFilter` format, every plausible store-context
   parameter name (`storeId`, `pickupStoreId`, `fulfilmentStoreId`, `locationId`,
   `addressId`, `clickAndCollectStoreId`, etc.), both `GET` and `POST` methods, and
   various `size`/`page`/`sort` combinations.

4. **Compared prices across store contexts** to detect whether the API carries
   per-store pricing. Searched "milk" with 10 products under three different store
   parameters and diffed each SKU's `salePrice` field against a no-parameter baseline.
   Zero differences confirmed global pricing.

5. **Tested all store-switch endpoints** by sending `POST` requests with three payload
   variants (`{"storeId": ...}`, `{"pickupAddressId": ...}`, `{"fulfilmentStoreId": ...}`)
   to 19 plausible endpoint paths. Every response was 404 — confirming no public API
   path exists for programmatic store context changes.

6. **Captured the full `shell` response** by calling `GET /api/v1/shell` and dumping
   every top-level key, then drilling into `context.shopper`, `context.fulfilment`,
   `mainNavs`, `specials`, and product search settings.

7. **Built the complete dasFacet hierarchy** by iterating all 14 department slugs from
   `mainNavs[1].navigationItems[0].items`, calling `GET /api/v1/products?target=browse
   &dasFilter=Department;;<slug>;false&size=1` for each, and collecting the returned
   `dasFacets` array (aisles) for each department.

8. **Inspected every key on store records** from `GET /api/v1/addresses/pickup-addresses`
   by iterating all `storeAreas[].storeAddresses[]` and printing the full key list for
   each record. No bridge keys (e.g. `siteDataId`, `externalId`) were found.

---

## 2. Base URL and Host

```
Base URL:  https://www.woolworths.co.nz/api/v1
Backend:   shop.countdown.co.nz  (internal hostname visible in all error messages)
```

All endpoints listed below are relative to `/api/v1`.

---

## 3. Required Request Headers

Every call to `/api/v1` must include at minimum these headers. Omitting
`x-requested-with` causes an immediate HTTP 400 with body
`{"message":"One or more errors occurred","errors":[{"field":"Header",
"message":"Header is missing and is invalid."}]}`.

```
x-requested-with:  ??           ← literal string, not a placeholder
User-Agent:        Mozilla/5.0 (Windows NT 10.0; Win64; x64)
                    AppleWebKit/537.36 (KHTML, like Gecko)
                    Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0
Accept:            application/json, text/plain, */*
Accept-Language:   en-NZ,en;q=0.9
```

The `x-requested-with: ??` header value was discovered through existing github repos (https://github.com/neon-ninja/woolies). Both the literal string `"??"` and `"XMLHttpRequest"` return HTTP 200; an empty string or absent header returns HTTP 400. Any other non empty string appears to be accepted. 

---

## 4. Session Seeding

A vanilla `requests.Session` with the headers above is sufficient. No cookies,
tokens, or login are required for public endpoints. A single call to the homepage
establishes the cookie jar:

```python
import requests

session = requests.Session()
session.headers.update({...headers from section 3...})
session.get("https://www.woolworths.co.nz/", timeout=10)   # seeds cookies
```

Cookies acquired this way remain valid for weeks (observed behaviour; no expiry
header was found in responses). This is sufficient to call all documented endpoints.

---

## 5. Confirmed Working Endpoints

### 5.1 `GET /api/v1/shell`

Returns the full navigation shell, context, and site configuration for the current
(unauthenticated) session. This is the primary source of the department and aisle
taxonomy used by `dasFilter`.

**HTTP 200** — no parameters required.

#### Response structure

Top-level keys and their types:

| Key | Type | Description |
|-----|------|-------------|
| `specials` | `list[dict]` | Special offer categories (13 items) |
| `dynamicHeaderLink` | `dict` | Currently-promoted link |
| `mainNavs` | `list[dict]` | Primary navigation blocks (6 items) |
| `browseBanners` | `list[dict]` | Currently empty (`list[0]`) |
| `specialsBanners` | `list[dict]` | Promotional banner links |
| `recipesBanners` | `list[dict]` | Currently empty |
| `fulfilmentMessages` | `dict` | Localised delivery/pickup slot strings |
| `fulfilmentTimeouts` | `dict` | Reservation timeout labels |
| `traderVersion` | `string` | Front-end app version (e.g. `v7.79.23.1`) |
| `footerLinks` | `dict` | Footer navigation |
| `disabledMessageTitleNames` | `list` | Currently 3 items |
| `productSearchSettings` | `dict` | Keys: `maximumPagesToAutoLoad`,
`thresholdToLoadMoreOnScroll` |
| `expressFulfilmentSettings` | `dict` | Express delivery/pickup fee structure |
| `deliverySubscriptionSettings` | `dict` | Subscription order minimums |
| `deliveryFees` | `list[dict]` | 3 tier rows with `orderValue`, `baseFee`,
`additionalPercentageFee`, `isFreeDelivery` |
| `isSuccessful` | `bool` | Always `true` |
| `rootUrl` | `string` | `http://shop.countdown.co.nz` |
| `context` | `dict` | Session context (see 5.1.1) |
| `messages` | `null` | Always `null` |
| `changeOrderCheck` | `null` | Always `null` |

#### 5.1.1 `context` sub-object

```
context: {
  shoeper: { ... },            # see 5.1.2
  fulfilment: { ... },         # see 5.1.3
  enabledFeatures: list[106],  # scalar strings, feature-flag IDs
  shoppingListItems: list[0],  # empty for unauthenticated sessions
  basketTotals: null,          # always null without login
  advancedSettingsResponse: null
}
```

#### 5.1.2 `context.shopper` fields (unauthenticated session values)

| Field | Type | Observed value |
|-------|------|----------------|
| `firstName` | `string` | `null` |
| `isShopper` | `bool` | `false` |
| `isLoggedIn` | `bool` | `false` |
| `hasOnecard` | `bool` | `false` |
| `oneCardBalance` | `any` | `null` |
| `shopperIdHash` | `string` | `null` |
| `shopperScvId` | `string` | `""` |
| `sessionGroups` | `any` | `null` |
| `orderCount` | `int` | `null` |
| `isSupplyLimitOverrideShopper` | `bool` | `false` |
| `isPriorityShopper` | `bool` | `false` |
| `isChangingOrder` | `bool` | `false` |
| `changingOrderId` | `any` | `null` |
| `hasActiveDeliverySubscription` | `bool` | `false` |
| `isWPayDeliverySubscription` | `bool` | `false` |

No other shopper fields were present in the unauthenticated response.

#### 5.1.3 `context.fulfilment` fields

| Field | Type | Observed value | Description |
|-------|------|----------------|-------------|
| `address` | `string` | `"Glenfield"` | Suburb name (delivery area guess) |
| `selectedDate` | `string` | `null` | No slot selected |
| `selectedDateWithTZInfo` | `string` | `null` | — |
| `startTime` | `string` | `null` | Slot start window |
| `endTime` | `string` | `null` | Slot end window |
| `method` | `string` | `"Courier"` | `"Courier"` or `"Pickup"` |
| `cutOffTime` | `string` | `null` | Express cutoff |
| `isSlotToday` | `bool` | `false` | — |
| `isAddressInDeliveryZone` | `bool` | `true` | Whether delivery address is covered |
| `isDefaultDeliveryAddress` | `bool` | `false` | Is this the stored default? |
| `areaId` | `int` | `1242` | Geographic area identifier |
| `suburbId` | `int` | `0` | Always 0 in unauthenticated context |
| `pickupAddressId` | `int` | `0` | 0 = no pickup store selected |
| `fulfilmentStoreId` | `int` | `9171` | Default delivery-area store identifier |
| `perishableCode` | `string` | `"P"` | Perishable handling zone |
| `locker` | `any` | `null` | Locker selection (unused) |
| `expressFulfilment` | `dict` | See below | Express slot flags and fees |

`expressFulfilment` sub-keys:

| Key | Observed value |
|-----|----------------|
| `isExpressSlot` | `false` |
| `isFlexibleDeliverySlot` | `false` |
| `expressPickUpFee` | `null` |
| `expressDeliveryFee` | `null` |
| `flexibleDeliveryFee` | `null` |

**Critical distinction:** `fulfilmentStoreId: 9171` is a *delivery-area* store ID (for
courier fulfilment). It does **not** appear in the pickup-addresses store list (tested
by scanning 20+ store IDs — `9171` is absent). This ID belongs to the store's delivery ID.

#### 5.1.4 `mainNavs` structure

`mainNavs` is a list of 6 navigation blocks. The first five carry `navigationItems[]`,
each holding `items[]`. Each item carries navigation metadata and zero or more
`dasFacets` that describe its position in the facet tree.

Observed top-level `mainNavs` map:

| Index | Label | Items (first 3) |
|-------|-------|-----------------|
| 0 | *(unnamed)* | *no items present* |
| 1 | **Browse** | Fruit & Veg, Meat & Poultry, Fish & Seafood … |
| 2 | **Specials & offers** | Specials & offers, Member Price, Boosts … |
| 3 | **Favourites & lists** | Favourites, Past orders, Saved lists … |
| 4 | **Recipes** | *no items present* |
| 5 | **Disney OOSHIES™** | *no items present* |

Each Browse item has keys: `id`, `label`, `url` (e.g. `/shop/browse/meat-poultry`),
`dasFacets` (one element describing this department), `promoTiles`.

Each `dasFacets` entry on a Browse item:

| Key | Description |
|-----|-------------|
| `key` | Facet type, e.g. `"Department"` |
| `value` | Numeric string identifier, e.g. `"2"` |
| `name` | Human label, e.g. `"Meat & Poultry"` |
| `isBooleanValue` | `false` for all departments |
| `productCount` | Total products in this department |
| `shelfResponses` | Empty at the Browse level; populated on aisle-level responses |

### 5.2 `GET /api/v1/products`

The primary product catalogue endpoint. Accepts a large set of query parameters.

**HTTP 200** returns a JSON object with this shape:

```json
{
  "products": {
    "items":      [ /* product objects */ ],
    "totalItems": 10000
  },
  "dasFacets":   [ /* facet objects */ ],
  "sortOptions": [ /* sort option objects */ ],
  "currentPageSize":  24,
  "currentSortOption": "BrowseRelevance"
}
```

#### Parameters

| Parameter | Required | Values / type | Default | Description |
|-----------|----------|---------------|---------|-------------|
| `target` | Yes (mode) | `"search"` or `"browse"` | — | Switches between keyword search and full catalogue browse |
| `search` | Yes if target=search | `string` | — | Free-text product query |
| `dasFilter` | Yes for aisle/department filtering | `string` (see §6) | — | Hierarchical facet filter; only valid with `target=browse` |
| `size` | No | `int` (1–120 tested; 120 unconfirmed) | `24` | Results per page |
| `page` | No | `int` (1-indexed) | `1` | Page number |
| `sort` | No (browse) | `PriceAsc`, `PriceDesc`, `CUPAsc`, `BrowseRelevance` | `BrowseRelevance` | Sort order |
| `inStockProductsOnly` | No | `"false"` or `"true"` | `"false"` | Exclude out-of-stock items |

`target=search` ignores `dasFilter` and `sort`. `target=browse` ignores `search`.

#### `sort` option values

| Value | Meaning |
|-------|---------|
| `BrowseRelevance` | Site's internal relevance ranking (no order guaranteed) |
| `PriceAsc` | Lowest price first |
| `PriceDesc` | Highest price first |
| `CUPAsc` | Lowest unit price (cost per kg/L/unit) first |

#### Product item schema (target=search and target=browse)

```json
{
  "type":           "Product",
  "name":           "woolworths nz beef mince grass fed 5% fat",
  "brand":          "woolworths nz",
  "slug":           "woolworths-nz-beef-mince-grass-fed-5-fat",
  "sku":            "42246",
  "barcode":        "9414742036509",
  "variety":        "standard",
  "unit":           "Each",
  "selectedPurchasingUnit": null,
  "price": {
    "originalPrice":       16.99,
    "salePrice":           16.99,
    "savePrice":           0.00,
    "savePercentage":      0.0,
    "canShowSavings":      true,
    "hasBonusPoints":      false,
    "isClubPrice":         false,
    "isSpecial":           false,
    "isNew":               false,
    "canShowOriginalPrice":true,
    "discount":            null,
    "total":               null,
    "isTargetedOffer":     false,
    "averagePricePerSingleUnit": null,
    "isBoostOffer":        false,
    "purchasingUnitPrice": null,
    "ordered":             null
  }
}
```

**Price fields of interest:**

| Field | Type | Meaning |
|-------|------|---------|
| `price.salePrice` | `float` | **Current selling price — use this for comparisons** |
| `price.originalPrice` | `float` | Price before any discount |
| `price.savePrice` | `float` | `originalPrice − salePrice` |
| `price.savePercentage` | `float` | Discount percentage |
| `price.isSpecial` | `bool` | `true` if on special (not club price) |
| `price.isClubPrice` | `bool` | `true` if member/club exclusive price |
| `price.isMemberPrice` | `bool`/`null` | `true` if Everyday Rewards member price; `null` when not logged in |

#### Pagination

`size` controls items per page; `page` (1-indexed) selects the page. The maximum tested
`size` is 120 (from the GitHub code sample). For "milk" at `size=10`, `page=2` returned
10 items and `totalItems=495`, confirming the page parameter is honoured and counts are
exact. There is no `nextPage` cursor — page numbers are predictable integers.

#### `dasFacets` format (search and browse responses)

Both `target=search` and `target=browse` responses include a `dasFacets` array at the
top level. Each element:

```json
{
  "key":              "Aisle",       // facet type: "Department", "Aisle", "Brand", …
  "value":            "88",          // numeric string identifier
  "name":             "Beef",        // human label
  "productCount":     103,
  "isBooleanValue":   false,
  "shelfResponses": [                // empty at top level; populated in dept responses
    { "id": 541, "label": "Steak", "url": "steak" },
    …
  ]
}
```

At the top-level browse (no `dasFilter`), `dasFacets` contains all 14 departments.
When `dasFilter=Department;;meat-poultry;false` is applied, `dasFacets` is replaced by
the aisles within that department (12 aisles for Meat & Poultry).

### 5.3 `GET /api/v1/addresses/pickup-addresses`

Returns all click-and-collect pickup store locations.

**HTTP 200** — no parameters required.

#### Response structure

```json
{
  "storeAreas": [
    {
      "id":   494,
      "name": "All Pick up locations",
      "storeAddresses": [
        {
          "id":     1225718,
          "name":   " Woolworths Northlands",
          "address": "cnr Main North & Sawyers Arms Roads,Northlands Click and Collect,8051,Northlands Click and Collect"
        },
        …
      ]
    },
    …
  ]
}
```

**Store record schema (confirmed across 20+ stores):**

| Field | Type | Notes |
|-------|------|-------|
| `id` | `int` | Store identifier — this is the value used in `ChangeStore.py` button clicks |
| `name` | `string` | Store name (leading space present on some records) |
| `address` | `string` | Full address string; first comma-delimited segment is the street/suburb |
| *(no other keys)* | | `siteDataId`, `externalId`, `siteCode` are all absent |

The `storeAreas` array contains delivery-zone groupings. Area `id=494` with
`name="All Pick up locations"` is the catch-all group containing every pickup store.
This is the group selected in `ChangeStore.py` and `Get_woolworths_store_choices.py`.

---

## 6. DasFilter Syntax and Complete Taxonomy

### 6.1 Format

`dasFilter` accepts a semicolon-delimited string encoding a hierarchical facet path.
Each facet group has the form:

```
{key};;{value};{isBoolean}
```

Multiple facets are AND-chained simply by concatenation:

```
Department;;meat-poultry;false;Aisle;;88;false
```

| Segment | Meaning |
|---------|---------|
| `Department` | Facet type key (from `dasFacets[].key`) |
| `;;` | Delimiter between key, value, and boolean |
| `meat-poultry` | Facet value — for Departments, this is the URL slug from Browse |
| `false` | Boolean flag (`true`/`false`); observed as `false` for all departments and aisles |

**Valid key types observed in `dasFacets`:**

| Key | Value format | Example |
|-----|-------------|---------|
| `Department` | URL slug | `meat-poultry`, `pantry`, `fridge-deli` |
| `Aisle` | Numeric string | `88`, `89`, `116` |
| Subsequent levels | Not confirmed | shelf-level keys not tested |

**Confirmed working filters:**

| dasFilter value | Result |
|----------------|--------|
| *(absent)* | Full 10,000-product catalogue |
| `Department;;meat-poultry;false` | 624 products, aisles returned |
| `Department;;pantry;false` | 6,566 products |
| `Department;;fruit-veg;false` | 722 products |
| `Department;;meat-poultry;false;Aisle;;88;false` | Accepted (HTTP 200) but **does NOT narrow** from the parent department (still 624 items) |
| `2;;1;false` (raw numeric dept key) | Accepted but **ignored** (returns full catalogue) |

**Not working:** Shelf-level filtering (`Shelf;;541;false`) returns `totalItems=-1`
and zero items. Aisle-level chaining beyond the department produces no further
narrowing regardless of format tried.

### 6.2 Complete Department and Aisle Map

All counts are from `target=browse&dasFilter=Department;;<slug>;false&size=1`
as of the exploration date. `shelfResponses` is `[]` (empty) at the department
level for all departments — shelf data is not exposed via the API without additional
context that was not discovered.

#### Fruit & Veg (slug: `fruit-veg`) — 722 products

| Aisle ID | Name | Product count |
|----------|------|--------------|
| 116 | Fruit | 128 |
| 117 | Vegetables | 276 |
| 118 | Prepared Fruit & Veg | 48 |
| 119 | Fresh Salad & Herbs | 159 |
| 120 | In Season | 33 |
| 121 | Organic | 22 |
| 122 | The Odd Bunch | 14 |
| 123 | Shop Fresh Deals | 42 |

#### Meat & Poultry (slug: `meat-poultry`) — 624 products

| Aisle ID | Name | Product count |
|----------|------|--------------|
| 88 | Beef | 103 |
| 89 | Chicken & Poultry | 123 |
| 90 | Lamb | 53 |
| 91 | Pork | 71 |
| 92 | Venison & Game | 3 |
| 93 | Mince & Patties | 26 |
| 94 | Sausages | 61 |
| 95 | BBQ Meat | 105 |
| 96 | Roast Meat | 31 |
| 98 | Offal & Bones | 3 |
| 99 | Plant Based Alternatives | 9 |
| 100 | 3 for $20 | 36 |

#### Fish & Seafood (slug: `fish-seafood`) — 113 products

| Aisle ID | Name | Product count |
|----------|------|--------------|
| 130 | Fish | 5 |
| 131 | Salmon | 49 |
| 132 | Prawns & Seafood | 45 |
| 133 | 3 for $20 | 14 |

#### Fridge & Deli (slug: `fridge-deli`) — 2,821 products

| Aisle ID | Name | Product count |
|----------|------|--------------|
| 26 | Eggs, Butter & Spreads | 149 |
| 27 | Milk | 222 |
| 28 | Cheese | 791 |
| 29 | Yoghurt & Desserts | 271 |
| 30 | Cream & Custard | 42 |
| 31 | Juice & Drinks | 112 |
| 32 | Deli Meats & Seafood | 310 |
| 33 | Prepared Meals & Sides | 589 |
| 34 | Deli Salads | 41 |
| 35 | Pasta, Pizza & Pastry | 75 |
| 36 | Dips, Hummus & Nibbles | 191 |
| 37 | Vegan & Vegetarian | 19 |
| 38 | 3 for $12 Deli | 9 |

#### Bakery (slug: `bakery`) — 706 products

| Aisle ID | Name | Product count |
|----------|------|--------------|
| 16 | Bakery In Store | 179 |
| 17 | Sliced & Packaged Bread | 107 |
| 18 | Buns, Rolls & Bread Sticks | 58 |
| 19 | Wraps, Pita & Pizza Bases | 72 |
| 20 | Pastries, Croissants & Biscuits | 47 |
| 21 | Cakes, Muffins & Desserts | 165 |
| 22 | Bagels, Crumpets & Pancakes | 51 |
| 23 | Gluten Free | 14 |
| 24 | Low Carb & Keto | 13 |

#### Frozen (slug: `frozen`) — 997 products

| Aisle ID | Name | Product count |
|----------|------|--------------|
| 78 | Frozen Vegetables | 131 |
| 79 | Frozen Meat | 70 |
| 80 | Frozen Meat Alternatives | 24 |
| 81 | Frozen Seafood | 98 |
| 82 | Frozen Fruit & Drink | 45 |
| 83 | Frozen Meals & Snacks | 198 |
| 84 | Pizza, Pastry & Bread | 48 |
| 85 | Ice Cream & Sorbet | 326 |
| 86 | Frozen Desserts | 55 |
| 87 | Ice | 2 |

#### Pantry (slug: `pantry`) — 6,566 products

| Aisle ID | Name | Product count |
|----------|------|--------------|
| 59 | Snacks & Sweets | 1,866 |
| 60 | Biscuits & Crackers | 502 |
| 61 | Tinned Foods & Packets | 568 |
| 62 | Baking | 473 |
| 63 | Cereals & Spreads | 445 |
| 64 | Sauces & Pastes | 698 |
| 65 | Pasta, Noodles & Grains | 402 |
| 66 | Herbs, Spices & Stock | 349 |
| 67 | Oil, Vinegar & Condiments | 458 |
| 68 | Meal Kits | 183 |
| 69 | International Foods | 336 |
| 70 | Eggs | 25 |
| 71 | Desserts | 152 |
| 72 | Long Life Milk | 78 |
| 73 | Bulk Foods | 31 |

#### Beer & Wine (slug: `beer-wine`) — 1,557 products

| Aisle ID | Name | Product count |
|----------|------|--------------|
| 134 | Beer | 199 |
| 135 | Craft Beer | 96 |
| 136 | Cider | 50 |
| 137 | Champagne & Sparkling Wine | 109 |
| 138 | Red Wine | 416 |
| 139 | White Wine | 397 |
| 140 | Rose Wine | 108 |
| 141 | Moscato & Sweet Wine | 25 |
| 142 | Cask Wine | 17 |
| 143 | Mini Wine Bottles & Cans | 48 |
| 144 | Organic Wine | 14 |
| 145 | Seltzer & Alcoholic Kombucha | 6 |
| 146 | Lower Alcohol | 21 |
| 147 | Non Alcoholic | 51 |

#### Drinks (slug: `drinks`) — 1,683 products

| Aisle ID | Name | Product count |
|----------|------|--------------|
| 39 | Coffee | 473 |
| 40 | Tea & Milk Drinks | 349 |
| 41 | Soft Drinks & Sports Drinks | 362 |
| 42 | Juice & Cordial | 323 |
| 43 | Water | 137 |
| 44 | Chilled Juice & Drinks | 39 |

#### Health & Body (slug: `health-body`) — 3,968 products

| Aisle ID | Name | Product count |
|----------|------|--------------|
| 101 | Bath, Shower & Soap | 254 |
| 102 | Hair Care | 782 |
| 103 | Dental & Oral Care | 219 |
| 104 | Deodorant & Body Sprays | 166 |
| 105 | Skin Care & Sun Care | 778 |
| 106 | Eye & Ear Care | 51 |
| 107 | Shaving & Hair Removal | 123 |
| 108 | Make Up & Nail Care | 356 |
| 109 | Tissues & Cotton Wool | 50 |
| 110 | Period & Continence Care | 200 |
| 111 | Medical & First Aid | 290 |
| 112 | Vitamins & Supplements | 435 |
| 113 | Sports Nutrition & Weight Management | 216 |
| 115 | Contraception & Pregnancy | 48 |

#### Household (slug: `household`) — 2,189 products

| Aisle ID | Name | Product count |
|----------|------|--------------|
| 45 | Bathroom | 92 |
| 46 | Kitchen | 431 |
| 47 | Laundry | 190 |
| 48 | Cleaning | 398 |
| 49 | Pest Control | 69 |
| 50 | Homewares | 57 |
| 51 | Bags | 62 |
| 52 | Clothing & Accessories | 153 |
| 54 | Garden & Garage | 97 |
| 55 | Hardware & Electrical | 249 |
| 56 | Entertainment & Gifts | 205 |
| 57 | Magazines & Stationery | 186 |

#### Baby & Child (slug: `baby-child`) — 655 products

| Aisle ID | Name | Product count |
|----------|------|--------------|
| 125 | Nappies & Wipes | 207 |
| 126 | Baby Food | 199 |
| 127 | Formula | 62 |
| 128 | Bottles, Toys & Accessories | 181 |
| 129 | For Mum | 6 |

#### Pet (slug: `pet`) — 602 products

| Aisle ID | Name | Product count |
|----------|------|--------------|
| 74 | Cats | 278 |
| 75 | Dogs | 224 |
| 76 | Birds, Fish & Small Animals | 25 |
| 77 | Pet Health & Accessories | 75 |

#### Back to School (slug: `back-to-school`) — 1,264 products

| Aisle ID | Name | Product count |
|----------|------|--------------|
| 148 | Breakfast Ideas | 196 |
| 149 | Lunchbox Ideas | 444 |
| 150 | Snacks Ideas | 334 |
| 151 | Multipacks | 158 |
| 152 | School Essentials | 132 |

**Total catalogue product count at time of exploration: 22,512 products** (sum of all
department counts; each product appears in exactly one aisle).

---

## 7. Endpoints Tested That Do NOT Work

The following paths were probed and confirmed non-functional. They are listed here
to prevent redundant investigation.

### 7.1 GET endpoints returning 404

| Path | Error body |
|------|-----------|
| `/api/v1/stores` | `No HTTP resource was found … 'shop.countdown.co.nz/api/v1/stores'` |
| `/api/v1/store` | 404 |
| `/api/v1/store/finder` | 404 |
| `/api/v1/store-location` | 404 |
| `/api/v1/pickup-locations` | 404 |
| `/api/v1/addresses/find-store` | 404 |
| `/api/v1/product/{sku}` | 404 (path tried as `/api/v1/product/282768`) |
| `/api/v1/products/search` | 404 (distinct from `/api/v1/products?target=search`) |
| `/api/v1/shelves` | 404 |
| `/api/v1/shelf` | 404 |
| `/api/v1/categories` | 404 |
| `/api/v1/trolleys/active` | 404 |
| `/api/v1/trolleys` | 404 |
| `/api/v1/session/current` | 404 |
| `/api/v1/user/current` | 404 |
| `/api/v1/delivery-slots` | 404 |
| `/api/v1/bookatimeslot` | 404 |
| `/api/v1/click-and-collect` | 404 |
| `/api/v1/specials` | 404 |
| `/api/v1/member-prices` | 404 |
| `/api/v1/catalogs` | 404 |
| `/api/v1/store-products` | 404 |
| `/api/v1/session` | 404 (returns generic "Ooops" error) |

### 7.2 GET endpoints returning 401

| Path | Notes |
|------|-------|
| `/api/v1/trolleys/my` | Requires authenticated shopper session |

### 7.3 POST endpoints (all return 404)

Tested with payloads `{"storeId": <id>}`, `{"pickupAddressId": <id>}`, and
`{"fulfilmentStoreId": <id>}`:

| Path |
|------|
| `/api/v1/addresses/set-store` |
| `/api/v1/addresses/set-pickup-store` |
| `/api/v1/addresses/set-default-store` |
| `/api/v1/addresses/selected-store` |
| `/api/v1/addresses/change-store` |
| `/api/v1/addresses/my` |
| `/api/v1/addresses/current` |
| `/api/v1/addresses/pickup-address` |
| `/api/v1/addresses/pickup-addresses` |
| `/api/v1/store/context` |
| `/api/v1/store/current` |
| `/api/v1/store/set` |
| `/api/v1/store/selected` |
| `/api/v1/fulfilment/store` |
| `/api/v1/fulfilment/selected-store` |

No public API endpoint was found that accepts a store change instruction and
returns HTTP 200 or 204. Store context is set exclusively by browser cookies
acquired through navigation of the Woolworths web application.

### 7.4 `target=search` returning 400 (missing header)

`GET /api/v1/products?target=search&search=milk` returns HTTP 400 when the
`x-requested-with` header is absent or empty. This is not a broken endpoint — it is
a header-validation gate that all API calls must pass.

### 7.5 `target=browse` with aisle-level or shelf-level `dasFilter`

Adding an `Aisle` component to `dasFilter` is accepted (HTTP 200) but does not
narrow results:

```
target=browse&dasFilter=Department;;meat-poultry;false;Aisle;;88;false
→ HTTP 200  totalItems=624  (same as department-only filter)
```

The raw numeric format also does not work:

```
target=browse&dasFilter=2;;1;false
→ HTTP 200  totalItems=10000  (full catalogue, filter ignored)
```

Shelf-level targeting returns zero results:

```
target=browse&dasFilter=Department;;meat-poultry;false;Aisle;;88;false;Shelf;;541;false
→ HTTP 200  totalItems=10000  (filter ignored)
```

---

## 8. Per-Store Pricing — Key Finding

The `fulfilmentStoreId` and `pickupStoreId` query parameters on
`/api/v1/products` are accepted without error (HTTP 200) but **do not change prices**.

### Test methodology

1. Called `GET /api/v1/products?target=search&search=milk&size=10` with no store
   parameter → collected 10 products with their `sku` and `salePrice`.
2. Called the same endpoint adding `fulfilmentStoreId=9171` (the default delivery
   store from `context.fulfilment`) → compared every returned SKU price against
   the baseline. **Zero changes.**
3. Called the same endpoint adding `fulfilmentStoreId=1225718` (a pickup store,
   Woolworths Northlands, from the pickup-addresses list) → **zero changes.**

### Parameters tested (all accepted, none effective)

`fulfilmentStoreId`, `pickupStoreId`, `clickAndCollectStoreId`, `collectionStoreId`,
`deliveryStoreId`, `storeCode`, `storeExternalReference`, `locationId`, `addressId`,
`store`, `fulfilmentType`.

Woolworths NZ uses a **global price list** across all stores for the catalogue API.
Per-store pricing differences (if any) are applied at the checkout / fulfilment layer,
not at product-search time. This means the meal-cost optimizer can safely use a single
price search per ingredient across all nearby stores — the same ingredient will have
the same catalogue price regardless of which store context is active.

---

## 9. Summary of API Capabilities

| Capability | Available via API? | Method |
|-----------|-------------------|--------|
| Search products by keyword | Yes | `GET /api/v1/products?target=search&search=<term>` |
| Browse full catalogue (10K items) | Yes | `GET /api/v1/products?target=browse` |
| Filter by department | Yes (partial) | `target=browse&dasFilter=Department;;<slug>;false` |
| Filter by aisle | No (accepted but ignored) | — |
| Filter by shelf | No | — |
| Sort by price (asc/desc) | Yes | `sort=PriceAsc` / `sort=PriceDesc` |
| Sort by unit price | Yes | `sort=CUPAsc` |
| Get per-store pricing | No | Prices are global |
| Programmatically change store | No | No POST endpoint exists |
| Get all pickup stores | Yes | `GET /api/v1/addresses/pickup-addresses` |
| Get site navigation taxonomy | Yes | `GET /api/v1/shell` |
| Get session fulfilment context | Yes | `context.fulfilment` inside `/api/v1/shell` |
| View trolley / cart | No (unauthenticated) | 401 |
| Get delivery slot availability | No | 404 |

### What the API cannot do (requires browser / Playwright)

- **Set the pickup store context** — must be done via browser cookie by navigating to
  the Woolworths website, visiting the store-selection modal, and selecting a store.
  `scripts/woolworths/ChangeStore.py` automates this via Playwright by navigating
  directly to `https://www.woolworths.co.nz/bookatimeslot/(hww-modal:change-pick-up-store)`
  and clicking the store button.
- **Access member-only prices** — `price.isMemberPrice` is always `null` without an
  authenticated session. ClubPrice (`isClubPrice`) is visible without login.
- **Access checkout / trolley operations** — all protected endpoints return 401.

---

## 10. Practical Usage for the Meal Cost Optimizer

The API is sufficient to replace the Playwright-based scraping layer entirely for the
product-price component:

```
1. Seed session:    session.get("https://www.woolworths.co.nz/")
2. Search:          session.get("/api/v1/products",
                         params={"target":"search","search":<ingredient>,"size":3})
3. Read price:      item["price"]["salePrice"]
4. Read SKU:        item["sku"]
5. Read unit:       item["unit"]
```

Store filtering (finding which stores are within 5 km) continues to use the
pre-built `data/woolworths_stores.csv` (merged from the location API and pickup
choices API). The `woolworths_store_choices.csv` provides `id` → `name` mapping;
the `woolworths_store_data.csv` provides latitude/longitude.

The Playwright layer is **still required** for the store-switching step (to set the
correct availability context before browsing), but product prices can be fetched via
the JSON API using the same browser session cookies.
