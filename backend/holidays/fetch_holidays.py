import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("CALENDARIFIC_API_KEY")
COUNTRY = "US"

CURRENT_YEAR = datetime.now().year

def fetch_and_save():
    if not API_KEY:
        print("❌ Error: API Key not found.")
        return

    url = f"https://calendarific.com/api/v2/holidays?api_key={API_KEY}&country={COUNTRY}&year={CURRENT_YEAR}"
    
    print(f"⏳ Connecting to Calendarific for {CURRENT_YEAR} data...")
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if 'response' in data and 'holidays' in data['response']:
                holidays = data['response']['holidays']
                
                script_dir = os.path.dirname(os.path.abspath(__file__))
                file_path = os.path.join(script_dir, "holidays.json")
                
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(holidays, f, indent=4)
                    
                print(f"✅ Success! Saved {len(holidays)} holidays for {CURRENT_YEAR}.")
            else:
                print(f"❌ API Error: {data}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    fetch_and_save()