import calendar
import json
import os
import re
from datetime import datetime


def find_backend_root(start: str) -> str:
    """
    Walk upward until we find the backend root (folder containing server.py + config.py).
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
    return os.path.join(backend_dir, "data", "holidays.json")

DATA_FILE = get_data_file_path()

class HolidayAssistant:
    def __init__(self, filepath=DATA_FILE):
        self.holidays = []
        self.holiday_names = set()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                raise ValueError("holidays.json must be a JSON array")

            current_year = str(datetime.now().year)
            years_in_data = {
                h.get("date", {}).get("iso", "")[:4]
                for h in data
                if h.get("date", {}).get("iso")
            }
            if years_in_data and current_year not in years_in_data:
                print(f"holidays.json contains data for {years_in_data} — run fetch_holidays.py to update.")

            self.holidays = data
            self.holiday_names = {h["name"].lower() for h in self.holidays if len(h.get("name", "")) > 3}

            print(f"Holiday Assistant loaded {len(self.holidays)} events.")
        except FileNotFoundError:
            print("holidays.json not found — run fetch_holidays.py to populate it.")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"holidays.json is invalid: {e}")


    def check_date(self, date_str=None):
        """Checks if a specific date is a holiday."""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        found = [
            f"{h['name']} ({h.get('primary_type', 'Holiday')})"
            for h in self.holidays
            if h.get("date", {}).get("iso") == date_str
        ]

        return f"On {date_str}, I found: {', '.join(found)}." if found else None

    def find_holiday(self, name):
        """Finds a holiday by partial name match."""
        results = []
        name = (name or "").lower().strip()
        if not name:
            return None

        for h in self.holidays:
            h_name = (h.get("name") or "")
            if name in h_name.lower():
                date = h.get("date", {}).get("iso", "Unknown date")
                h_type = h.get("primary_type", (h.get("type") or ["Unknown"])[0])
                results.append(f"**{h_name}** is on {date} ({h_type})")
        return "\n".join(results) if results else None

    def get_upcoming(self, limit=5):
        """Gets the next few holidays."""
        today = datetime.now().strftime("%Y-%m-%d")
        upcoming = []
        count = 0

        for h in self.holidays:
            iso = h.get("date", {}).get("iso")
            if not iso:
                continue

            if iso >= today:
                h_type = h.get("primary_type", (h.get("type") or ["Unknown"])[0])
                upcoming.append(f"• **{iso}**: {h.get('name','(Unnamed)')} ({h_type})")
                count += 1
                if count >= limit:
                    break

        return "Here are the next few upcoming holidays:\n" + "\n".join(upcoming) if upcoming else None


_assistant = HolidayAssistant()

_MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

_UPCOMING_TRIGGERS = [
    "upcoming", "coming up", "soon",
    "next holiday", "next holidays",
    "list holiday", "list holidays",
    "holiday list", "holidays",
]

_APP_OPEN_VERBS = re.compile(r"^\s*(open|launch|start)\s+", re.IGNORECASE)

_TODAY_TRIGGERS = ["today", "right now", "currently"]

_WHEN_PAT = re.compile(
    r"\b(when\s+is|when'?s|whens|what\s+(day|date)\s+is|date\s+of)\b",
    re.IGNORECASE
)

_NEXT_N_PAT = re.compile(r"\bnext\s+(\d{1,2})\b", re.IGNORECASE)

_MONTH_QUERY_PAT = re.compile(
    r"\b(holidays?\s+(in|during)\s+([a-z]{3,9})|holidays?\s+this\s+month)\b",
    re.IGNORECASE
)

_FEDERAL_PAT = re.compile(r"\b(federal|national)\s+holidays?\b", re.IGNORECASE)

_ON_DATE_PAT = re.compile(
    r"\bon\s+(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})\b",
    re.IGNORECASE
)


def _parse_date_token(token: str) -> str | None:
    """Return ISO YYYY-MM-DD or None."""
    token = (token or "").strip()
    if not token:
        return None

    try:
        dt = datetime.strptime(token, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            dt = datetime.strptime(token, fmt)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue

    return None


def _get_upcoming_filtered(limit: int = 5, federal_only: bool = False) -> str | None:
    """Upcoming holidays, optionally filtered to federal/national/public types (best-effort)."""
    today = datetime.now().strftime("%Y-%m-%d")
    upcoming = []

    for h in _assistant.holidays:
        iso = h.get("date", {}).get("iso")
        if not iso or iso < today:
            continue

        h_type = h.get("primary_type", (h.get("type") or ["Unknown"])[0])

        if federal_only:
            if not any(k in str(h_type).lower() for k in ("national", "federal", "public")):
                continue

        upcoming.append(f"• **{iso}**: {h.get('name','(Unnamed)')} ({h_type})")
        if len(upcoming) >= limit:
            break

    return "Here are the next few upcoming holidays:\n" + "\n".join(upcoming) if upcoming else None


def _find_holidays_in_month(month_num: int, year: int | None = None, federal_only: bool = False) -> str | None:
    """Lists holidays in a given month (current year by default)."""
    if year is None:
        year = datetime.now().year

    results = []
    for h in _assistant.holidays:
        iso = h.get("date", {}).get("iso", "")
        if not iso.startswith(f"{year}-"):
            continue

        try:
            dt = datetime.strptime(iso, "%Y-%m-%d")
        except Exception:
            continue

        if dt.month != month_num:
            continue

        h_type = h.get("primary_type", (h.get("type") or ["Unknown"])[0])

        if federal_only and not any(k in str(h_type).lower() for k in ("national", "federal", "public")):
            continue

        results.append(f"• **{iso}**: {h.get('name','(Unnamed)')} ({h_type})")

    if not results:
        return None

    month_name = calendar.month_name[month_num]
    header = f"Holidays in {month_name} {year}:"
    if federal_only:
        header = f"Federal/National holidays in {month_name} {year}:"
    return header + "\n" + "\n".join(results)


def maybe_handle_holiday_action(user_message: str) -> str | None:
    """
    Smarter router for holiday questions.
    Supports:
    - "When's Thanksgiving?"
    - "Is today a holiday?"
    - "Next 10 holidays"
    - "Holidays in July" / "Holidays this month"
    - "Federal holidays this month"
    - "On 2026-07-04 is it a holiday?"
    """
    msg = (user_message or "").strip()
    if not msg:
        return None

    if _APP_OPEN_VERBS.match(msg):
        return None

    clean = re.sub(r"[^\w\s/'-]", "", msg.lower()).strip()

    m = _ON_DATE_PAT.search(clean)
    if m:
        iso = _parse_date_token(m.group(1))
        if iso:
            out = _assistant.check_date(iso)
            return out if out else f"I don't see a holiday on {iso}."

    if ("holiday" in clean or "holidays" in clean) and any(t in clean for t in _TODAY_TRIGGERS):
        out = _assistant.check_date()
        return out if out else "I don't see a holiday today."

    nmatch = _NEXT_N_PAT.search(clean)
    if nmatch and any(k in clean for k in ("next holiday", "next holidays", "upcoming", "coming up", "soon")):
        n = int(nmatch.group(1))
        if n < 1:
            n = 1
        if n > 25:
            n = 25
        federal_only = bool(_FEDERAL_PAT.search(clean))
        out = _get_upcoming_filtered(limit=n, federal_only=federal_only)
        return out if out else None
    
    if any(trigger in clean for trigger in _UPCOMING_TRIGGERS):
        federal_only = bool(_FEDERAL_PAT.search(clean))
        out = _get_upcoming_filtered(limit=5, federal_only=federal_only)
        return out if out else None

    mm = _MONTH_QUERY_PAT.search(clean)
    if mm:
        federal_only = bool(_FEDERAL_PAT.search(clean))
        if "this month" in clean:
            month_num = datetime.now().month
        else:
            mon_token = (mm.group(3) or "").lower()
            month_num = _MONTHS.get(mon_token)
            if not month_num:
                return None
        out = _find_holidays_in_month(month_num, year=datetime.now().year, federal_only=federal_only)
        return out if out else None

    if _WHEN_PAT.search(clean):
        search_term = _WHEN_PAT.sub("", clean).strip()
        if len(search_term) >= 3:
            out = _assistant.find_holiday(search_term)
            return out if out else None

    for h_name in _assistant.holiday_names:
        if f" {h_name} " in f" {clean} ":
            out = _assistant.find_holiday(h_name)
            return out if out else None

    return None


if __name__ == "__main__":
    print(maybe_handle_holiday_action("Tell me about Halloween please"))
    print(maybe_handle_holiday_action("Is Christmas coming up?"))
    print(maybe_handle_holiday_action("Any holidays soon?"))
    print(maybe_handle_holiday_action("When's Thanksgiving?"))
    print(maybe_handle_holiday_action("Holidays in July"))
    print(maybe_handle_holiday_action("Federal holidays this month"))
    print(maybe_handle_holiday_action("On 7/4/2026 is it a holiday?"))