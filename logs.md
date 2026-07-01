# Major Errors & Resolutions

## 1. POST /CommonApi/Store/GetStoreList returns 307 → 404

**Symptom**: Hitting `https://www.paknsave.co.nz/CommonApi/Store/GetStoreList` returns a 307 redirect, which then 404s.

**Cause**: Vercel redirects mixed-case paths to lowercase. Next.js catches the lowercased route instead of proxying to the .NET backend.

**Resolution**: Do not use this endpoint. Use the mobile API (`/mobile/store/physical`) or the CSV fallback instead.

## 2. Algolia search keys not accessible

**Symptom**: Tried to use Algolia for product search directly. JS bundles are minified and keys are not exposed.

**Cause**: Algolia search keys are set server-side, not embedded in client JS.

**Resolution**: Use the Foodstuffs mobile API for product search instead.

## 3. Loose Garlic pricing ($40+/kg)

**Symptom**: Searching "garlic" returns "Loose Garlic" priced at $39.99/kg, making a single bulb appear extremely expensive.

**Cause**: The API returns per-kg pricing for loose items. The first result is loose garlic, not pre-packaged crushed garlic.

**Resolution**: Accept that some items have misleading per-kg pricing. The crushed garlic jar ($2.29) is a more practical result and sometimes appears instead. This is a known limitation.

## 4. `cloudscraper` not in requirements.txt

**Symptom**: `ModuleNotFoundError: No module named 'cloudscraper'` when running scripts after a fresh `pip install -r requirements.txt`.

**Cause**: `cloudscraper` was added to the code but never added to `requirements.txt`.

**Resolution**: Install manually with `pip install cloudscraper`. Should be added to `requirements.md` (now renamed from `requirements.txt`).

## 5. Store slug matching failures

**Symptom**: Some stores didn't match between the store-finder page slugs and the `__NEXT_DATA__` GUIDs.

**Cause**: Slug generation from store names doesn't always match the URL slugs on the website (e.g., apostrophes, "MINI" prefix, "-city" suffix).

**Resolution**: Hardcoded fallback mappings in `fetch_stores.py` for known mismatches (e.g., Henderson → "alderman-drive-henderson"). Not fully automated — manual verification needed for new stores.

## 6. Nominatim geocoding returning None

**Symptom**: `geocode()` returns `(None, None)` for some addresses.

**Cause**: Nominatim doesn't recognize the address format, or the address is too vague.

**Resolution**: The `fetch_stores.py` script has a fallback that tries `"Pak'nSave {name}, New Zealand"` as an alternative query. For user addresses, they need to provide a recognizable NZ address.
