import requests
import json
import os
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("CALENDARIFIC_API_KEY")
COUNTRY = "US"

def find_backend_root(start: str) -> str:
    """
    Walk upward until we find the backend root (folder containing server.py + config.py).
    Works even if this script is inside backend/features/holidays/.
    """
    cur = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(cur, "server.py")) and os.path.exists(os.path.join(cur, "config.py")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            raise RuntimeError("Could not locate backend root (server.py/config.py not found).")
        cur = parent

def get_data_file_path() -> str:
    backend_dir = find_backend_root(os.path.dirname(__file__))
    data_dir = os.path.join(backend_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "holidays.json")

def fetch_and_save(year: int | None = None):
    if not API_KEY:
        print("Error: CALENDARIFIC_API_KEY not found in .env")
        return

    if year is None:
        year = datetime.now().year

    url = (
        f"https://calendarific.com/api/v2/holidays"
        f"?api_key={API_KEY}&country={COUNTRY}&year={year}"
    )

    print(f"Fetching holidays for {year} ({COUNTRY})...")

    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"HTTP {response.status_code}: {response.text}")
            return

        data = response.json()
        if "response" not in data or "holidays" not in data["response"]:
            print(f"Unexpected API response: {data}")
            return

        holidays = data["response"]["holidays"]

        file_path = get_data_file_path()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(holidays, f, indent=4, ensure_ascii=False)

        print(f"Saved {len(holidays)} holidays for {year} → {file_path}")

    except requests.Timeout:
        print("Request timed out — check your connection and try again.")
    except requests.RequestException as e:
        print(f"Connection failed: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch US holidays from Calendarific.")
    parser.add_argument("--year", type=int, default=None, help="Year to fetch (default: current year)")
    args = parser.parse_args()
    fetch_and_save(year=args.year)
