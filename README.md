# Quacky

Quacky is a local-first desktop assistant built in Python. It combines a PyQt desktop UI, a lightweight local HTTP backend, Gemini-based chat/tool orchestration, and a growing set of assistant features such as calendar actions, timers, memory, weather, and app launching.

## Run Model

Quacky is not deployed through GitHub Actions.

Current behavior:

- GitHub Actions runs CI only
- the app itself runs locally on your machine
- you need local setup plus a valid `.env` to launch it

GitHub Actions currently handles:

- dependency installation in CI
- Ruff lint checks
- automated test execution
- Python dependency auditing with `pip-audit`

It does not:

- deploy Quacky to a server
- host the backend anywhere remote
- provide a hosted desktop or web instance

Current local security posture:

- the backend is intended to be reachable only from the local machine
- saved API keys are stored locally and are no longer returned by the settings API after save
- face-recognition data is treated as local-only developer data and should not be committed

## What It Does

- Chat with a local desktop assistant UI
- Route user requests through a local backend server
- Use Gemini for conversation, intent classification, and response styling
- Execute assistant features such as timers, alarms, calendar actions, memory, app launching, weather, and holidays
- Optionally generate speech output through ElevenLabs

## Repo Layout

```text
Quacky/
├── app.py                   # Root desktop launcher
├── backend/                 # Local HTTP backend and assistant logic
├── frontend/                # PyQt desktop UI
├── scripts/                 # Setup and local developer entrypoints
├── tests/                   # Unit tests and smoke tests
├── .github/workflows/       # CI
├── README.md
└── requirements.txt
```

Key areas:

- `app.py`: root-level desktop launcher for `python app.py`
- `backend/server.py`: HTTP server and route handlers
- `backend/core/`: chat runtime, routing, confirmation, persistence helpers
- `backend/features/`: feature implementations such as timers and calendar helpers
- `backend/tools/`: tool-facing wrappers used by runtime and router layers
- `frontend/app.py`: desktop app bootstrap
- `frontend/chat/`: main chat window and chat-specific UI
- `frontend/settings/`: settings UI and controller logic
- `scripts/dev.py`: unified local setup and run entrypoint

## Quick Start

### 1. Set up the project

macOS/Linux:

```bash
./scripts/setup.sh
```

Windows PowerShell:

```powershell
.\scripts\setup.ps1
```

This will:

- create `.venv`
- install dependencies from `requirements.txt`
- copy `.env.example` to `.env` if needed

### 2. Add API keys

At minimum, set one of these in `.env`:

```env
GEMINI_API_KEY=your_key_here
```

or

```env
GOOGLE_API_KEY=your_key_here
```

Optional keys:

- `ELEVENLABS_API_KEY`
- `WEATHERAPI_KEY`
- `CALENDARIFIC_API_KEY`

### 3. Validate local setup

```bash
python scripts/dev.py doctor
```

### 4. Run the full test suite

```bash
python scripts/dev.py test
```

### 5. Run lint checks

```bash
python scripts/dev.py lint
```

### 6. Audit dependencies

```bash
python -m pip_audit -r requirements.txt
```

### 7. Run Quacky

Desktop app:

```bash
python app.py
```

Developer entrypoint with preflight checks:

```bash
python scripts/dev.py ui
```

Backend only:

```bash
python scripts/dev.py server
```

Text client against a running backend:

```bash
python scripts/dev.py cli
```

By default, `ui`, `server`, and `cli` run Ruff and the full test suite before launching. During active debugging you can bypass that with `--skip-tests`.

## Developer Commands

Unified entrypoint:

```bash
python scripts/dev.py setup
python scripts/dev.py doctor
python scripts/dev.py lint
python scripts/dev.py test
python scripts/dev.py server
python scripts/dev.py ui
python scripts/dev.py cli
```

Wrapper scripts still exist for convenience:

- `./scripts/setup.sh`
- `./scripts/run-server.sh`
- `./scripts/run-ui.sh`
- `.\scripts\setup.ps1`
- `.\scripts\run-server.ps1`
- `.\scripts\run-ui.ps1`

## Platform Notes

Linux:

```bash
sudo apt-get install python3-pyaudio portaudio19-dev
```

macOS:

```bash
brew install portaudio
```

Windows:

- If PyAudio fails to install, install the Visual C++ Build Tools first.

## Testing

Run the test suite:

```bash
python scripts/dev.py test
```

Run lint checks:

```bash
python scripts/dev.py lint
```

Run a dependency audit:

```bash
python -m pip_audit -r requirements.txt
```

The current Ruff rollout is enforced on the actively maintained developer, test, and backend runtime paths rather than the entire repository.

Useful smoke check:

```bash
python -m compileall backend frontend tests scripts
```

CI lives in [`.github/workflows/ci.yml`](/home/jake/code/Quacky/.github/workflows/ci.yml).

## Architecture Docs

For current architecture and design notes, start with:

- [`docs/ARCHITECTURE.md`](/home/jake/code/Quacky/docs/ARCHITECTURE.md)
- [`docs/BACKEND_ARCHITECTURE.md`](/home/jake/code/Quacky/docs/BACKEND_ARCHITECTURE.md)
- [`docs/FRONTEND_ARCHITECTURE.md`](/home/jake/code/Quacky/docs/FRONTEND_ARCHITECTURE.md)

The existing frontend-specific notes also remain in [`frontend/ARCHITECTURE.md`](/home/jake/code/Quacky/frontend/ARCHITECTURE.md).

## Current State

This project is optimized for local development and feature iteration. The most important operational concerns right now are:

- consistent local setup
- reliable branch integration
- test coverage around runtime routing and feature logic
- keeping docs aligned with the actual repo structure
- protecting local secrets and biometric data from accidental exposure
