import sys
import pandas as pd
import math
import requests
import time
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

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

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))

def load_and_filter_stores(user_lat, user_lon, stores_csv_path, max_dist_km=5):
    stores_csv = Path(stores_csv_path)
    if not stores_csv.exists():
        print(f"Error: Woolworths store data not found at {stores_csv_path}")
        sys.exit(1)
    df = pd.read_csv(stores_csv)
    df["distance_km"] = df.apply(
        lambda r: haversine(user_lat, user_lon, r["latitude"], r["longitude"]),
        axis=1,
    )
    return df[df["distance_km"] <= max_dist_km].sort_values("distance_km")

DISH_INGREDIENTS = {
    "spaghetti bolognese": ["beef mince", "spaghetti pasta", "canned tomatoes", "onion", "carrot", "garlic", "mixed herbs"],
}

DISH_QUANTITIES = {
    "spaghetti bolognese": {
        "beef mince": "500g",
        "spaghetti pasta": "400g",
        "canned tomatoes": "1 can (400g)",
        "onion": "1 medium",
        "carrot": "2 medium",
        "garlic": "2 cloves",
        "mixed herbs": "1 tsp",
    },
}

def get_ingredients(dish_name):
    return DISH_INGREDIENTS.get(dish_name.lower(), [])

def get_quantities(dish_name):
    return DISH_QUANTITIES.get(dish_name.lower(), {})

async def change_store(page, store_name):
    MODAL_URL = "https://www.woolworths.co.nz/bookatimeslot/(hww-modal:change-pick-up-store)"
    await page.goto(MODAL_URL, wait_until="domcontentloaded")
    dropdown_selector = 'select[id*="area-dropdown"]'
    await page.wait_for_selector(dropdown_selector)
    await page.locator(dropdown_selector).select_option(label="All Pick up locations")
    await asyncio.sleep(2) 
    store_btn = page.get_by_role("button", name=store_name)
    await store_btn.wait_for(state="visible")
    await store_btn.click()
    await asyncio.sleep(2)

async def scrape_products(page, ingredient, limit=20):
    url = f"https://www.woolworths.co.nz/shop/searchproducts?search={ingredient}"
    await page.goto(url, wait_until="domcontentloaded")
    await asyncio.sleep(5)
    return await page.evaluate("""(limit) => {
        const entries = Array.from(
            document.querySelectorAll('product-stamp-grid .product-entry')
        );
        const out = [];
        for (const el of entries.slice(0, limit)) {
            try {
                const titleEl = el.querySelector('h3[id$="-title"]');
                const unitEl  = el.querySelector('[id$="-unitPrice"] .cupPrice');
                const priceEl = el.querySelector('[id$="-price"]');
                const name = titleEl ? titleEl.innerText.trim() : '';
                const unit = unitEl ? unitEl.innerText.trim() : '';
                const price = priceEl
                    ? (priceEl.getAttribute('aria-label') || priceEl.innerText || '')
                    : '';
                out.push({ name, unitPrice: unit, actualPrice: price });
            } catch (_) { /* skip broken entries */ }
        }
        return out;
    }""", limit)

def analyze_results(df, ingredients, dish_name):
    # Perform numeric conversion
    df['price_float'] = df['actualPrice'].str.extract(r'(\d+\.?\d*)').astype(float)
    
    # --- COST COMPARISON SUMMARY ---
    cheapest_per_ing_per_store = df.groupby(["store", "ingredient"])["price_float"].min().reset_index()
    summary = cheapest_per_ing_per_store.groupby("store")["price_float"].sum().reset_index()
    summary.columns = ["store", "total_cost"]
    summary = summary.set_index("store").sort_values("total_cost")
    
    # --- PER-STORE BREAKDOWN ---
    store_names = sorted(df["store"].unique())
    quantities = get_quantities(dish_name)
    
    rows = []
    for ing in ingredients:
        row = {"Ingredient": ing, "Qty": quantities.get(ing, "-")}
        for sn in store_names:
            match = df[(df["ingredient"] == ing) & (df["store"] == sn)]
            if not match.empty:
                best_prod = match.loc[match['price_float'].idxmin()]
                row[sn] = f"{best_prod['name'][:20]}...: ${best_prod['price_float']:.2f} ({best_prod['unitPrice']})"
            else:
                row[sn] = "NOT FOUND"

        prices = []
        for sn in store_names:
            match = df[(df["ingredient"] == ing) & (df["store"] == sn)]
            if not match.empty:
                prices.append((sn, match.loc[match['price_float'].idxmin()]["price_float"]))
        if prices:
            best_sn, best_px = min(prices, key=lambda x: x[1])
            row["Best Price"] = f"${best_px:.2f}"
            row["Best Store"] = best_sn
        else:
            row["Best Price"] = "-"
            row["Best Store"] = "-"
        rows.append(row)

    table = pd.DataFrame(rows).set_index("Ingredient")
    
    # Totals row
    totals = {"Qty": ""}
    for sn in store_names:
        store_total = df[df["store"] == sn].groupby("ingredient")["price_float"].min().sum()
        totals[sn] = f"${store_total:.2f}"
    
    best_total_mix = 0
    for ing in ingredients:
        ing_prices = df[df["ingredient"] == ing]["price_float"]
        if not ing_prices.empty:
            best_total_mix += ing_prices.min()
            
    totals["Best Price"] = f"${best_total_mix:.2f}"
    totals["Best Store"] = "(mix)"
    table.loc["TOTAL"] = totals
    
    return summary, table

async def main():
    # Allow passing arguments, or default
    if len(sys.argv) > 3:
        USER_ADDRESS = sys.argv[1]
        DISH_NAME = sys.argv[2]
        OUTPUT_FILE = sys.argv[3]
    else:
        USER_ADDRESS = "123 Queen Street, Auckland CBD, 1010"
        DISH_NAME = "spaghetti bolognese"
        OUTPUT_FILE = "data/latest_results.csv"

    user_lat, user_lon = geocode(USER_ADDRESS)
    
    # Path is relative to the script execution in this case
    stores = load_and_filter_stores(user_lat, user_lon, "data/woolworths_stores.csv").head(2)
    ingredients = get_ingredients(DISH_NAME)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        all_data = []
        for _, store in stores.iterrows():
            store_name = store['name']
            print(f"\n--- Store: {store_name} ---")
            await change_store(page, store_name)
            for ing in ingredients:
                print(f"  Scraping: {ing}")
                products = await scrape_products(page, ing)
                if products:
                    for product in products:
                        all_data.append({**product, "store": store_name, "ingredient": ing})
                        print(f"    Found: {product['name']} - {product['actualPrice']} ({product['unitPrice']})")
                else:
                    print("    Not found.")
        await browser.close()
        
    # Aggregate total cost per store
    all_results = all_data  # aliasing for easier logic
    df = pd.DataFrame(all_results)
    
    # Save to CSV for the notebook
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nResults saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
