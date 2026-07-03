import cloudscraper
import json
import re
import time

import pandas as pd
import requests

DATA_DIR = "../data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

scraper = cloudscraper.create_scraper()
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0"}

# ── Step 1: Extract GUIDs from __NEXT_DATA__ ──────────────────────
print("Fetching homepage __NEXT_DATA__...")
r = scraper.get("https://www.paknsave.co.nz/", headers=headers)
match = re.search(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    r.text,
    re.DOTALL,
)
if not match:
    raise SystemExit("Could not find __NEXT_DATA__")

data = json.loads(match.group(1))
page_props = data["props"]["pageProps"]
cs_stores = page_props.get("contentstackStores", [])

slug_guid_map = {}
for item in cs_stores:
    uid = item.get("uid", "")
    url = item.get("url", "")
    if url:
        slug = url.rstrip("/").split("/")[-1]
        slug_guid_map[slug] = uid

print(f"Loaded {len(slug_guid_map)} GUIDs from __NEXT_DATA__")
print(f"Slugs: {list(slug_guid_map.keys())[:5]}...")

# ── Step 2: Get store names/addresses from store-finder page ──────
print("\nFetching store-finder page...")
r2 = scraper.get("https://www.paknsave.co.nz/store-finder", headers=headers)

# Extract store data from the locations list script
locations_match = re.search(
    r'var locations\s*=\s*(\[.*?\]);',
    r2.text,
    re.DOTALL,
)
store_entries = []
if locations_match:
    locations = json.loads(locations_match.group(1))
    for loc in locations:
        name = loc.get("name", "").replace("PAK'nSAVE ", "")
        address = loc.get("address", "")
        parts = [p.strip() for p in address.split(",")]
        street = parts[0] if len(parts) > 0 else ""
        city = parts[-1] if len(parts) > 0 else street
        region = ""
        for part in parts:
            if part in ("Auckland", "Hamilton", "Wellington", "Christchurch", "Tauranga", "Napier", "Dunedin", "Lower Hutt", "Porirua", "New Plymouth", "Invercargill"):
                region = part
                break
        store_entries.append({
            "name": name,
            "address": address,
            "street": street,
            "city": city,
            "region": region,
        })
else:
    # Fallback: parse the HTML
    items = re.findall(
        r'<h3[^>]*>(.*?)</h3>.*?<p[^>]*>(.*?)</p>',
        r2.text,
        re.DOTALL,
    )
    for name, addr in items:
        name = re.sub(r'<[^>]+>', "", name).replace("PAK'nSAVE ", "").strip()
        addr = re.sub(r'<[^>]+>', "", addr).strip()
        store_entries.append({
            "name": name,
            "address": addr,
            "street": addr.split(",")[0].strip(),
            "city": addr.split(",")[-1].strip(),
            "region": "",
        })

print(f"Found {len(store_entries)} stores from store-finder")

# ── Step 3: Match slugs to GUIDs ──────────────────────────────────
# Build slug from store name
def name_to_slug(name):
    name_clean = re.sub(r"'s\b", "", name)
    slug = name_clean.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug

for entry in store_entries:
    slug = name_to_slug(entry["name"])
    # Try different slug patterns
    guess = slug
    if guess not in slug_guid_map:
        # Try with MINI prefix
        guess_alt = f"mini-{slug}"
        if guess_alt in slug_guid_map:
            guess = guess_alt
        elif slug.endswith("-city"):
            guess = slug.replace("-city", "")
        elif "henderson" in slug:
            guess = "alderman-drive-henderson"

    entry["store_id"] = slug_guid_map.get(guess, "")

# ── Step 4: Geocode addresses ─────────────────────────────────────
print(f"\nGeocoding stores with Nominatim...")
geo_headers = {"User-Agent": "NZMealCostOptimizer/1.0 (research project)"}
for i, entry in enumerate(store_entries, 1):
    name = entry["name"]
    address = entry["address"]
    print(f"  [{i}/{len(store_entries)}] {name}: ", end="")

    params = {"q": address, "format": "json", "limit": 1}
    resp = scraper.get(
        "https://nominatim.openstreetmap.org/search",
        headers=geo_headers,
        params=params,
    )
    if resp.status_code == 200 and resp.json():
        loc = resp.json()[0]
        entry["latitude"] = float(loc["lat"])
        entry["longitude"] = float(loc["lon"])
        print(f"{entry['latitude']}, {entry['longitude']}")
    else:
        # Fallback: try Pak'nSave {name}
        alt_q = f"Pak'nSave {name}, New Zealand"
        params["q"] = alt_q
        resp2 = scraper.get(
            "https://nominatim.openstreetmap.org/search",
            headers=geo_headers,
            params=params,
        )
        if resp2.status_code == 200 and resp2.json():
            loc = resp2.json()[0]
            entry["latitude"] = float(loc["lat"])
            entry["longitude"] = float(loc["lon"])
            print(f"{entry['latitude']}, {entry['longitude']} (alt)")
        else:
            entry["latitude"] = None
            entry["longitude"] = None
            print("None, None")

    time.sleep(1.1)

# ── Step 5: Save to CSV ───────────────────────────────────────────
df = pd.DataFrame(store_entries)
df = df[["store_id", "name", "address", "city", "region", "latitude", "longitude"]]
df.columns = ["store_id", "name", "address", "city", "region", "latitude", "longitude"]
df.to_csv(f"{DATA_DIR}/paknsave_stores.csv", index=False)

print(f"\nSaved {len(df)} stores to {DATA_DIR}/paknsave_stores.csv")
print(f"Stores with coords: {df['latitude'].notna().sum()} / {len(df)}")

# Print table
pd.set_option("display.max_columns", 10)
pd.set_option("display.width", 120)
pd.set_option("display.max_colwidth", 30)
print(df[["name", "address", "latitude", "longitude"]].to_string(index=False))
