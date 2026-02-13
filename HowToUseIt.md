# Get your API Key
go to aistudio.google.com  
sign in, and at the bottom left of the screen, click get API key. Follow the prompts.  
copy the key, and paste it in .env.example. Then, rename to .env

# Get your Weather API Key
go to https://www.weatherapi.com/
create an account and verify, then it will give you an api key
after you get the key go to .env and make WEATHERAPI_KEY=, then place your key there

# Using the Calendar Feature
You can control your local Outlook calendar using natural language commands.

### Open Calendar
- Open my calendar  
- Open Outlook  
- Launch Outlook calendar  

### Add an Event
Use this format:
> Add [event name] on [date] at [time] for [duration]

Examples:
- Add a meeting tomorrow at 2 PM for 30 minutes  
- Schedule Project Sync on March 10 at 4 PM for 1 hour  
- Create dentist appointment on April 5 at 9 AM  

You can also specify a timezone:
- Add a call tomorrow at 3 PM Pacific time  

### Update an Event (By Name)
Use this format:
> Move / Change / Update [event name] to [new time or date]

Examples:
- Move Project Sync to 5 PM tomorrow  
- Change dentist appointment to next Monday at 10 AM  
- Update Interview Prep to last 2 hours  

If multiple events share the same name, the next upcoming event is updated.

### Delete an Event
Use this format:
> Delete / Remove / Cancel [event name]

Examples:
- Delete Project Sync  
- Cancel dentist appointment  

### Notes
- If no timezone is specified, your default timezone is used.
- Calendar changes sync automatically if Outlook is connected to a Microsoft account.

## Using the Weather Feature

You can ask about the weather using natural language commands.

The assistant understands current conditions, today, tomorrow, weekends, weekly forecasts, and custom multi-day forecasts.

### Examples

- "What’s the weather?"
- "How hot is it right now?"
- "Will it rain tomorrow?"
- "Weather this weekend"
- "Next 3 days forecast"
- "7 day weather outlook"
- "Is it windy outside?"
- "Do I need an umbrella today?"

By default, weather is fetched using your current location (auto IP detection).


## Holiday Feature

The Holiday feature lets you ask natural-language questions about holidays.

Holiday data is fetched from Calendarific and stored locally in `holidays.json`.  
All responses are generated from this local file for fast performance.

### Example Prompts

- "Any holidays coming up?"
- "Next 10 holidays"
- "When’s Thanksgiving?"
- "Date of Memorial Day"
- "Is today a holiday?"
- "Holidays in July"
- "Federal holidays this month"
- "On 7/4/2026 is it a holiday?"

The assistant detects the intent (upcoming, specific holiday, month query, or date check) and searches the local dataset to return the correct information.
