# Tools Overview

This folder contains tool wrappers that expose app features to the assistant.
Each tool function returns a user-facing status string.

## `weather_tool.py`
- `get_weather(timeframe, location)`: Gets current or forecast weather for a location or auto-detected IP location.

## `holiday_tool.py`
- `get_holidays(query_type, date, name, month, n)`: Looks up holidays (upcoming, federal, date check, name search, month list, or today).

## `calendar_tool.py`
- `add_outlook_event(...)`: Creates an Outlook calendar event.
- `update_outlook_event_time(...)`: Updates event timing by title.
- `delete_outlook_event_by_title(title)`: Deletes an event by title.

## `app_tool.py`
- `open_app(app_name)`: Opens a local application by name.

## `email_tool.py`
- `send_email(email_address, subject, body)`: Validates required fields, then sends an email through the feature layer.

## `memory_tool.py`
- `remember_memory(key, value, chat_id)`: Saves a key/value memory fact.
- `recall_memory(key, chat_id)`: Returns one memory fact or all saved facts.
- `forget_memory(key, chat_id)`: Deletes one memory fact by key.
- `add_task_memory(task, chat_id)`: Adds a task to active memory.
- `list_task_memory(chat_id)`: Lists active tasks.
- `complete_task_memory(task, chat_id)`: Marks a task complete and removes it.

## `__init__.py`
- Exports all tool functions.
- Defines `ALL_TOOLS`, the registry list used when wiring tools into the assistant runtime.
