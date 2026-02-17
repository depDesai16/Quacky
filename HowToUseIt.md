# Get your API Key
go to aistudio.google.com  
sign in, and at the bottom left of the screen, click get API key. Follow the prompts.  
copy the key, and paste it in .env.example. Then, rename to .env

# Get your Weather API Key
go to https://www.weatherapi.com/
create an account and verify, then it will give you an api key
after you get the key go to .env and make WEATHERAPI_KEY=, then place your key there

## Calendar Feature
Control your Outlook calendar using natural, conversational language.

### Open Calendar
- "Open my calendar"
- "Open Outlook"
- "Launch Outlook calendar"

### Add an Event
Just tell Quacky what you want to schedule:

**Examples:**
- "Schedule dentist appointment Friday at 2pm for 45 minutes"
- "I need to meet with Sarah next Tuesday at 3"
- "Put team standup on my calendar Monday at 9am"
- "Add project review tomorrow at 3pm"

**What Quacky understands:**
- Natural dates: "tomorrow", "next Friday", "March 10"
- Casual times: "at 3" (assumes 3pm during business hours), "2pm", "noon"
- Duration: "for 30 minutes", "for 1 hour" (defaults to 60 minutes if not specified)

### Update an Event
Change the time or duration of existing events:

**Examples:**
- "Move dentist to next Wednesday at 10am"
- "Reschedule my meeting with Sarah to Thursday at 4pm for 1 hour"
- "Change team standup to Tuesday 9am"

**Smart features:**
- Case-insensitive matching: "dentist", "Dentist", or "DENTIST" all work
- Recognizes event titles even without exact wording

### Delete an Event
Remove events from your calendar:

**Examples:**
- "Cancel dentist"
- "Remove meeting with Sarah"
- "Delete team standup"

**Note:** Quacky will ask for confirmation before deleting any event.

### Smart Validations
Quacky catches common mistakes:
- "Add meeting yesterday" → Warns you can't schedule past events
- "Schedule call for 600 minutes" → Asks if you meant hours instead
- "Create event called meeting on Friday" → Asks for a more specific title

### Clarifying Questions
If your request is ambiguous, Quacky will ask for clarification:
- "Move my meeting to 3pm" → "Which meeting would you like to reschedule?"
- "Cancel my appointment" → "Which appointment should I cancel?"

---

## Weather Feature
Get weather information using natural, conversational questions.

### What You Can Ask

**Current conditions:**
- "What's the weather?"
- "How hot is it right now?"
- "Is it windy outside?"

**Today's forecast:**
- "Weather today"
- "Do I need an umbrella?"
- "Should I bring a jacket?"

**Future forecasts:**
- "Will it rain tomorrow?"
- "What's the weather this weekend?"
- "Give me a 5 day forecast"
- "Weather for the next 3 days"
- "What's it like next week?"

**Combined questions:**
- "What's the weather Friday and is that a holiday?"
- "Is it going to be nice enough to go hiking Saturday?"

### How It Works
- Weather is automatically detected from your IP address
- Forecasts support up to 10 days ahead
- Quacky phrases responses naturally based on your question

---

## Holiday Feature
Ask about US federal and national holidays using natural language.

### What You Can Ask

**Upcoming holidays:**
- "Any holidays coming up?"
- "Next 10 holidays"
- "Federal holidays this month"

**Specific holidays:**
- "When is Thanksgiving?"
- "Date of Memorial Day"
- "When's the Fourth of July?"

**Check a date:**
- "Is today a holiday?"
- "Is July 4th a holiday?"
- "On 2/17/2026 is it a holiday?"

**Holidays in a month:**
- "Holidays in July"
- "What holidays are in December?"
- "Any days off next month?"