PROJECT: Boot-to-Browser Autonomous Voice Co-Pilot. A voice-controlled agent that lets visually impaired users operate a computer. Loop: listen -> observe -> plan -> safety_gate -> act -> verify, repeated until the goal is done.

CONSTRAINTS:
- Python 3.11, Windows primary, CPU only (no GPU). Heavy reasoning uses a cloud vision-language model (Gemini API); everything else runs locally.
- Grounding uses raw screen pixels with numbered Set-of-Mark boxes, NOT the DOM or accessibility tree.
- Shared data types live in schema.py (Pydantic v2). Do not change them without telling me first.
- API keys come from .env via python-dotenv. Never hardcode or log them.
- Never send passwords or OTPs to the cloud model.
- Import hardware libraries (sounddevice, pyautogui, mss, keyboard) inside functions so tests run without hardware.
- Every module needs type hints, docstrings, logging (no bare print) and a pytest test using mocks.
- Make small changes. Only touch the files I name. Keep ruff clean, line length 100.
- After each task, tell me exactly how to test it.
