import os
import sys
import pandas as pd
from datetime import datetime
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from integrations.stock_api import get_stock_price

CSV_PATH = os.path.join(PROJECT_ROOT, 'data', 'stock_data.csv')

def update_csv():
    print(f"Reading {CSV_PATH}...")
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found!")
        return

    df = pd.read_csv(CSV_PATH)
    
    updated_count = 0
    today = datetime.now().strftime("%Y-%m-%d")
    
    for index, row in df.iterrows():
        ticker = row['ticker']
        print(f"Fetching latest data for {ticker}...")
        
        # Add a delay to avoid rate limits on free APIs
        time.sleep(1)
        
        # Fetch data using the existing API cascading fallback
        data = get_stock_price(ticker)
        
        # If the API succeeds AND the source is NOT the local CSV fallback, update the row
        if data.get("success") and not data.get("source", "").startswith("Local CSV"):
            df.at[index, 'current_price'] = data['current_price']
            df.at[index, 'day_high'] = data['day_high']
            df.at[index, 'day_low'] = data['day_low']
            
            vol = data['volume']
            if isinstance(vol, str):
                vol = vol.replace('"', '')
            df.at[index, 'volume'] = vol
            df.at[index, 'last_updated'] = today
            
            print(f"  -> Updated {ticker}: ${data['current_price']} ({data['source']})")
            updated_count += 1
        else:
            print(f"  -> Failed to fetch live data for {ticker} (kept old data).")
            
    # Save back to CSV
    df.to_csv(CSV_PATH, index=False)
    print(f"\nSuccessfully updated {updated_count} out of {len(df)} tickers!")

if __name__ == "__main__":
    update_csv()
