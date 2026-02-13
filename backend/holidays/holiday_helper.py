import json
import os
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "holidays.json")

class HolidayAssistant:
    def __init__(self, filepath=DATA_FILE):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                self.holidays = json.load(f)
            
            self.holiday_names = {h['name'].lower() for h in self.holidays if len(h['name']) > 3}
            
            print(f"✅ Holiday Assistant loaded {len(self.holidays)} events.")
        except FileNotFoundError:
            self.holidays = []
            self.holiday_names = set()

    def check_date(self, date_str=None):
        """Checks if a specific date is a holiday."""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        found = [f"{h['name']} ({h.get('primary_type', 'Holiday')})" 
                 for h in self.holidays if h['date']['iso'] == date_str]
        
        return f"On {date_str}, I found: {', '.join(found)}." if found else None

    def find_holiday(self, name):
        """Finds a holiday by partial name match."""
        results = []
        name = name.lower()
        for h in self.holidays:
            if name in h['name'].lower():
                date = h['date']['iso']
                h_type = h.get('primary_type', h.get('type', ['Unknown'])[0])
                results.append(f"📅 **{h['name']}** is on {date} ({h_type})")
        return "\n".join(results) if results else None

    def get_upcoming(self, limit=5):
        """Gets the next few holidays."""
        today = datetime.now().strftime("%Y-%m-%d")
        upcoming = []
        count = 0
        for h in self.holidays:
            if h['date']['iso'] >= today:
                h_type = h.get('primary_type', h.get('type', ['Unknown'])[0])
                upcoming.append(f"• **{h['date']['iso']}**: {h['name']} ({h_type})")
                count += 1
                if count >= limit: break
        return "Here are the next few upcoming holidays:\n" + "\n".join(upcoming) if upcoming else None

_assistant = HolidayAssistant()

def maybe_handle_holiday_action(user_message: str) -> str | None:
    """
    Intelligent router for holiday questions.
    """
    clean_msg = re.sub(r'[^\w\s]', '', user_message.lower()).strip()
    
    upcoming_triggers = ["upcoming", "coming up", "soon", "next holiday", "list holiday", "calendar"]
    if any(trigger in clean_msg for trigger in upcoming_triggers):
        return _assistant.get_upcoming()

    if "today" in clean_msg:
        return _assistant.check_date() 
    
    for h_name in _assistant.holiday_names:
        if f" {h_name} " in f" {clean_msg} ":
            return _assistant.find_holiday(h_name)

    if "when is" in clean_msg or "date of" in clean_msg:
        search_term = clean_msg.replace("when is", "").replace("date of", "").strip()
        if len(search_term) > 3: 
            return _assistant.find_holiday(search_term)

    return None

if __name__ == "__main__":
    print(maybe_handle_holiday_action("Tell me about Halloween please"))
    print(maybe_handle_holiday_action("Is Christmas coming up?")) 
    print(maybe_handle_holiday_action("Any holidays soon?"))