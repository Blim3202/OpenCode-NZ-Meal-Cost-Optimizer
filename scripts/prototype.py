import cloudscraper
import pandas as pd
import requests
import math
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
stores_csv = pd.read_csv(DATA_DIR / "paknsave_stores.csv")

BASE = "https://api-prod.prod.fsniwaikato.kiwi/prod"

class PaknSaveAPI:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        self._token = None

    def _ensure_token(self):
        if self._token:
            return
        r = self.scraper.post(
            f"{BASE}/mobile/user/login/guest",
            json={"banner": "PNS"},
            headers={"User-Agent": "PAKnSAVEApp/4.32.0", "Content-Type": "application/json"},
        )
        r.raise_for_status()
        data = r.json()
        self._token = data["access_token"]
        self._auth = {
            "Authorization": f"Bearer {self._token}",
            "access_token": self._token,
            "User-Agent": "PAKnSAVEApp/4.32.0",
            "Content-Type": "application/json",
        }

    def search_products(self, store_id: str, query: str):
        self._ensure_token()
        r = self.scraper.post(
            f"{BASE}/mobile/ecomm-products/PNS/{store_id}/search?q={query}",
            headers=self._auth, json=[],
        )
        if r.status_code == 200:
            return r.json()
        return None

    def get_stores(self):
        self._ensure_token()
        r = self.scraper.get(f"{BASE}/mobile/store/physical", headers=self._auth)
        if r.status_code == 200:
            return {s["id"]: s for s in r.json()["stores"]}
        return {}

api = PaknSaveAPI()

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

def find_nearby(user_lat, user_lon, radius_km=5):
    df = stores_csv.copy()
    df["distance_km"] = df.apply(
        lambda r: haversine(user_lat, user_lon, r["latitude"], r["longitude"]),
        axis=1,
    )
    return df[df["distance_km"] <= radius_km].sort_values("distance_km")

DISH_INGREDIENTS = {
    "spaghetti bolognese": ["beef mince", "spaghetti pasta", "canned tomatoes", "onion", "carrot", "garlic", "mixed herbs"],
    "chicken stir fry": ["chicken breast", "stir fry vegetables", "soy sauce", "rice noodles"],
    "beef stir fry": ["beef strips", "stir fry vegetables", "soy sauce", "rice noodles"],
    "roast lamb": ["lamb roast", "potato", "carrot", "broccoli", "stock"],
    "chicken curry": ["chicken thigh", "curry paste", "coconut milk", "rice", "onion"],
    "beef curry": ["diced beef", "curry paste", "coconut milk", "rice", "onion"],
    "fish and chips": ["fish fillet", "potato", "oil"],
    "nachos": ["beef mince", "tortilla chips", "cheese", "beans", "sour cream"],
    "pumpkin soup": ["pumpkin", "onion", "cream", "stock", "bread"],
    "tacos": ["beef mince", "taco shells", "lettuce", "tomato", "cheese", "sour cream"],
    "lamb chops": ["lamb chops", "potato", "mint sauce", "mixed vegetables"],
    "butter chicken": ["chicken thigh", "butter chicken sauce", "rice", "cream"],
    "lasagne": ["beef mince", "lasagne sheets", "cheese", "canned tomatoes", "milk", "butter", "flour"],
    "shepherd's pie": ["beef mince", "potato", "carrot", "peas", "stock"],
    "pizza": ["pizza base", "pizza sauce", "cheese", "pepperoni"],
    "vegie stir fry": ["stir fry vegetables", "tofu", "soy sauce", "rice noodles", "garlic"],
    "frittata": ["eggs", "potato", "onion", "cheese", "milk"],
    "pancakes": ["flour", "eggs", "milk", "sugar", "butter"],
    "chicken soup": ["chicken breast", "carrot", "onion", "celery", "stock", "pasta"],
    "tomato pasta": ["pasta", "canned tomatoes", "garlic", "olive oil", "mixed herbs", "cheese"],
    "chicken katsu": ["chicken breast", "flour", "eggs", "bread", "rice", "katsu sauce"],
}

def get_ingredients(dish_name):
    key = dish_name.lower().strip()
    if key in DISH_INGREDIENTS:
        return DISH_INGREDIENTS[key]
    return [key]

def search_ingredient(store_id, ingredient):
    results = api.search_products(store_id, ingredient)
    if not results:
        return None
    products = results.get("products", [])
    if not products:
        return None
    p = products[0]
    price_cents = p.get("price")
    if price_cents is None or price_cents <= 0:
        return None
    return {
        "name": p["name"],
        "brand": p.get("brand", ""),
        "price": price_cents / 100,
        "units": p.get("units", ""),
        "product_id": p.get("productId", ""),
    }

if __name__ == "__main__":
    import sys
    USER_ADDRESS = sys.argv[1] if len(sys.argv) > 1 else "123 Queen Street, Auckland CBD, 1010"
    DISH_NAME = sys.argv[2] if len(sys.argv) > 2 else "spaghetti bolognese"
    MAX_DISTANCE_KM = 5

    user_lat, user_lon = geocode(USER_ADDRESS)
    if user_lat is None:
        print("Could not geocode address")
        sys.exit(1)
    print(f"Address: {USER_ADDRESS}")
    print(f"Coords: {user_lat:.5f}, {user_lon:.5f}")
    print()

    nearby = find_nearby(user_lat, user_lon, MAX_DISTANCE_KM)
    if nearby.empty:
        print(f"No stores within {MAX_DISTANCE_KM}km")
        sys.exit(1)

    # Get API store data for accurate store names and coords
    api_stores = api.get_stores()

    print(f"Nearby stores ({len(nearby)} within {MAX_DISTANCE_KM}km):")
    for _, s in nearby.iterrows():
        sid = s["store_id"]
        api_name = api_stores.get(sid, {}).get("name", s["name"])
        print(f"  {api_name:35s} {s['distance_km']:.2f} km")
    print()

    ingredients = get_ingredients(DISH_NAME)
    print(f"Dish: {DISH_NAME}")
    print(f"Ingredients: {', '.join(ingredients)}")
    print()

    all_results = []
    for _, store in nearby.iterrows():
        store_id = store["store_id"]
        store_name = api_stores.get(store_id, {}).get("name", store["name"])
        print(f"--- {store_name} ---")
        total = 0.0
        for ing in ingredients:
            result = search_ingredient(store_id, ing)
            if result:
                all_results.append({**result, "store": store_name, "ingredient": ing, "distance_km": store["distance_km"]})
                print(f"  {ing:25s} {result['price']:>6.2f}  {result['name'][:50]}")
                total += result["price"]
            else:
                print(f"  {ing:25s}  NOT FOUND")
        print(f"  {'TOTAL':25s} {total:>6.2f}")
        print()

    if all_results:
        df = pd.DataFrame(all_results)
        summary = df.groupby("store").agg(
            total_cost=("price", "sum"),
            items_found=("ingredient", "count"),
            distance_km=("distance_km", "first"),
        ).sort_values("total_cost")
        print("=" * 60)
        print("COST COMPARISON")
        print("=" * 60)
        print(summary.to_string())
        print()
        best_store = summary.index[0]
        best_total = summary["total_cost"].iloc[0]
        print(f"Cheapest: {best_store} — ${best_total:.2f} total")

        # Show itemized for best store
        best_items = df[df["store"] == best_store]
        print(f"\nItemized ({best_store}):")
        for _, row in best_items.iterrows():
            print(f"  {row['ingredient']:25s} ${row['price']:.2f}  {row['name']} ({row['units']})")
