from bs4 import BeautifulSoup
import pandas as pd

# 1. Read the HTML file (make sure it's in the same folder)
with open('scripts/woolworths/All Stores Extracted HTML Element.txt', 'r', encoding='utf-8') as f:
    html = f.read()

# 2. Parse with BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')

stores = []

# 3. Find every store item
for li in soup.find_all('li', class_='addressList-item'):
    # Name
    name_tag = li.find('strong', class_='addressList-title')
    name = name_tag.get_text(strip=True) if name_tag else ''
    
    # Subtitle
    sub_tag = li.find('span', class_='addressList-subtitle')
    if sub_tag:
        raw = sub_tag.get_text()                     # gets text with normal spaces
        clean = raw.replace('\xa0', ' ').strip()    # replace non‑breaking spaces
        parts = [p.strip() for p in clean.split(',') if p.strip()]
    else:
        parts = []
    
    # Pad to exactly 5 address fields
    addresses = (parts + [''] * 5)[:5]
    
    stores.append({
        'Name': name,
        'Address 1': addresses[0],
        'Address 2': addresses[1],
        'Address 3': addresses[2],
        'Address 4': addresses[3],
        'Address 5': addresses[4],
    })

# 4. Create DataFrame and show it
df = pd.DataFrame(stores)
print(df.head(200))          # preview first few rows

# 5. Save to CSV
df.to_csv('data\woolworths_all_stores.csv', index=False, encoding='utf-8-sig') #encoding for emdashes
print("Saved to woolworths_all_stores.csv")