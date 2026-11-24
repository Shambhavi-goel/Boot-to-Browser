"""Queued text-to-speech playback with network and local fallbacks."""

import asyncio
import logging
import os
import queue
import tempfile
import threading
from pathlib import Path

import numpy as np

logger = logging.getLogger("boot_to_browser")
_voice_queue: queue.Queue[tuple[str, bool, threading.Event | None]] = queue.Queue()
_stop_requested = threading.Event()
_playback_lock = threading.Lock()
_worker_started = False
_worker_lock = threading.Lock()
_pyttsx3_engine: object | None = None


def _ensure_mixer() -> object:
    """Initialize pygame mixer for audio playback."""
    import pygame

    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=22050, size=-16, channels=1)
    return pygame


def _play_file(path: str) -> bool:
    """Play an audio file until completion or stop request."""
    pygame = _ensure_mixer()
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            if _stop_requested.is_set():
                pygame.mixer.music.stop()
                return False
            pygame.time.wait(20)
        return not _stop_requested.is_set()
    except Exception:
        logger.exception("Could not play TTS audio")
        return False


def _edge_speech(text: str, target: Path) -> bool:
    """Generate speech with edge-tts and save it to a temporary MP3."""
    try:
        import edge_tts

        voice = os.getenv("TTS_VOICE", "en-IN-NeerjaNeural")

        async def _save() -> None:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(target))

        asyncio.run(_save())
        return target.is_file() and target.stat().st_size > 0
    except Exception:
        logger.warning("edge-tts failed; using local fallback")
        return False


def _piper_speech(text: str, target: Path) -> bool:
    """Use a local Piper ONNX model when one exists in models/."""
    model_files = list(Path("models").glob("*.onnx"))
    if not model_files:
        return False

    try:
        from piper.voice import PiperVoice

        voice = PiperVoice.load(str(model_files[0]))
        with target.open("wb") as audio_file:
            voice.synthesize(text, audio_file)
        return target.is_file() and target.stat().st_size > 0
    except Exception:
        logger.warning("piper-tts fallback failed")
        return False


def _pyttsx3_speech(text: str) -> bool:
    """Speak directly with the offline pyttsx3 engine."""
    global _pyttsx3_engine
    try:
        import pyttsx3

        _pyttsx3_engine = pyttsx3.init()
        engine = _pyttsx3_engine
        engine.say(text)
        engine.runAndWait()
        return True
    except Exception:
        logger.exception("pyttsx3 fallback failed")
        return False


def _synthesize(text: str, target: Path) -> bool:
    """Generate speech, falling back through local engines."""
    if _edge_speech(text, target):
        return True
    if _piper_speech(text, target):
        return True
    return _pyttsx3_speech(text)


def _worker() -> None:
    """Process queued speech messages sequentially."""
    while True:
        text, _blocking, completion = _voice_queue.get()

        with _playback_lock:
            _stop_requested.clear()
            print(text)
            temp_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                    temp_path = Path(temp_file.name)
                if not _edge_speech(text, temp_path):
                    if not _piper_speech(text, temp_path):
                        _pyttsx3_speech(text)
                    elif temp_path.is_file():
                        _play_file(str(temp_path))
                elif temp_path.is_file():
                    _play_file(str(temp_path))
            finally:
                if temp_path is not None:
                    temp_path.unlink(missing_ok=True)

        if completion is not None:
            completion.set()
        _voice_queue.task_done()


def _ensure_worker() -> None:
    """Start the queue worker once."""
    global _worker_started
    with _worker_lock:
        if not _worker_started:
            _worker_started = True
            threading.Thread(target=_worker, daemon=True).start()


def speak(text: str, blocking: bool = True) -> None:
    """Queue a spoken message, optionally waiting for playback."""
    logger.info("tts: %s", text)
    _ensure_worker()
    completion = threading.Event() if blocking else None
    _voice_queue.put((text, blocking, completion))
    if completion is not None:
        completion.wait()


def stop_speaking() -> None:
    """Immediately stop playback and clear queued messages."""
    _stop_requested.set()
    try:
        _ensure_mixer().mixer.music.stop()
    except Exception:
        pass

    if _pyttsx3_engine is not None:
        try:
            _pyttsx3_engine.stop()
        except Exception:
            pass

    while True:
        try:
            _voice_queue.get_nowait()
            _voice_queue.task_done()
        except queue.Empty:
            break


def play_chime() -> None:
    """Play a short generated sine tone without an audio file."""
    try:
        pygame = _ensure_mixer()
        sample_rate = 22050
        times = np.arange(int(sample_rate * 0.12), dtype=np.float32)
        samples = np.sin(2 * np.pi * 880 * times / sample_rate)
        pcm16 = (np.clip(samples * 0.25, -1.0, 1.0) * 32767).astype("<i2")
        stereo = np.column_stack((pcm16, pcm16)).reshape(-1).tobytes()
        pygame.sndarray.make_sound(stereo).play()
    except Exception:
        logger.exception("Could not play chime")
