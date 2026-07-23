import cloudscraper
import pandas as pd
import time
import os
import json
from bs4 import BeautifulSoup

BASE = "https://api-prod.prod.fsniwaikato.kiwi/prod"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', 'data'))

def get_new_world_stores_from_api():
    scraper = cloudscraper.create_scraper()
    r = scraper.post(
        f"{BASE}/mobile/user/login/guest",
        json={"banner": "MNW"},
        headers={"User-Agent": "NewWorldApp/4.32.0", "Content-Type": "application/json"},
    )
    r.raise_for_status()
    # Generate credentials for /mobile/store/physical (Same structure as Pak'nSave API)
    token = r.json()["access_token"]
    auth = {
        "Authorization": f"Bearer {token}",
        "access_token": token,
        "User-Agent": "NewWorldApp/4.32.0",
        "Content-Type": "application/json",
    }
    # Get the store ID, name, address, location, region, and other store meta-data
    r2 = scraper.get(f"{BASE}/mobile/store/physical", headers=auth, timeout=30)
    r2.raise_for_status()
    stores = r2.json()["stores"]
    nw_stores = [s for s in stores if s.get("banner") == "MNW"]
    print(f"Found {len(nw_stores)} New World stores from mobile API")
    return nw_stores

def get_store_urls_from_page():
    # 23/07/2026 Note: 7 stores currently missing from this the store finder list (cause not found):
        # Foodie Mart,
        # New World Metro Auckland,
        # New World Metro Willis St,
        # New World Mount Maunganui,
        # New World Shore City,
        # New World Turangi,
        # New World Wanaka
    scraper = cloudscraper.create_scraper()
    url = "https://www.newworld.co.nz/store-finder"
    r = scraper.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    script = soup.find("script", {"id": "__NEXT_DATA__"})
    if not script:
        raise RuntimeError("Could not find __NEXT_DATA__")
    data = json.loads(script.string)
    store_groups = data["props"]["pageProps"]["page"]["page_content"]["content_blocks"][1]["store_finder"]["regionStoreGroupings"]
    url_map = {}
    for group_key in ["northIsland", "southIsland"]:
        for group in store_groups[group_key]:
            for store in group["stores"]:
                name = store["title"]
                url_map[name] = {
                    "url": store["url"],
                    "address": store["address"],
                }
    print(f"Found {len(url_map)} stores from store-finder page")
    return url_map

def main():
    api_stores = get_new_world_stores_from_api()
    page_stores = get_store_urls_from_page()

    rows = []
    for store in api_stores:
        name = store["name"]
        address = store["address"]
        lat = store.get("latitude")
        lon = store.get("longitude")
        store_id = store.get("id")

        page_data = page_stores.get(name.replace("New World ", ""), {})
        url = page_data.get("url", "")
        page_address = page_data.get("address", "") # Redundant information

        if not lat or not lon:
            search_addr = f"{address}, New Zealand"
            print(f"  Missing coords for {name}: {search_addr}")

        rows.append({
            "store_id": store_id,
            "name": name,
            "url": url,
            "address": address,
            "latitude": lat,
            "longitude": lon,
            "banner": store.get("banner", "MNW"),
            "click_and_collect": store.get("clickAndCollect", False),
            "delivery": store.get("delivery", False),
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("name").reset_index(drop=True)
    output_path = os.path.join(DATA_DIR, "newworld_stores.csv")
    df.to_csv(output_path, index=False)
    print(f"\nSaved {len(df)} stores to {output_path}")
    print(f"With coordinates: {df.latitude.notna().sum()}")
    print(f"With store_id: {df.store_id.notna().sum()}")
    print(f"With URL: {df.url.notna().sum()}")

    missing_coords = df[df.latitude.isna()]
    if len(missing_coords) > 0:
        print(f"\nStores still missing coordinates ({len(missing_coords)}):")
        for _, row in missing_coords.iterrows():
            print(f"  {row['name']}: {row['address']}")

if __name__ == "__main__":
    main()
