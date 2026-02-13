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