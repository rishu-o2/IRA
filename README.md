# IRA - Intelligent Responsive Assistant

IRA is a personal AI assistant inspired by futuristic systems like J.A.R.V.I.S, FRIDAY, and Samantha. The goal is to build an intelligent desktop companion that can talk with the user, control computer actions, automate workflows, understand screen context, remember preferences, and eventually connect with mobile devices.

This project is starting with a small working foundation: a Python backend that can receive natural language commands and safely perform basic computer actions.

## Current Prototype

The first version of IRA can:

* Respond to simple chat commands
* Open apps like Notepad, Calculator, Chrome, Edge, and Spotify
* Open files and folders by path
* Open websites
* Search YouTube for music or videos
* Run from a command-line interface

## Run IRA

### Backend CLI

From the project root:

```powershell
cd backend
python -m ira.cli
```

Try commands like:

```text
hello
help
open notepad
open calculator
open website youtube.com
open folder C:\Users\hp\Downloads
play relaxing music
exit
```

### Backend Server

Run this when you want the frontend to execute real IRA commands:

```powershell
cd backend
python -m ira.server
```

The server listens on:

```text
http://127.0.0.1:8765
```

### Frontend Desktop App

From the project root:

```powershell
cd frontend
npm install
npm run desktop
```

For browser-only development:

```powershell
cd frontend
npm run dev
```

Then open the local URL Vite prints in the terminal.

For the frontend command box and quick action buttons to control the computer, keep the backend server running in another terminal.

## Planned Features

### Desktop Control

* Open apps, files, folders, and websites
* Control keyboard and mouse with permission
* Automate browser tasks
* Play music through Spotify or YouTube
* Manage local workflows and productivity tasks

### Voice Interaction

* Speech-to-text
* Text-to-speech
* Wake/listen mode
* Real-time voice conversation

### Memory

* Store user preferences
* Remember common folders, apps, and routines
* Keep useful conversation and task history
* Use SQLite and vector search for long-term memory

### Screen Understanding

* Screenshot analysis
* OCR
* Computer vision for UI awareness
* Context-aware assistance

### Mobile Companion

* Android app or mobile companion service
* Remote commands from phone to PC
* Notifications
* Calling and messaging integrations with explicit permission

## Technologies

### Backend

* Python

### Frontend

* React
* Electron

### AI & Language Models

* Google AI Studio / Gemini API
* Ollama
* Local LLM integration

### Google AI Studio Setup

Create a Gemini API key in Google AI Studio, then add it to `backend/.env`:

```text
GEMINI_API_KEY=your_google_ai_studio_api_key_here
GEMINI_MODEL=gemini-3.1-flash-lite
```

### Automation

* Playwright
* PyAutoGUI
* Pynput

### Vision System

* Local OpenCV face detection
* OCR
* Screen analysis

### Memory & Data

* SQLite
* ChromaDB

## Safety Rules

IRA should ask for confirmation before sensitive actions, including:

* Sending messages or emails
* Calling someone
* Deleting or moving files
* Accessing private accounts
* Making purchases
* Running system-level commands

## Status

Currently under active development. The project has begun with a backend command prototype.

## Disclaimer

IRA is intended strictly for ethical, educational, and productivity purposes. The project is not designed for malicious activity, unauthorized access, surveillance, credential theft, or harmful automation.
