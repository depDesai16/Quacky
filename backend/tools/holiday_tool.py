"""
Holiday tool wrapper for Quacky.
"""

from datetime import datetime

from backend.features.holidays.holiday_helper import (
    _MONTHS,
    _find_holidays_in_month,
    _get_upcoming_filtered,
)
from backend.features.holidays.holiday_helper import (
    _assistant as _holiday,
)


def get_holidays(
    query_type: str = "upcoming",
    date: str = "",
    name: str = "",
    month: str = "",
    n: int = 5,
) -> str:
    """
    Look up holiday information.

    query_type options:
        "upcoming"   - next N upcoming holidays (use n for count, default 5)
        "federal"    - next N federal/national holidays only
        "check_date" - is a specific date a holiday? (requires date as YYYY-MM-DD)
        "find"       - find a holiday by name (requires name, e.g. "Thanksgiving")
        "month"      - all holidays in a given month (requires month, e.g. "July")
        "today"      - is today a holiday?
    """
    qt = (query_type or "upcoming").strip().lower()
    year = datetime.now().year

    if qt == "today":
        today = datetime.now().strftime("%Y-%m-%d")
        result = _holiday.check_date(today)
        return result if result else "No holidays today."

    if qt == "check_date":
        d = (date or "").strip()
        if not d:
            today = datetime.now().strftime("%Y-%m-%d")
            result = _holiday.check_date(today)
            return result if result else "No holidays today."
        result = _holiday.check_date(d)
        return result if result else f"No holiday found on {d}."

    if qt == "find":
        h_name = (name or "").strip()
        if not h_name:
            return "Please provide a holiday name to search for."
        result = _holiday.find_holiday(h_name)
        return result if result else f"No holiday found matching '{h_name}'."

    if qt == "month":
        m_name = (month or "").strip().lower()
        month_num = _MONTHS.get(m_name)
        if not month_num:
            return f"Could not recognise month '{month}'. Use a full or abbreviated month name."
        result = _find_holidays_in_month(month_num, year=year)
        return result if result else f"No holidays found in {month.title()}."

    if qt == "federal":
        limit = max(1, min(int(n or 5), 25))
        result = _get_upcoming_filtered(limit=limit, federal_only=True)
        return result if result else "No upcoming federal holidays found."

    limit = max(1, min(int(n or 5), 25))
    result = _get_upcoming_filtered(limit=limit)
    return result if result else "No upcoming holidays found."