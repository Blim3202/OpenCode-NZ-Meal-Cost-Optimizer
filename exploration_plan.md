# Woolworths Per-Store Pricing -- Exploration Plan & Technical Findings

## Objective

Find a way to set the Woolworths store context so `/api/v1/products` returns **per-store pricing** instead of the global price list tied to the default delivery address (Glenfield, $7.33 for 3L milk).

**Known price differential (validation targets):**
- Greymouth (id 764300): Woolworths Milk Standard Bottle 3L = **$7.15**
- Glenfield  (id 1190273): Woolworths Milk Standard Bottle 3L = **$7.33**

---

## How Cookies Encode Store Context

### Why URL params don't work

When `requests.get("https://www.woolworths.co.nz/?pickupStoreId=764300")` is called, the server returns the homepage HTML. The `pickupStoreId` parameter is read by **frontend JavaScript** running in the browser -- the server itself does not translate URL params into cookies.

The `requests.Session` receives the server's Set-Cookie headers, but these are generic session cookies (security tokens, etc.) with no store information.

**The store selection flow is entirely browser-side JavaScript:**
1. User clicks "Change pickup store" -> navigates to `/bookatimeslot/(hww-modal:change-pick-up-store)`
2. User selects "All Pick up locations" from the area dropdown
3. User clicks the target store button
4. Woolworths JavaScript reads the store ID and sets **internal cookies scoped to `.woolworths.co.nz`** that encode the selected store
5. All subsequent `/api/v1` calls send these cookies, and the server uses them to return per-store prices

URL parameters are never sufficient because the store context is set exclusively by JavaScript running in a real browser.

---

## What Cookies Are Required

### Cookie domain breakdown (from Greymouth capture -- 67 cookies total)

| Domain | # Cookies | Example names | Purpose |
|--------|-----------|---------------|---------|
| `.woolworths.co.nz` | ~30 | `AKA_A2`, `rxVisitor`, `dtSa`, `dtPC` | **First-party; likely carries per-store context** |
| `.www.woolworths.co.nz` | 1 | `RT` | Adobe Analytics (ECID) -- NOT store-specific, not required |
| `www.woolworths.co.nz` | ~15 | `cw-ssuflow`, `agaCORS`, `aga...` | First-party app cookies |
| `.doubleclick.net`, `.adnxs.com`, etc. | ~20 | `IDE`, `uuid2`, `TDID` | Third-party ad/analytics -- not required for pricing |

### Which cookies matter

- **`session_state`** (`.www.woolworths.co.nz`): alone -- insufficient. Returns $7.33 for both stores.
- **`RT`** (Adobe Analytics, `.www.woolworths.co.nz`): alone -- insufficient. Not store-specific.
- **All 67 cookies injected**: works perfectly. Greymouth $7.15, Glenfield $7.33.

**Conclusion:** The per-store pricing signal is in one or more of the ~30 `.woolworths.co.nz` scoped cookies. We cannot isolate which one(s) without further testing. The safe approach is to inject the **full cookie jar**.

### Third-party cookies (RT, uuid2, IDE, etc.)

These come from external services (Adobe, AppNexus, Google, etc.) and are assigned **probabilistically** -- you cannot predict or compute them. They're also not the per-store mechanism, but they may be required to make the request look like a legitimate browser session (Akamai may validate the cookie ecosystem).

**Implication:** You must capture ALL cookies per store using Playwright. You cannot construct the required cookie set manually.

---

## How to Get Products Once Cookies Are Stored

### The flow (working)

```
1. [One-time per store] Playwright opens https://www.woolworths.co.nz/bookatimeslot/(hww-modal:change-pick-up-store)
                          -> selects store -> captures full cookie jar -> saves to JSON

2. [Every price query] Load cookie jar from JSON
                        -> inject ALL cookies into requests.Session (preserving domain/path from capture)
                        -> GET https://www.woolworths.co.nz/  [seed]
                        -> GET /api/v1/products?target=search&search=<ingredient>&size=3
                        -> read item["price"]["salePrice"]

3. [If price check fails] Re-run step 1 to refresh the cookie jar
```

**Playwright is NOT needed for price queries after the jar is captured.** A single `requests.Session` with injected cookies is sufficient.

### Session seeding with injected cookies

