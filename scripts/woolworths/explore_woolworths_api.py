import requests
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

# Section	Purpose
# A)	Calls target=search for each of the 7 ingredients from spaghetti bolognese — verifies search returns real products, prints name/brand/SKU/price for the first 2 results
# B)	Calls target=search&page=2 for "milk" — verifies pagination works and checks totalItems to see how many results exist in total
# C)	Tries target=browse with a dasFilter param (taken directly from the GitHub code) — to see if browse responses can filter by department
# D)	Calls /api/v1/shell and prints every department name + URL — to map out the full taxonomy for possible dasFilter use

BASE = "https://www.woolworths.co.nz"
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-NZ,en;q=0.9",
    "x-requested-with": "??",
})

session.get(BASE, timeout=10)


def search(term, size=5, **extra):
    params = {
        "target": "search",
        "search": term,
        "inStockProductsOnly": "false",
        "size": size,
    }
    params.update(extra)
    r = session.get(f"{BASE}/api/v1/products", params=params, timeout=10)
    return r.status_code, r.json()


ingredients = ["beef mince", "spaghetti", "tomatoes canned", "onion", "garlic", "cheese", "rice"]

print("=" * 60)
print("A) Search each ingredient (size=3)")
print("=" * 60)
for ing in ingredients:
    code, data = search(ing, size=3)
    items = data.get("products", {}).get("items", [])
    print(f"\n{ing!r} -> {len(items)} products (HTTP {code})")
    for p in items[:2]:
        price = p.get("price", {})
        print(f"  - {p.get('name')}  brand={p.get('brand')}  sku={p.get('sku')}  "
              f"sale=${price.get('salePrice')}  orig=${price.get('originalPrice')}  unit={p.get('unit')}")
    time.sleep(0.3)


print("\n" + "=" * 60)
print("B) Search 'milk' - check page=2 (HTTP 200 expected)")
print("=" * 60)
code, data = search("milk", size=10, page=2)
items = data.get("products", {}).get("items", [])
print(f"  HTTP {code}  items={len(items)}  totalItems={data.get('products', {}).get('totalItems')}")
for p in items[:3]:
    price = p.get("price", {})
    print(f"  - {p.get('name')}  sale=${price.get('salePrice')}  unit={p.get('unit')}")


print("\n" + "=" * 60)
print("C) Try 'browse' target with a dasFilter")
print("=" * 60)
code, data = search(
    "milk",
    target="browse",
    dasFilter="Department;;poultry-and-meat;false",
    size=5, page=1
)
items = data.get("products", {}).get("items", [])
print(f"  HTTP {code}  items={len(items)}  keys={list(data.keys())}")
print(f"  dasFacets present={'dasFacets' in data}")


print("\n" + "=" * 60)
print("D) Inspect /api/v1/shell taxonomy (department names)")
print("=" * 60)
r = session.get(f"{BASE}/api/v1/shell", timeout=10)
shell = r.json()
navs = shell.get("mainNavs", [])
print(f"  mainNavs count: {len(navs)}")
for nav in navs:
    label = nav.get("label", "")
    for ni in nav.get("navigationItems", [{}]):
        for it in ni.get("items", [])[:10]:
            print(f"  [{label}] {it.get('label')}  url={it.get('url')}")
