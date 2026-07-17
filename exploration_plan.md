# Woolworths Per-Store Pricing — Exploration Plan & Findings

## Objective
Find a way to set the Woolworths store context so `/api/v1/products` returns **per-store pricing** instead of the global price list tied to the default delivery address (Glenfield, $7.33 for 3L milk).

**Known price differential:**
- Greymouth store (pickup): Woolworths Milk Standard Bottle 3L = **$7.15**
- Glenfield store (pickup): Woolworths Milk Standard Bottle 3L = **$7.33**

---

## ✅ CONFIRMED FINDINGS (Phase 1 Complete)

### Finding 1: URL-param seeding does NOT work
Visiting `https://www.woolworths.co.nz/?pickupStoreId=764300` (or any combination of `pickupStoreId`, `storeId` URL params) does **NOT** change the milk price — all return $7.33. The store context is not set via URL parameters on the homepage.

### Finding 2: Full Playwright cookie injection WORKS
Capturing cookies via Playwright (headed) after selecting a store in the change-pick-up-store modal, then injecting those cookies into a `requests.Session`, returns correct per-store pricing:
- Greymouth (67 cookies injected): **$7.15** ✓
- Glenfield (67 cookies injected): **$7.33** ✓

### Finding 3: Neither session_state nor RT alone works
- `session_state` cookie only: both stores return $7.33 (wrong)
- `RT` cookie only: both stores return $7.33 (wrong)
- Both together (RT + session_state): not yet confirmed working

### Finding 4: Cookie domain breakdown (Greymouth)
| Domain | # Cookies | Example cookies |
|--------|-----------|-----------------|
| `.woolworths.co.nz` | 30 | `AKA_A2`, `rxVisitor`, `dtSa`, `dtPC` |
| `.www.woolworths.co.nz` | 1 | `RT` (Adobe Analytics) |
| `www.woolworths.co.nz` | 15 | `cw-ssuflow`, `agaCORS`, `aga...` |
| `.adnxs.com`, `.doubleclick.net`, etc. | many | Third-party ad/analytics |

### Finding 5: Only 1 cookie visible in filtered injection output
When all 67 cookies are injected in step 2, only 1 (`session_state`) appears in the filtered `cookie_jar_summary` output. This is because the filter checks for "woolworths"/"countdown" in the **name**, not domain. The other 66 cookies ARE in the jar but don't match the filter — they're likely `.woolworths.co.nz` scoped cookies being sent with API requests (explaining why step 2 works).

### Finding 6: Per-store pricing requires the full cookie ecosystem
The session_state cookie alone is not sufficient. The per-store pricing signal is likely carried by one or more cookies in the `.woolworths.co.nz` domain (30 cookies) — possibly `rxVisitor` (Tealium/Adobe browser ID, unique per session) or another persistent cookie that maps to store context server-side.

---

## Next Steps

### High Priority
1. **Test `session_state + rxVisitor` together**: `rxVisitor` is in `.woolworths.co.nz` domain and is unique per browser session — test if these two alone replicate per-store pricing
2. **Confirm whether all 67 cookies from `.woolworths.co.nz` domain are needed**: inject all Greymouth cookies and verify full price ($7.15)
3. **Persist cookie jars per store**: use Playwright to capture full cookie jars for all nearby stores, save to JSON, inject in optimizer

### Medium Priority
4. Test if navigating to `https://www.woolworths.co.nz/bookatimeslot/(hww-modal:change-pick-up-store)` with the `storeId` query parameter auto-selects the store in the JS, which might trigger the correct cookies to be set
5. Investigate whether `localStorage` or `sessionStorage` carries store context that must be replicated

### Architecture Decision Needed
The working approach is: Playwright visits store-selection modal → captures full cookie jar → injects into requests.Session → API returns per-store prices. This means:
- Each nearby store requires a Playwright session to capture its cookie jar
- Cookie jars can be persisted to disk and reused until expired
- When a jar fails (returns wrong price), refresh it with Playwright

---

## Pickup Store IDs (Known)

| Store | Pickup Address ID |
|-------|------------------|
| Greymouth | 764300 |
| Glenfield | 1190273 |
| Northlands | 1225718 |

Run `scripts/woolworths/Get_woolworths_store_choices.py` to get the full list.