```python
session = requests.Session()
session.headers.update({
    "x-requested-with": "??",
    "User-Agent": "Mozilla/5.0 ...",
    "Accept": "application/json, ...",
})

# Seed cookies -- visit homepage first
session.get("https://www.woolworths.co.nz/", timeout=15)

# Clear Woolworths cookies from seed, inject stored jar
session.cookies.clear()
for name, info in stored_jar.items():
    domain = info.get("domain")   # preserves .woolworths.co.nz scoping
    session.cookies.set(name, info["value"], domain=domain, path="/")

# API call -- returns per-store pricing
resp = session.get(
    "https://www.woolworths.co.nz/api/v1/products",
    params={"target": "search", "search": "milk", "size": 3},
    timeout=15,
)
```

---

## PHASE 2 FINDINGS -- Shell Validation and cw-lrkswrdjp Cookie

### Finding 7: /api/v1/shell correctly reflects injected cookie store context

Injecting Playwright-captured cookies and calling `/api/v1/shell` returns the correct store in `context.fulfilment`:

| Store | fulfilmentStoreId | pickupAddressId | method | address |
|-------|-------------------|-----------------|--------|---------|
| Greymouth | 9009 | 764300 | Pickup | Woolworths Greymouth |
| Glenfield | 9443 | 1190273 | Pickup | Woolworths Glenfield |
| Birkenhead | 9101 | 2124460 | Pickup | Woolworths Birkenhead |
| BASELINE (no cookies) | 9171 | 0 | Courier | Glenfield |

This means `/api/v1/shell` can be used as a **diagnostic check**: if `fulfilmentStoreId == 9171`, cookies have expired or were not injected correctly. No need to compare product prices to detect expiry.

### Finding 8: fulfilmentStoreId as query param does NOT work

Passing `fulfilmentStoreId=764300` as a query parameter to `/api/v1/shell` or `/api/v1/products` returns the default context (9171) -- confirmed again. No price changes detected.

### Finding 9: cw-lrkswrdjp is THE per-store cookie

This single cookie controls the entire store context. Its format:

```
dm-Pickup,f-9009,a-224,s-38    (Greymouth)
dm-Pickup,f-9443,a-440,s-38    (Glenfield)
dm-Pickup,f-9101,a-720,s-38    (Birkenhead)
```

| Field | Meaning | Greymouth | Glenfield | Birkenhead |
|-------|---------|-----------|-----------|------------|
| `dm` | Delivery method | Pickup | Pickup | Pickup |
| `f`  | fulfilmentStoreId | 9009 | 9443 | 9101 |
| `a`  | areaId (internal) | 224 | 440 | 720 |
| `s`  | Site/segment (constant) | 38 | 38 | 38 |

- **Injecting ONLY cw-lrkswrdjp** (no session_state, no other Playwright cookies) correctly sets the shell context to the right store.
- **session_state is NOT required** for context -- the full jar is NOT needed.
- **a- and s- fields are optional** -- cookie works with just `dm-Pickup,f-{fulfilmentStoreId}`
- BASELINE has no cw-lrkswrdjp cookie (absent when no store is selected).

### Finding 10: fulfilmentStoreId is NOT available from the API

The `fulfilmentStoreId` and `areaId` are internal IDs not exposed by any API endpoint:
- `/api/v1/addresses/pickup-addresses` returns only `id`, `name`, `address` per store
- The `id` field is the `pickupAddressId` (e.g., 764300), NOT the `fulfilmentStoreId` (e.g., 9009)
- No POST endpoint or query param can retrieve the mapping
- The `a-` area ID (e.g., 224) does NOT match any area from the `pickup-addresses` response

**Implication:** We must capture the mapping once via Playwright, then save it to disk.

---

## PHASE 3 FINDINGS -- Programmatic Cookie Construction (CONFIRMED)

### Finding 11: Constructed cookies work for shell context (3/3 stores)

Building `cw-lrkswrdjp` from known `fulfilmentStoreId` and `areaId` and injecting it into `requests.Session` correctly sets `/api/v1/shell` context for all tested stores:

| Store | Constructed cookie | Shell fulfilmentStoreId | Shell pickupAddressId | Status |
|-------|-------------------|------------------------|----------------------|--------|
| Greymouth | dm-Pickup,f-9009,a-224,s-38 | 9009 | 764300 | OK |
| Glenfield | dm-Pickup,f-9443,a-440,s-38 | 9443 | 1190273 | OK |
| Birkenhead | dm-Pickup,f-9101,a-720,s-38 | 9101 | 2124460 | OK |

### Finding 12: Constructed cookies produce per-store PRICING (21/21 products)

The critical confirmation: injecting a programmatically constructed `cw-lrkswrdjp` cookie into `requests.Session` causes `/api/v1/products` to return **correct per-store prices**.

Tested with 21 common milk SKUs between Greymouth and Glenfield -- ALL 21 show price differences:

