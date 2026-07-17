import json
import requests
import time
import os
from pathlib import Path

BASE_URL = "https://www.woolworths.co.nz/api/v1"
SITE_URL = "https://www.woolworths.co.nz/"

HEADERS = {
    "x-requested-with": "??",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-NZ,en;q=0.9",
    "Referer": "https://www.woolworths.co.nz/",
}

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _load_store_mapping():
    """Load fulfilmentStoreId mapping from woolworths_store_data.json.

    Returns dict: {pickupAddressId (str): {fulfilmentStoreId (int), name (str)}}
    """
    store_data_path = DATA_DIR / "woolworths_store_data.json"
    if not store_data_path.exists():
        raise FileNotFoundError(f"Store data not found: {store_data_path}")

    with open(store_data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    mapping = {}
    for detail in data.get("siteDetail", []):
        site = detail.get("site", {})
        extra1 = site.get("extra1")
        extra2 = site.get("extra2")
        name = site.get("name", "")
        lat = site.get("latitude")
        lon = site.get("longitude")

        if extra1 and extra2 and str(extra1) != "null" and str(extra2) != "null":
            mapping[str(extra2)] = {
                "fulfilmentStoreId": int(extra1),
                "name": name,
                "lat": lat,
                "lon": lon,
            }
    return mapping


STORE_MAPPING = None


def get_store_mapping():
    """Return the store mapping, loading it once on first call."""
    global STORE_MAPPING
    if STORE_MAPPING is None:
        STORE_MAPPING = _load_store_mapping()
    return STORE_MAPPING


def create_session():
    """Create a requests.Session with Woolworths headers and seed cookies."""
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get(SITE_URL, timeout=15)
    return session


def set_store_context(session, pickup_address_id):
    """Set per-store pricing by injecting the cw-lrkswrdjp cookie.

    Args:
        session: requests.Session (must already have baseline cookies from create_session)
        pickup_address_id: str or int — the store's pickupAddressId from pickup-addresses API

    Returns:
        dict with fulfilmentStoreId, method, storeName

    Raises:
        ValueError: if store not found in mapping
        RuntimeError: if cookie injection didn't take effect
    """
    mapping = get_store_mapping()
    store = mapping.get(str(pickup_address_id))
    if not store:
        raise ValueError(f"Store {pickup_address_id} not in mapping")

    fsid = store["fulfilmentStoreId"]
    cookie_val = f"dm-Pickup,f-{fsid},s-38"
    session.cookies.set("cw-lrkswrdjp", cookie_val, domain="www.woolworths.co.nz", path="/")

    # Validate via shell
    resp = session.get(f"{BASE_URL}/shell", timeout=15)
    shell = resp.json()
    fulf = shell.get("context", {}).get("fulfilment", {})
    if fulf.get("fulfilmentStoreId") == 9171:
        raise RuntimeError(
            f"Cookie not accepted — shell still shows default store 9171. "
            f"Expected fulfilmentStoreId {fsid}."
        )

    return {
        "fulfilmentStoreId": fulf.get("fulfilmentStoreId"),
        "method": fulf.get("method"),
        "storeName": store["name"],
    }


def search_products(session, query, size=20):
    """Search for products with the current store context.

    Returns list of product dicts with keys: sku, name, salePrice, originalPrice,
    isSpecial, unitPrice, url, imageUrl.
    """
    resp = session.get(
        f"{BASE_URL}/products",
        params={"target": "search", "search": query, "size": size},
        timeout=15,
    )
    data = resp.json()
    items = data.get("products", {}).get("items", [])
    results = []
    for item in items:
        price_info = item.get("price", {})
        results.append({
            "sku": item.get("sku"),
            "name": item.get("name", ""),
            "salePrice": price_info.get("salePrice"),
            "originalPrice": price_info.get("originalPrice"),
            "isSpecial": price_info.get("isSpecial", False),
            "unitPrice": item.get("cupPrice", ""),
            "url": item.get("url", ""),
            "imageUrl": item.get("imageUrl", ""),
        })
    return results


def find_cheapest(session, query, size=20):
    """Search and return the cheapest product for a query.

    Returns dict with product info and price, or None if nothing found.
    """
    products = search_products(session, query, size=size)
    if not products:
        return None

    priced = [p for p in products if p["salePrice"] is not None]
    if not priced:
        return None

    cheapest = min(priced, key=lambda p: p["salePrice"])
    return cheapest


def get_nearby_stores(user_lat, user_lon, max_dist_km=5):
    """Return stores within max_dist_km, sorted by distance.

    Returns list of dicts: {pickupAddressId, name, fulfilmentStoreId, lat, lon, distance_km}
    """
    import math

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        return R * 2 * math.asin(math.sqrt(a))

    mapping = get_store_mapping()
    nearby = []
    for pid, info in mapping.items():
        if info["lat"] is None or info["lon"] is None:
            continue
        dist = haversine(user_lat, user_lon, info["lat"], info["lon"])
        if dist <= max_dist_km:
            nearby.append({
                "pickupAddressId": pid,
                "name": info["name"],
                "fulfilmentStoreId": info["fulfilmentStoreId"],
                "lat": info["lat"],
                "lon": info["lon"],
                "distance_km": round(dist, 2),
            })
    nearby.sort(key=lambda s: s["distance_km"])
    return nearby


def geocode(address):
    """Geocode a NZ address via Nominatim. Returns (lat, lon) or (None, None)."""
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        headers={"User-Agent": "NZMealCostOptimizer/1.0"},
        params={"q": address, "format": "json", "limit": 1},
    )
    if r.status_code == 200 and r.json():
        loc = r.json()[0]
        return float(loc["lat"]), float(loc["lon"])
    return None, None
