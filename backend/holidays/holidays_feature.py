import json
import urllib.request
import urllib.error
from datetime import date

BASE_URL = "https://date.nager.at/api/v3"

def _http_get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Quacky/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_upcoming_us_holidays(limit: int = 10) -> str:
    """
    Returns upcoming US public holidays using Nager API.
    """
    url = f"{BASE_URL}/NextPublicHolidays/US"

    try:
        data = _http_get_json(url)
    except urllib.error.HTTPError as e:
        return f"Could not fetch US holidays (HTTP {e.code})."
    except Exception:
        return "Could not fetch US holidays right now."

    if not data:
        return "No upcoming US holidays found."

    lines = []
    for item in data[:limit]:
        holiday_date = item.get("date", "")
        name = item.get("name", "")
        lines.append(f"- {holiday_date}: {name}")

    return f"Upcoming US holidays (starting {date.today().isoformat()}):\n" + "\n".join(lines)
