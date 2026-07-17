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
| BASELINE (no cookies) | 9171 | 0 | Courier | Glenfield |

This means `/api/v1/shell` can be used as a **diagnostic check**: if `fulfilmentStoreId == 9171`, cookies have expired or were not injected correctly. No need to compare product prices to detect expiry.

### Finding 8: fulfilmentStoreId as query param does NOT work

Passing `fulfilmentStoreId=764300` as a query parameter to `/api/v1/shell` or `/api/v1/products` returns the default context (9171) -- confirmed again. No price changes detected.

### Finding 9: cw-lrkswrdjp is THE per-store cookie

This single cookie controls the entire store context. Its format:

```
dm-Pickup,f-9009,a-224,s-38    (Greymouth)
dm-Pickup,f-9443,a-440,s-38    (Glenfield)
```

| Field | Meaning | Greymouth | Glenfield |
|-------|---------|-----------|-----------|
| `dm` | Delivery method | Pickup | Pickup |
| `f`  | fulfilmentStoreId | 9009 | 9443 |
| `a`  | areaId | 224 | 440 |
| `s`  | Site/segment (constant) | 38 | 38 |

- **Injecting ONLY cw-lrkswrdjp** (no session_state, no other Playwright cookies) correctly sets the shell context to the right store.
- **session_state is NOT required** for context -- the full jar is NOT needed.
- BASELINE has no cw-lrkswrdjp cookie (absent when no store is selected).

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
| Programmatic cw-lrkswrdjp construction | [PENDING] Not yet tested | Need to verify prices also change |

---

## Implementation Checklist

### Phase 2 (immediate)
- [ ] Test programmatic cw-lrkswrdjp construction: `dm-Pickup,f-{fulfilmentStoreId},a-{areaId},s-38` -- verify prices change
- [ ] Confirm `s-38` is constant across all NZ Woolworths stores (test 3+ stores)
- [ ] Confirm `dm-Pickup` is always `Pickup` for pickup stores

### Phase 3 (if programmatic construction works)
- [ ] Build `build_cw_lrkswrdjp_cookie(fulfilment_store_id, area_id)` helper
- [ ] Build `set_store_context(session, fulfilment_store_id, area_id)` -- inject cw-lrkswrdjp, verify via /api/v1/shell
- [ ] Add shell context validation: call /api/v1/shell after cookie injection, check fulfilmentStoreId matches expected

### Phase 3 (fallback if programmatic fails)
- [ ] Build `capture_cw_lrkswrdjp(store_name, store_id)` -- Playwright captures just this 1 cookie
- [ ] Build `save_cookies_to_disk(store_id, jar)` -- persist to `data/woolworths_cookies/<store_id>.json`
- [ ] Build `load_and_inject_cookies(session, store_id)` -- load from disk, inject into session
- [ ] Build `is_jar_valid(jar)` -- check expiry via /api/v1/shell fulfilmentStoreId check

### General
- [ ] Add expiration refresh logic to optimizer (check shell context on each query)
- [ ] Expand DISH_INGREDIENTS in woolworths_optimizer.py to 21 dishes
- [ ] Fix hardcoded values in woolworths_optimizer.py (lines 175, 196)

---

## Key Files

- `scripts/woolworths/explore_woolworths_api_part2.py` -- Phase 1 exploration (URL seeding, full cookie injection)
- `scripts/woolworths/explore_woolworths_api_part3.py` -- Phase 2 exploration (shell validation, cw-lrkswrdjp deep-dive)
- `scripts/woolworths/ChangeStore.py` -- Playwright store-selection (reference for cookie capture)
- `scripts/woolworths/explore_woolworths_api.py` -- Original API exploration
- `data/part2_cookies.json` -- Saved Greymouth/Glenfield cookie jars for reference
- `data/woolworths_store_choices.csv` -- Store ID -> name mapping