| SKU | Product | Greymouth | Glenfield | Diff |
|-----|---------|-----------|-----------|------|
| 282768 | Woolworths Milk Standard 3L | $7.15 | $7.33 | +$0.18 |
| 282765 | Woolworths Milk Standard 1L | $4.95 | $4.91 | -$0.04 |
| 282793 | Meadow Fresh Milk Standard | $6.09 | $6.17 | +$0.08 |
| 701971 | Meadow Fresh Milk Standard | $9.09 | $9.16 | +$0.07 |
| 705692 | Anchor Milk Standard Blue | $9.07 | $8.92 | -$0.15 |
| ... | (16 more products) | ... | ... | ... |

**All 21 products have price differences -- per-store pricing confirmed via programmatic cookies.**

### Finding 13: No Playwright needed for price queries

The complete flow without Playwright:
1. Look up `fulfilmentStoreId` and `areaId` from `data/store_id_mapping.json`
2. Construct cookie: `dm-Pickup,f-{fulfilmentStoreId},a-{areaId},s-38`
3. Inject into `requests.Session`
4. Call `/api/v1/shell` to verify context (check `fulfilmentStoreId != 9171`)
5. Call `/api/v1/products` for pricing

Playwright is only needed **once** to capture the mapping for each store.

### Finding 14: Mapping table captured for 3 stores

Saved to `data/store_id_mapping.json`:

| pickupAddressId | fulfilmentStoreId | areaId | Store Name |
|-----------------|-------------------|--------|------------|
| 764300 | 9009 | 224 | Woolworths Greymouth |
| 1190273 | 9443 | 440 | Woolworths Glenfield |
| 2124460 | 9101 | 720 | Woolworths Birkenhead |

To expand to all 171 stores: run Playwright capture for each, extract cw-lrkswrdjp, parse fields, save to mapping.

### Implication: No Playwright needed for price queries

If we can generate the `cw-lrkswrdjp` cookie value programmatically (e.g., from a known `fulfilmentStoreId` and `areaId`), we can set the store context with a **single cookie** -- no Playwright, no 67-cookie jar, no browser automation.

The format `dm-Pickup,f-{fulfilmentStoreId},a-{areaId},s-38` appears to be a simple encoding. We need to:
1. Confirm the `s-38` constant across all NZ Woolworths stores
2. Confirm `dm-Pickup` is always `Pickup` for pickup stores
3. Test whether constructing this cookie from known IDs and injecting it returns correct per-store pricing

### Open question: Does cw-lrkswrdjp alone change PRICES (not just shell context)?

Step 3b confirmed the shell context shifts correctly. The milk 3L price was not found in the top-5 search results during the test -- this needs re-testing with a broader search or a different product to confirm prices also change.

---

## Cookie Lifespan and Expiry

### Observed behavior
- `session_state` cookies expire when the browser closes (session scope)
- First-party `.woolworths.co.nz` cookies (`rxVisitor`, `dtPC`, etc.) appear to be **session-scoped or short-lived** (1-4 hours observed)
- Third-party cookies (RT, ad networks) can be longer-lived (days to weeks)

### Implications for the optimizer

| Scenario | Cookie validity | What to do |
|----------|-----------------|------------|
| Fresh jar, same browser session | Valid | Use directly |
| After browser restart | May be expired | Re-capture with Playwright |
| After ~1-4 hours | Likely expired | Re-capture with Playwright |
| When prices return to $7.33 baseline | Cookies expired or store changed | Re-capture with Playwright |

**Reliability strategy:** If an API call returns prices that don't match the expected store (e.g., all stores return $7.33), the cookie jar has likely expired and needs refreshing. *Note* we could maybe try GET /api/v1/shell to see if the context store ID had changed with new cookies or if the cookie expires.

---

## Application Design: On-the-Fly vs Bulk Processing

### Option A: Construct cw-lrkswrdjp cookie programmatically (ideal)
- **Pros:** No Playwright at all, instant, no expiry issues, no browser needed
- **Cons:** Only confirmed for shell context -- need to verify prices also change
- **Format:** `dm-Pickup,f-{fulfilmentStoreId},a-{areaId},s-38`
- **Verdict:** Best if prices confirmed -- this is the target architecture

### Option B: Bulk process cookies daily (fallback)
- **Flow:** Daily scheduled task runs Playwright to capture cw-lrkswrdjp cookies for all stores, saves to disk
- **Pros:** Reliable, all stores ready
- **Cons:** Requires Playwright infrastructure, daily refresh needed
- **Verdict:** Good fallback if programmatic construction doesn't work for pricing

