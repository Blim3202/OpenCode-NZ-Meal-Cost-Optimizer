# 🛒 NZ Meal Cost Optimizer

Find the cheapest Pak'nSave or Woolworths for a given dish by comparing ingredient prices across nearby stores in New Zealand.

## 🚀 Proof of Concept (PoC)
Check out our Pak'nSave live dashboard: [NZ Meal Cost Optimizer Dashboard](https://nz-mealcost-optimizer-587140610895.asia-southeast1.run.app)

This dashboard is a **Proof of Concept** demonstrating:
- **LLM Integration:** Semantic searching, retrieval, and smart filtering of products.
- **Backend Pipeline:** Automated API calls and reliable data extraction.
- **Geocoding:** Precise store identification using Nominatim.

## 💡 How It Works
1. **Input:** User provides an address and a dish.
2. **Geocoding:** Converts address to coordinates.
3. **Store Filtering:** Filters supermarkets within a 5km radius.
4. **Price Comparison:** Automates ingredient price extraction from Pak'nSave (API) and Woolworths (Playwright-headed scraping).
5. **Analysis:** Calculates the cheapest total cost for your dish.

## 🛠 Tech Stack
- **Python**
- **Playwright** (for Woolworths scraping)
- **Requests / Cloudscraper** (for API interactions)
- **Pandas / NumPy** (for data processing)
- **JupyterLab** (experimental environment)
- **LLMs** (for semantic product filtering)

## ⚠️ Disclaimer
This is an **experimental, personal project**. It is not affiliated with or endorsed by Pak'nSave, Woolworths, or any other supermarket chain. Functionality depends on the stability of their websites and APIs; scraping techniques may break without notice.
