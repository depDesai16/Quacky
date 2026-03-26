# Frontend Architecture

## Purpose

The frontend is a PyQt desktop shell around the local backend. It is responsible for:

- bootstrapping the application
- managing the backend process lifecycle in desktop mode
- rendering chat and settings UI
- presenting timer/event status data

The frontend should not own assistant logic. That belongs in the backend.

## Entry Point

### `frontend/app.py`

- configures platform-specific Qt/OpenGL behavior
- starts the backend server subprocess
- waits on `/health`
- creates the initial chat session
- instantiates the main window
- manages tray behavior and shutdown

This file is effectively the desktop runtime bootstrapper.

## UI Areas

### `frontend/chat/`

- main chat window
- chat timeline and composer integration
- shortcut/timer/event panels
- speech-to-speech UI
- 3D/model-related chat presentation pieces

### `frontend/settings/`

- settings view composition
- settings controller/backend interactions
- settings-specific UI widgets

### `frontend/widgets/`

- reusable shared UI building blocks
- should stay generic and not import feature-specific logic

## Communication Pattern

The frontend talks to the backend only through `backend/client.py`.

That gives the project one transport boundary for:

- chat requests
- settings reads/writes
- dashboard fetches
- health checks

## Frontend Boundary Rules

- Views render and emit user intent.
- Controllers or top-level windows perform backend calls.
- Reusable widgets remain feature-agnostic.
- Business logic should move to the backend rather than accumulate in PyQt event handlers.

## Runtime Model

Desktop mode currently runs as a parent/child pair:

1. frontend process
2. backend subprocess

That keeps local setup simple, but it also means:

- frontend startup depends on backend health
- desktop shutdown should terminate the backend cleanly
- backend process management is part of the frontend bootstrap path

## Documentation Relationship

This file is the high-level frontend architecture summary.

More implementation-specific folder notes remain in [`frontend/ARCHITECTURE.md`](/home/jake/code/Quacky/frontend/ARCHITECTURE.md).
