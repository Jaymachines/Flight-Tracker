import time
import random
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

ORIGIN = "YQB"

DESTINATIONS = [
    "TYO", "KIX", "OKA", "FUK", "CGK", "SIN", 
    "ICN", "TPE", "HKG", "PEK", "HAN", "BKK"
]

PAGES_TO_SCAN = 6 
TODAY_DATE = datetime.now().strftime("%Y-%m-%d")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

def parse_calendar_text(raw_text, scraped_dates, route_id):
    lines = raw_text.split('\n')
    current_month = "Unknown"
    current_day = "Unknown"
    new_entries = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        for m in MONTHS:
            if m in line and len(line) < 20: 
                current_month = line
                break
                
        if line.isdigit() and 1 <= int(line) <= 31:
            current_day = line
            continue
            
        if "$" in line:
            parts = line.split()
            if len(parts) >= 2 and parts[0].isdigit():
                current_day = parts[0]
                price_string = " ".join(parts[1:])
            else:
                price_string = line
                
            clean_price = "".join(c for c in price_string if c.isdigit())
            
            if clean_price and current_month != "Unknown" and current_day != "Unknown":
                full_date = f"{current_month} {current_day}"
                
                if full_date not in scraped_dates:
                    print(f"  [{full_date}] | Price: ${clean_price}")
                    scraped_dates.add(full_date)
                    new_entries += 1
                    
                    try:
                        parsed_date = datetime.strptime(full_date, "%B %d")
                        current_month_num = datetime.now().month
                        target_year = 2026 if parsed_date.month >= current_month_num else 2027 
                        db_date = parsed_date.replace(year=target_year).strftime("%Y-%m-%d")
                    except ValueError:
                        db_date = full_date 
                    
                    payload = {
                        "route_id": route_id, 
                        "airline": "Aggregated", 
                        "price": float(clean_price),
                        "departure_date": db_date,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "source": "calendar_vacuum_oneway"
                    }
                    
                    try:
                        requests.post("http://127.0.0.1:8000/ingest_price", json=payload)
                    except Exception:
                        pass 
                    
                current_day = "Unknown"
                
    return new_entries

def scrape_calendar_grid():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 900} 
        )
        page = context.new_page()
        
        stealth = Stealth()
        stealth.apply_stealth_sync(page)

        for dest in DESTINATIONS:
            legs = [
                {"from": ORIGIN, "to": dest, "id": f"{ORIGIN}-{dest}"},
                {"from": dest, "to": ORIGIN, "id": f"{dest}-{ORIGIN}"}
            ]

            for leg in legs:
                print(f"\n=======================================================")
                print(f"TARGETING: {leg['id']} | {leg['from']} -> {leg['to']} (One Way)")
                print(f"=======================================================\n")
                
                # le url direct si il marche (ca marche plus burner par Google)
                url = "https://www.google.com/travel/flights?hl=en&curr=CAD"
                
                try:
                    page.goto(url)
                    time.sleep(random.uniform(4, 6))

                    # 1. Force One-way en 1er pour clean up the UI
                    round_trip_dropdown = page.locator('div[role="combobox"]:has-text("Round trip")')
                    if round_trip_dropdown.count() > 0:
                        round_trip_dropdown.first.click()
                        time.sleep(1)
                        page.locator('li[role="option"]:has-text("One way")').first.click()
                        time.sleep(1.5) 

                    # 2. Type Origin manuel
                    print(f"Setting Origin: {leg['from']}")
                    where_from = page.locator('input[aria-label="Where from?"], input[placeholder="Where from?"]').first
                    where_from.click()
                    time.sleep(0.5)
                    page.keyboard.press("Backspace") # Clears any default IP-based city
                    time.sleep(0.5)
                    page.keyboard.type(leg['from'])
                    time.sleep(1.5)
                    page.keyboard.press("Enter")
                    time.sleep(1)

                    # 3. Type Destination manuel
                    print(f"Setting Destination: {leg['to']}")
                    where_to = page.locator('input[aria-label="Where to?"], input[placeholder="Where to?"]').first
                    where_to.click()
                    time.sleep(0.5)
                    page.keyboard.press("Backspace")
                    time.sleep(0.5)
                    page.keyboard.type(leg['to'])
                    time.sleep(1.5)
                    page.keyboard.press("Enter")
                    time.sleep(1.5)

                    # 4. Open the calendar
                    print("Opening the calendar...")
                    try:
                        page.locator('div[aria-label*="Departure"], input[placeholder*="Depart"]').first.click(timeout=4000)
                    except:
                        try:
                            page.get_by_text("Departure").first.click(timeout=4000)
                        except:
                            print("Error: Could not click the calendar box.")
                    
                    scraped_dates = set() 

                    for page_num in range(PAGES_TO_SCAN):
                        print(f"\n--- Scanning Page {page_num + 1} of {PAGES_TO_SCAN} for {leg['id']} ---")
                        time.sleep(4) 
                        
                        raw_screen_text = page.locator('body').inner_text()
                            
                        new_entries = parse_calendar_text(raw_screen_text, scraped_dates, leg['id'])
                        print(f"-> Sent {new_entries} new days to SQL.")

                        if page_num < PAGES_TO_SCAN - 1:
                            next_button = page.locator('button[aria-label*="Next"], div[aria-label*="Next"]').first
                            if next_button.is_visible():
                                next_button.click()
                            else:
                                print("End of calendar reached.")
                                break
                                
                except Exception as e:
                    print(f"Error extracting {leg['id']}: {e}")

                cooldown = random.uniform(8, 12)
                print(f"Cooling down for {int(cooldown)} seconds...")
                time.sleep(cooldown)

        print("-" * 60)
        print("BATCH SCRAPE COMPLETE.")
        time.sleep(2)
        browser.close()

if __name__ == "__main__":
    scrape_calendar_grid()