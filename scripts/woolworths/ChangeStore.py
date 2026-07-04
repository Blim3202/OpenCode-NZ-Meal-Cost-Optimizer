import os
import time
from playwright.sync_api import sync_playwright

# Configuration
URL = "https://www.woolworths.co.nz/"
BOOKATIMESLOT_URL = "https://www.woolworths.co.nz/bookatimeslot"
OUT_DIR = os.path.join(".", ".Temp")
os.makedirs(OUT_DIR, exist_ok=True)


def save_html(page, step_name):
    """Save rendered DOM after a major step."""
    html = page.content()
    out_path = os.path.join(OUT_DIR, f"woolworths_{step_name}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved HTML to {out_path}")
    return out_path

def main():
    print("Starting Woolworths store change investigation...")
    
    with sync_playwright() as p:
        print("Launching headed Chromium...")
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-default-browser-check",
            ],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/138.0.0.0 Safari/537.36",
            locale="en-NZ",
            timezone_id="Pacific/Auckland",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()
        
        ### Step 1: Navigate to the homepage ###
        print("\n1. Navigating to homepage...")
        page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)
        save_html(page, "homepage")


        ### Step 2: Navigate to booking a timeslot ###
        print("\n2. go to bookatimeslot page...")
        book_found = False
        try:
            loc = page.get_by_text("Change location", exact=False)
            if loc.count() > 0:
                print("Found 'Change location' on homepage")
                loc.first.click()
                book_found = True
        except Exception as e:
            print(f"Homepage 'Change location' probe error: {e}")

        if book_found:
            time.sleep(3)
            save_html(page, "bookatimeslot")
            print(f"Post-click URL: {page.url}")
        else:
            print("Could not find 'Change store' button with selector")
            browser.close()
        

        ### Step 3: Click the pickup radio button ###
        print("\nStep 3: Click the pickup radio button...")
        pickup_found = False
        pickup_radio = page.locator('input#method-pickup[type="radio"]')
        try:
            if pickup_radio.count() > 0:
                print("Found pickup radio button, clicking...")
                pickup_radio.first.click()
                pickup_found = True
        except Exception as e: 
             print(f"Pickup radio probe error: {e}")

        if book_found:
            time.sleep(3)
            save_html(page, "pickup")
            print(f"Post-click URL: {page.url}")
        else:
            print("Could not find 'Pickup' radio button with selector")
            browser.close()      

        ### Step 4: Click the change store button ###
        print("\nStep 4: Click the change store button...")
        changestore_found = False
        change_store_selector = 'button[data-cy="link"]:has-text("Change store")'
        change_store_button = page.locator(change_store_selector)
        pickup_radio = page.locator('input#method-pickup[type="radio"]')

        try:    
            if change_store_button.count() > 0:
                print("Found change store button, clicking...")
                change_store_button.first.click()
                changestore_found = True
        except Exception as e: 
             print(f"Change store button probe error: {e}")

        if changestore_found:
            time.sleep(3)
            save_html(page, "changestore")
            print(f"Post-click URL: {page.url}")
        else:
            print("Could not find 'change store' button with selector")
            browser.close()      
        


        browser.close()




if __name__ == "__main__":
    main()