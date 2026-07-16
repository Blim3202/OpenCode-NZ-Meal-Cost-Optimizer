import requests
import json
import csv
import os
import sys

# This API endpoint was manually discovered (by me) by inspecting network sources on webpage refreshes-
# while on the https://www.woolworths.co.nz/bookatimeslot/(hww-modal:change-pick-up-store) webpage and clicking store dropdown.
# It provides a JSON output of Woolworths (formerly Countdown) store names and IDs. Stores with pickup.

def main():
    # Config
    WOOLWORTHS_API_BASE_URL = "https://www.woolworths.co.nz/api/v1/addresses/pickup-addresses"
    DATA_DIR = "data"
    JSON_FILE = os.path.join(DATA_DIR, "woolworths_store_choices.json")
    CSV_FILE = os.path.join(DATA_DIR, "woolworths_store_choices.csv")
    
    # Headers 
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.woolworths.co.nz/bookatimeslot/(hww-modal:change-pick-up-store)",
        "X-Requested-With": "OnlineShopping.WebApp",
        "X-UI-Ver": "7.75.24",
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }

    # No params
    params = {}

    # Session with cookies
    session = requests.Session()
    session.headers.update(headers)

    # Fetch API
    try:
        session.get("https://www.woolworths.co.nz/bookatimeslot", timeout=20)
    except requests.RequestException as e:
        print(f"❌ Error visiting initial page: {e}")
        sys.exit(1)

    print(f"Fetching data from: {WOOLWORTHS_API_BASE_URL} with parameters {params}")
    try:
        response = session.get(WOOLWORTHS_API_BASE_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"❌ Error fetching data: {e}")
        sys.exit(1)

    # Ensure output directory 
    os.makedirs(DATA_DIR, exist_ok=True)

    # Save full raw JSON
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved raw JSON to {JSON_FILE}")



    # Extract target area (id=494, name="All Pick up locations")
    target_area = next(
        (area for area in data.get("storeAreas", [])
         if area.get("id") == 494 and area.get("name") == "All Pick up locations"),
        None
    )

    if not target_area:
        print("❌ Area not found")
        sys.exit(1)

    stores = target_area.get("storeAddresses", [])
    print(f"✅ Found {len(stores)} stores")


# Save filtered stores to CSV
    fieldnames = ["id", "name", "address"]
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for store in stores:
            writer.writerow({
                "id": store.get("id"),
                "name": store.get("name"),
                "address": store.get("address"),
            })

    print(f"✅ Saved {len(stores)} locations to {CSV_FILE}")

if __name__ == "__main__":
    main()