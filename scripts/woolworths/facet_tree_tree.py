import requests, sys, json, time

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://www.woolworths.co.nz"
API  = f"{BASE}/api/v1"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-NZ,en;q=0.9",
    "x-requested-with": "??",
})
session.get(BASE, timeout=10)

# Get top-level dept slugs from shell
r_shell = session.get(f"{API}/shell", timeout=10)
navs = r_shell.json().get("mainNavs", [])
browse_nav = next((n for n in navs if n.get("label") == "Browse"), {})
dept_items = []
for ni in browse_nav.get("navigationItems", [{}]):
    for it in ni.get("items", []):
        dept_items.append({
            "name": it.get("label"),
            "url":  it.get("url", ""),
            "slug": it.get("url", "").replace("/shop/browse/", ""),
        })

print(f"Departments to explore: {len(dept_items)}")
for d in dept_items:
    print(f"  {d['name']}  slug={d['slug']}")

# For each dept, fetch with dasFilter and capture aisles
print("\n\nFULL AISLE MAP PER DEPARTMENT:")
print("=" * 90)
full_map = {}
for dept in dept_items:
    slug = dept["slug"]
    if not slug:
        continue
    df = f"Department;;{slug};false"
    r = session.get(f"{API}/products",
                    params={"target": "browse", "dasFilter": df, "size": 1}, timeout=10)
    data = r.json()
    facets = data.get("dasFacets", [])
    aisles = []
    for f in facets:
        aisles.append({
            "key":       f.get("key"),
            "value":     f.get("value"),
            "name":      f.get("name"),
            "count":     f.get("productCount"),
            "isBoolean": f.get("isBooleanValue"),
            "shelves": [
                {"id": s.get("id"), "label": s.get("label"), "url": s.get("url")}
                for s in (f.get("shelfResponses") or [])
            ],
        })
    full_map[dept["name"]] = {"slug": slug, "aisles": aisles}
    print(f"\n  [{dept['name']}] slug={slug}  aisles={len(aisles)}")
    for a in aisles:
        shelf_str = ", ".join(f"{s['label']}(id={s['id']})" for s in a["shelves"][:3])
        print(f"    {a['key']}={a['value']}  {a['name']}  count={a['count']}  shelves=[{shelf_str}]")
    time.sleep(0.3)

# Save raw JSON for reference
with open("facet_tree.json", "w", encoding="utf-8") as f:
    json.dump(full_map, f, indent=2, ensure_ascii=False)
print("\nSaved to facet_tree.json")
