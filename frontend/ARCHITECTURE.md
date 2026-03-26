# Frontend Architecture

This file is the implementation-oriented frontend note. For the higher-level project view, start with [`docs/FRONTEND_ARCHITECTURE.md`](/home/jake/code/Quacky/docs/FRONTEND_ARCHITECTURE.md).

## Boundary Rules

- Views render UI and emit signals only.
- Controllers handle backend calls and async work.
- Reusable widgets stay in `frontend/widgets` and never import from feature folders.

## Feature Folders

### `frontend/chat`

- `window.py`: main chat window implementation
- `model_window.py`, `glwidget.py`, `obj_loader.py`: model and 3D presentation support
- `shortcuts_panel.py`, `timers_events_panel.py`: chat-adjacent utility panels
- `speech_to_speech/`: speech-oriented chat UI pieces

### `frontend/settings`

- `view.py`: settings UI composition
- `controller.py`: settings backend orchestration
- `ui.py`: settings layout internals and mixins
- `widgets/toggle_slider.py`: settings-specific reusable control

### `frontend/widgets`

- shared UI primitives used across the app

## Root Files

- `app.py`: desktop bootstrap and backend subprocess lifecycle
- `theme.py`: shared theme constants
- `draw_icon.py`: tray/app icon generation

## Guidance

- Keep backend communication centralized through `backend.client.QuackyClient`.
- Avoid embedding assistant behavior in the frontend.
- Prefer adding new backend endpoints over duplicating business rules in the UI.
