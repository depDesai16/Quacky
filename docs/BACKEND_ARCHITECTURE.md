# Backend Architecture

## Purpose

The backend is Quacky’s orchestration layer. It turns user messages into one of four outcomes:

- a clarifying question
- a confirmation request
- a deterministic feature/tool result
- a normal conversational LLM response

## Module Responsibilities

### `backend/server.py`

- Starts the local HTTP server
- Initializes `ChatRuntime`
- Exposes routes for:
  - health
  - chat session start/message/history/reset
  - settings toggles
  - timers/events dashboard data
- Optionally attaches TTS output to responses

### `backend/client.py`

- Thin HTTP client for frontend and local tools
- Normalizes backend requests and responses
- Handles timeout and connection error shaping

### `backend/core/chat_runtime.py`

- Owns active chat sessions and in-memory per-chat memory context
- Coordinates:
  - intent classification
  - confirmation handling
  - deterministic dispatch
  - conversational fallback
- Applies preference-memory handling and due-alert merging

### `backend/core/intent_classifier.py`

- Uses Gemini to return structured intent JSON
- Converts natural-language requests into router-friendly payloads
- Supports combined intents, clarification intents, timer intents, memory intents, and calendar intents

### `backend/core/action_router.py`

- Dispatches deterministic, non-calendar intents directly to feature/tool handlers
- Extracts clarification, calendar, and confirmable intents
- Validates high-impact actions before execution
- Builds normalized pending-action payloads for confirmation flows

### `backend/core/confirmation.py`

- Handles replies when a pending action exists
- Executes the stored action on positive confirmation
- Cancels the action on negative confirmation
- Defers voice/personality phrasing to the response-style layer

### `backend/core/settings_service.py`

- Stores and retrieves local backend settings
- Supports persisted feature toggles such as confirmation settings

### `backend/core/memory_store.py`

- Persists remembered preferences and task notes
- Supports listing and clearing assistant memory

### `backend/core/activity_store.py`

- Persists recent assistant-created calendar event activity
- Feeds the frontend timer/events dashboard

## Request Lifecycle

For a normal `/chat/message` request:

1. `server.py` reads the request and identifies the chat session.
2. `ChatRuntime.handle_message()` loads in-memory context.
3. Due timer/alarm alerts are collected.
4. If a pending action exists, `confirmation.py` handles the reply.
5. Otherwise `intent_classifier.py` classifies the message.
6. `action_router.py` determines whether the message becomes:
   - clarify
   - calendar confirmation
   - non-calendar confirmation
   - direct deterministic dispatch
   - LLM fallback
7. The final text is optionally rewritten in Quacky’s voice.
8. `server.py` returns JSON, optionally with synthesized audio.

## State Model

### In-memory state

- active Gemini chat handles
- per-chat pending confirmation actions
- per-chat recent context
- runtime confirmation toggle state

### File-backed state

- API/settings values
- memory/preferences/tasks
- recent calendar activity

## Why Confirmation Exists

Some actions are cheap and reversible; some are not. Quacky uses confirmation for higher-risk operations such as:

- calendar mutations
- app launching
- sending email
- timer/alarm changes when that toggle is enabled
- clearing all memory

This avoids giving the LLM direct unchecked control over side effects.

## Known Architectural Tradeoffs

- `backend.tools` imports are broad and can pull in optional dependencies earlier than ideal.
- `ChatRuntime` currently handles several policy concerns and could eventually be decomposed.
- Server state is process-local, so restarting the backend resets active chat sessions.
- Some feature boundaries are clear conceptually but still a bit mixed in module dependency shape.
