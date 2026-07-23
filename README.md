# IRA - Intelligent Responsive Assistant

IRA is a personal AI desktop assistant inspired by systems like J.A.R.V.I.S, FRIDAY, and Samantha. It talks with you, understands voice commands, controls your computer, remembers context, and is being built out into a full agentic assistant — with a phone companion planned down the line.

## Status

Actively in development. Core architecture, memory, voice pipeline, and the skill framework are built and working. Currently building out agentic task planning and orchestration (Phase 8).

## What works today

- **Natural language chat**, backed by the Gemini API
- **Voice input**, powered by a locally-run Faster-Whisper model, with latency optimizations applied
- **Skill framework** — commands are routed through a `Skill` interface rather than one giant command parser:
  - `SystemSkill` — system-level commands (mute, volume, lock, etc.)
  - `AppSkill` — open applications (Chrome, VS Code, Notepad, Calculator, Spotify, etc.) and known folders (Downloads, Documents, Desktop, Pictures, Videos, Music)
  - `BrowserSkill` — website navigation and web search
  - `MediaSkill` — media/volume control
- **Memory system** — remembers context across a session (e.g. resolving "close it" / "refresh it" to the right target) and persists useful state
- **Goal/task planner** — early multi-step task planning (`ira/goals/`, `ira/planner/`) for commands that need more than one action
- **Fast local intent routing** — a lightweight router handles simple commands locally before falling back to the LLM, cutting unnecessary API calls
- **React + Electron desktop app** — Electron is kept as a thin shell (window, system tray, IPC); all logic lives in the Python backend
- **FastAPI backend server**, plus a standalone CLI for quick testing

## Run IRA

### Backend server

From the project root:

```
python -m backend.ira.server
```

The server listens on `http://127.0.0.1:8765`.

### Backend CLI (for quick testing without the frontend)

```
cd backend
python -m ira.cli
```

### Frontend desktop app

```
cd frontend
npm install
npm run desktop
```

For browser-only development: `npm run dev`, then open the local URL Vite prints. Keep the backend server running in another terminal for the frontend to execute real commands.

### Gemini API setup

Create a Gemini API key in Google AI Studio and add it to `backend/.env`:

```
GEMINI_API_KEY=your_google_ai_studio_api_key_here
GEMINI_MODEL=gemini-3.1-flash-lite
```

## Architecture

```
IRA/
├── backend/
│   └── ira/
│       ├── assistant.py       # core assistant / response handling
│       ├── actions.py         # low-level OS action layer
│       ├── server.py          # FastAPI server
│       ├── cli.py             # command-line interface
│       ├── voice.py           # voice input/output
│       ├── face.py            # local vision / face detection
│       ├── virtual_world.py
│       ├── skills/            # Skill framework (system, app, browser, media)
│       ├── goals/             # goal management
│       ├── planner/           # task planning
│       ├── memory/            # context + memory
│       └── execution/         # task execution
│
├── frontend/
│   ├── React + Vite
│   ├── Electron (thin shell only — no business logic)
│   └── src/
│
└── README.md
```

## Roadmap

**Near-term**
- Phase 8: intelligent orchestration / agentic multi-step planning across skills
- Expand skill coverage (more apps, more automation)
- Wake word ("Hey IRA") and always-listening mode

**Longer-term**
- Screen understanding (OCR, computer vision, context-aware assistance)
- Persistent long-term memory (vector search via ChromaDB)
- Mobile companion app — remote commands from phone to PC, notifications
- Broader automation (Playwright/PyAutoGUI-driven browser and desktop tasks)

Messaging integrations, payments, and full cross-device control are the eventual goal, but are treated as later-stage work once the core assistant is reliable — not part of the near-term roadmap.

## Technologies

- **Backend:** Python, FastAPI
- **Frontend:** React, Electron
- **AI:** Google AI Studio / Gemini API, local intent routing, Ollama (planned local LLM fallback)
- **Voice:** Faster-Whisper (local STT)
- **Vision:** OpenCV (local face detection), OCR (planned)
- **Automation:** Playwright, PyAutoGUI, Pynput
- **Memory/Data:** SQLite, ChromaDB (planned for long-term memory)

## Safety rules

IRA asks for confirmation before sensitive actions, including:

- Sending messages or emails
- Calling someone
- Deleting or moving files
- Accessing private accounts
- Making purchases
- Running system-level commands

## Disclaimer

IRA is intended strictly for ethical, educational, and productivity purposes. It is not designed for malicious activity, unauthorized access, surveillance, credential theft, or harmful automation.
