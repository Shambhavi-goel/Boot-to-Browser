"""Startup sequence for the voice co-pilot and browser."""

from actions.browser import BrowserSession
from voice.tts import play_chime, speak


def run_boot_sequence(start_page: str = "https://www.google.com") -> BrowserSession:
    """Play readiness feedback, open the browser, and keep it running."""
    play_chime()
    speak("Co-pilot ready")

    browser = BrowserSession()
    browser.start()
    browser.open(start_page)
    return browser
