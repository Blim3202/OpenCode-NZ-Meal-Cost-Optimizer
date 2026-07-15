import cloudscraper
import json
import re
import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8") # Just in case we get special characters (Māngere, Pāpāmoa, Whakatāne, etc.)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', 'data'))
os.makedirs(DATA_DIR, exist_ok=True)

scraper = cloudscraper.create_scraper()
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0"}

print("Fetching store-finder page __NEXT_DATA__...")
r = scraper.get("https://www.paknsave.co.nz/store-finder", headers=headers)

# All our data is stored in the __NEXT_DATA__ conveniently
match = re.search(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    r.text,
    re.DOTALL,
)
if not match:
    raise SystemExit("Could not find __NEXT_DATA__")

data = json.loads(match.group(1))
page_props = data["props"]["pageProps"]

# ── Step 1: Build url → store_id map from contentstackStores ──────
cs_stores = page_props.get("contentstackStores", [])
url_to_store_id = {}
for item in cs_stores:
    url = item.get("url", "")
    store_id = item.get("store_id", "")
    if url and store_id:
        url_to_store_id[url] = store_id

print(f"Loaded {len(url_to_store_id)} store_id mappings from contentstackStores")

# ── Step 2: Extract store details from store_finder.regionStoreGroupings ──
page = page_props.get("page", {})
content_blocks = page.get("page_content", {}).get("content_blocks", [])
store_finder_block = next(
    (b for b in content_blocks if "store_finder" in b),
    {},
)
store_finder = store_finder_block.get("store_finder", {})
region_groupings = store_finder.get("regionStoreGroupings", {})

store_entries = []
for island_key, region_label in [("northIsland", "NI"), ("southIsland", "SI")]:
    groups = region_groupings.get(island_key, [])
    for group in groups:
        stores = group.get("stores", [])
        for store in stores:
            title = store.get("title", "")
            url = store.get("url", "")
            address = store.get("address", "")
            contact = store.get("contactDetails") or {}
            latitude = contact.get("latitude")
            longitude = contact.get("longitude")

            store_id = url_to_store_id.get(url, "")

            city = address.split(",")[0].strip() if address else ""

            store_entries.append({
                "store_id": store_id,
                "name": title,
                "address": address,
                "city": city,
                "region": region_label,
                "latitude": latitude,
                "longitude": longitude,
            })

print(f"Found {len(store_entries)} stores from regionStoreGroupings")

# ── Step 3: Save to CSV ───────────────────────────────────────────
df = pd.DataFrame(store_entries)
df = df[["store_id", "name", "address", "city", "region", "latitude", "longitude"]]
output_path = os.path.join(DATA_DIR, "paknsave_stores.csv")
df.to_csv(output_path, index=False)

print(f"\nSaved {len(df)} stores to {output_path}")
print(f"Stores with coords: {df['latitude'].notna().sum()} / {len(df)}")

pd.set_option("display.max_columns", 10)
pd.set_option("display.width", 120)
pd.set_option("display.max_colwidth", 30)
print(df[["name", "address", "latitude", "longitude"]].to_string(index=False))

# Removed:
# - Separate store-finder HTML page fetch (r2)
# - Regex parsing of var locations JS array
# - HTML fallback parsing
# - Nominatim geocoding (entire Step 4 + requests + time imports)
# - Raw JSON debug print
# Kept:
# - contentstackStores extraction for GUID → URL mapping (now from the same page)
# Added:
# - Fetches /store-finder page instead of homepage (both contentstackStores and store_finder live in the same __NEXT_DATA__)
# - Navigation path: page.page_content.content_blocks[2].store_finder.regionStoreGroupings
# - Extracts title, url, address, contactDetails (lat/lon) directly — no geocoding needed
# - city derived from the URL path's second-to-last segment (e.g., /upper-north-island/auckland/albany → Auckland)
# - region set to NI or SI based on the island grouping key
# - sys.stdout.reconfigure(encoding="utf-8") for proper Unicode handling of macron characters (Māngere, Pāpāmoa, Whakatāne, etc.)