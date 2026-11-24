"""Microphone speech-to-text using a cached Faster-Whisper model."""

import logging
import time
from typing import Any

from voice.vad import record

logger = logging.getLogger("boot_to_browser")
_model: Any | None = None


def _get_model() -> Any:
    """Load the CPU Faster-Whisper base model once and cache it."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


def listen() -> str:
    """Record audio, transcribe it, and return stripped text or an empty string."""
    recording_started = time.perf_counter()
    audio = record()
    logger.info(
        "voice.recording_ms=%d",
        round((time.perf_counter() - recording_started) * 1000),
    )

    if getattr(audio, "size", 0) == 0:
        return ""

    transcription_started = time.perf_counter()
    segments, _ = _get_model().transcribe(audio, vad_filter=True)
    text = " ".join(segment.text for segment in segments).strip()
    logger.info(
        "voice.transcription_ms=%d",
        round((time.perf_counter() - transcription_started) * 1000),
    )
    return text


def listen_push_to_talk(key: str = "f9") -> str:
    """Wait for a key press, then listen through the microphone."""
    import keyboard

    keyboard.wait(key)
    return listen()
