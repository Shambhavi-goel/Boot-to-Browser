"""Temporary text-to-speech output stub."""

import logging

logger = logging.getLogger("boot_to_browser")


def speak(text: str) -> None:
    """Log and print progress text for the command-line prototype."""
    logger.info("tts: %s", text)
    print(text)
