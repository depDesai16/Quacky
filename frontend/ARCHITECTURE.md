# Frontend Architecture

## Boundary Rules
- Views render UI and emit signals only.
- Controllers handle backend calls and async work.
- Reusable widgets stay in `frontend/widgets` and never import from feature folders.

## Feature Folders
- `frontend/chat`
  - `window.py`: main chat window implementation
  - `view.py`: chat view entrypoint
  - `controller.py`: chat orchestration target
  - `model_window.py`, `glwidget.py`, `obj_loader.py`, `shortcuts_panel.py`: chat-specific UI modules
- `frontend/settings`
  - `view.py`: settings UI composition
  - `controller.py`: settings backend orchestration
  - `ui.py`: settings page UI internals and layout mixin
  - `widgets/toggle_slider.py`: settings-specific toggle widget

## Root Files
- Keep only shared/core files at `frontend/` root, such as `app.py`, `theme.py`, and `draw_icon.py`.
- Legacy root compatibility shims have been removed; imports should target `frontend/chat/*` and `frontend/settings/*` modules directly.
