# Quacky Architecture

## Overview

Quacky is a local desktop application with two primary runtime layers:

1. A PyQt frontend that owns the desktop UX.
2. A local HTTP backend that owns chat orchestration, feature execution, and persistence.

The backend uses Gemini in three distinct ways:

- main conversational chat
- intent classification
- response rewriting and confirmation phrasing

This split keeps the frontend relatively thin and keeps assistant behavior concentrated in backend modules.

## High-Level Flow

```text
User
  -> PyQt frontend
  -> backend.client.QuackyClient
  -> local HTTP server (backend.server)
  -> ChatRuntime
  -> intent classification / routing / feature execution / LLM fallback
  -> HTTP response
  -> frontend renders text, settings state, and timer/event data
```

## Main Components

### Frontend

- Starts the local backend process when launched through `frontend/app.py`
- Waits for backend health before opening the main UI
- Uses `backend/client.py` for all backend communication
- Renders chat, settings, and dashboard-like timer/event views

### Backend Server

- Exposes routes for chat, settings, health, history, and timer/event dashboard data
- Owns process-local runtime state such as active chats and confirmation toggles
- Delegates most assistant behavior to `ChatRuntime`

### Chat Runtime

- Creates and stores Gemini chat sessions
- Classifies user input before deciding whether to:
  - ask for clarification
  - require confirmation
  - dispatch directly to deterministic features
  - fall back to conversational chat
- Merges due timer/alarm alerts into outgoing responses

### Features and Tools

- `backend/features/` contains feature-specific implementations
- `backend/tools/` provides callable tool wrappers used by the runtime/router stack
- Deterministic features are preferred where possible so the LLM is not doing actual business logic

### Persistence

Quacky currently uses local file-backed persistence for selective assistant state, including:

- local settings
- remembered preferences/task notes
- activity/event logs

This keeps local setup simple but means the app currently behaves like a single-user workstation application rather than a multi-user service.

## Design Priorities

- local-first development
- fast iteration over features
- deterministic routing for high-impact actions
- explicit confirmation for risky actions
- low operational overhead

## Current Constraints

- The backend is a local process, not a deployed service platform
- Some modules still reflect earlier project layouts and need ongoing cleanup
- External integrations rely on environment configuration rather than managed secrets/infrastructure
- UI and backend process lifecycle are coupled in the desktop launch path
