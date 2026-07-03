import time, json
from playwright.sync_api import sync_playwright

URL = "https://www.woolworths.co.nz/"
SEARCH_TERM = "milk"
OUT_DIR = "../../Temp"
os.makedirs(OUT_DIR, exist_ok=True)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-default-browser-check",
            ],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            locale="en-NZ",
            timezone_id="Pacific/Auckland",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        print("Navigating to homepage...")
        resp = page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
        print(f"Homepage status: {resp.status}")
        print(f"Homepage final URL: {page.url}")

        # Intercept navigation to search page
        print("\nNavigating directly to search results page...")
        search_url = f"{URL}shop/searchproducts?search={SEARCH_TERM}"
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(12)
        print(f"Search final URL: {page.url}")
        print(f"Search title: {page.title()}")

        # dump window.location and document state
        state = page.evaluate("""() => {
            return {
                url: location.href,
                title: document.title,
                bodyLen: document.body.innerHTML.length,
                scripts: Array.from(document.querySelectorAll('script')).map(s => s.src || s.textContent.slice(0, 200)).slice(0,20),
                forms: Array.from(document.querySelectorAll('form')).map(f => ({action: f.action, method: f.method, inputs: Array.from(f.querySelectorAll('input')).map(i => ({name:i.name, value:i.value}))})).slice(0,20)
            };
        }""")
        print("=== STATE ===")
        print(json.dumps(state, indent=2)[:3000])

        # Dump full search HTML to inspect raw response
        html = page.content()
        out = f"{OUT_DIR}/woolworths_search_full.html"
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\nSaved full search HTML -> {out}")
        print(f"Length: {len(html)}")

        # check for inline JSON blobs
        subs = []
        for marker in ["window.__INITIAL_STATE__", "window.__APOLLO_STATE__", "window.__NEXT_DATA__", "self.__next_f", "ng-state"]:
            idx = html.find(marker)
            if idx != -1:
                subs.append(marker)
                snippet = html[idx:idx+1000]
                print(f"Found {marker} snippet: {snippet[:200]}...")
        if not subs:
            print("No standard app-state markers found.")

        # innerText of body to inspect whether product info rendered
        body_text = page.evaluate("document.body.innerText")
        print("\n=== BODY TEXT SAMPLE ===")
        print(body_text[:2000])

        browser.close()


if __name__ == "__main__":
    run()
