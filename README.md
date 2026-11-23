# Boot-to-Browser Autonomous Voice Co-Pilot

## What it does

Boot-to-Browser is a voice-controlled agent that helps visually impaired users operate a computer. It follows a listen, observe, plan, safety gate, act, and verify loop until the goal is complete.

## Setup

Requires Python 3.11 on Windows.

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `GEMINI_API_KEY` and `GEMINI_MODEL` in `.env`.

## Run

No application entry point is implemented yet.

## Architecture

The project is organized into packages for voice, vision, planning, actions, safety, startup, evaluation, and shared utilities. The agent uses raw screen pixels with numbered Set-of-Mark boxes as grounding.

## Limitations

This is an initial Python skeleton. Application logic, hardware integration, model integration, and evaluation scenarios have not been implemented yet.