### Option C: Per-store on-demand capture (hybrid)
- **Flow:** On first query to a store, if no cookie exists, capture with Playwright, save to disk
- **Pros:** No upfront work
- **Cons:** First query slow
- **Verdict:** Acceptable for meal-planner scale

### Recommendation

**Phase 2 priority:** Verify whether constructing `cw-lrkswrdjp` programmatically changes product prices (not just shell context). If confirmed, the architecture becomes:

```
No Playwright needed at all:
  1. Look up store's fulfilmentStoreId and areaId from data/woolworths_store_choices.csv
  2. Construct cookie: dm-Pickup,f-{fulfilmentStoreId},a-{areaId},s-38
  3. Inject into requests.Session
  4. Call /api/v1/shell to verify context (check fulfilmentStoreId != 9171)
  5. Call /api/v1/products for pricing
```

If programmatic construction doesn't work for pricing, fall back to Playwright capture of just the `cw-lrkswrdjp` cookie (not the full 67-cookie jar).

---

## Confirmed: Stored Cookies Eliminate the Need for Playwright at Query Time

**Yes -- confirmed by experiment.**

The full Playwright cookie injection test (Step 2) showed:
- Greymouth: Greymouth cookies injected -> **$7.15** ✓
- Glenfield: Glenfield cookies injected -> **$7.33** ✓
- Baseline (no cookies): -> **$7.33** (default, wrong)

With a stored cookie jar and `requests.Session`, no browser is required for price queries. Only for **acquiring or refreshing the jar**.

---

## Confirmed Findings Summary

| Test | Result | Notes |
|------|--------|-------|
| URL-param seeding (`?pickupStoreId=764300`) | [FAIL] No effect | Server doesn't translate params to cookies |
| `session_state` cookie only | [FAIL] Returns $7.33 | Not the store-context carrier |
| `RT` (Adobe Analytics) cookie only | [FAIL] Returns $7.33 | Not store-specific, not required |
| All 67 Playwright cookies injected | [OK] $7.15 / $7.33 | Works; full jar required |
| Stored cookie jar + requests.Session | [OK] No Playwright needed | For price queries |
| /api/v1/shell with injected cookies | [OK] Correct store shown | fulfilmentStoreId matches selected store |
| fulfilmentStoreId as query param | [FAIL] No effect | Still returns default 9171 |
| cw-lrkswrdjp + session_state only | [OK] Correct store shown | Only 2 cookies needed for context |
| cw-lrkswrdjp ONLY | [OK] Correct store shown | 1 cookie controls entire store context |
| **Programmatic cw-lrkswrdjp construction** | **[OK] Per-store pricing** | **21/21 products show price differences** |
| **Constructed cookie vs full jar** | **[OK] Equivalent** | **Same prices, no Playwright needed** |

---

## Implementation Checklist

### Phase 3 (complete)
- [x] Test programmatic cw-lrkswrdjp construction -- verified per-store pricing (21/21 products)
- [x] Confirm s-38 is constant across stores (Greymouth, Glenfield, Birkenhead all use 38)
- [x] Capture mapping for 3 stores: Greymouth, Glenfield, Birkenhead
- [x] Save mapping to `data/store_id_mapping.json`

### Phase 4 (next)
- [ ] Bulk capture mapping for all 171 Woolworths stores via Playwright
- [ ] Build `set_store_context(session, fulfilment_store_id, area_id)` helper
- [ ] Add shell context validation: call /api/v1/shell after cookie injection, check fulfilmentStoreId
- [ ] Integrate cw-lrkswrdjp injection into woolworths_optimizer.py
- [ ] Expand DISH_INGREDIENTS in woolworths_optimizer.py to 21 dishes
- [ ] Fix hardcoded values in woolworths_optimizer.py (lines 175, 196)

---

## Key Files

- `scripts/woolworths/explore_woolworths_api_part2.py` -- Phase 1 exploration (URL seeding, full cookie injection)
- `scripts/woolworths/explore_woolworths_api_part3.py` -- Phase 2 exploration (shell validation, cw-lrkswrdjp deep-dive)
- `scripts/woolworths/explore_woolworths_api_part4.py` -- Phase 3 exploration (programmatic cookie construction, price validation)
- `scripts/woolworths/ChangeStore.py` -- Playwright store-selection (reference for cookie capture)
- `data/store_id_mapping.json` -- pickupAddressId -> fulfilmentStoreId/areaId mapping (3 stores captured)
- `data/part2_cookies.json` -- Saved Greymouth/Glenfield cookie jars for reference
- `data/woolworths_store_choices.csv` -- Store ID -> name mapping (171 stores)
- `data/woolworths_stores.csv` -- Store locations with lat/lon