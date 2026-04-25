import time
import random
import subprocess
from datetime import datetime, timedelta

# SETTINGS
MIN_HOURS = 2
MAX_HOURS = 4
SCRAPER_FILE = "calendar_scraper.py"

def run_scraper():
    """Launches the scraper as a separate process."""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚀 Launching Scraper...")
    try:
        # Runs command py calendar_scraper.py like normal
        subprocess.run(["py", SCRAPER_FILE], check=True)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Scraper run finished successfully.")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error running scraper: {e}")

def main_loop():
    print("--- StreetPulse Stealth Automation Engine ---")
    print(f"Interval: Every {MIN_HOURS} to {MAX_HOURS} hours (Randomized)")
    
    # start direct
    run_scraper()

    while True:
        # le wait time
        wait_hours = random.uniform(MIN_HOURS, MAX_HOURS)
        wait_seconds = wait_hours * 3600
        
        next_run_time = datetime.now() + timedelta(seconds=wait_seconds)
        
        print(f"\n--- STANDBY ---")
        print(f"Next run scheduled for: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Waiting for {round(wait_hours, 2)} hours...")
        
        # s'assure que tout soit up avant de prendre les données
        time.sleep(wait_seconds)
        
        # do it
        run_scraper()

if __name__ == "__main__":
    main_loop()