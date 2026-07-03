import os, re
p = os.path.join("..", "..", "Temp", "woolworths_search_dom.html")
html = open(p, "r", encoding="utf-8").read()
print("Length:", len(html))
for pat in ["product-price", "price", "cents", "Search", "searchTerm", "milk", "resultsGrid", "noUi", "productList", "section-"]:
    hits = len(re.findall(pat, html, re.IGNORECASE))
    print(f"{pat}: {hits}")
print("data-test=product count:", html.count('data-test="product'))
print("data-test=price count:", html.count('data-test="price"'))
print("product-card count:", html.count('product-card'))
# print sample around first product-class match
idx = html.find('"product')
if idx != -1:
    print("Snippet around product:", html[idx-200:idx+500])
else:
    print("No 'product' substring found in HTML")
