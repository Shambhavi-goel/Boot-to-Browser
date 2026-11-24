"""Mocked tests for microphone recording and speech transcription."""

from types import SimpleNamespace

import numpy as np
import pytest

import voice.stt as stt


class _FakeModel:
    """Faster-Whisper model mock."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[tuple[object, bool]] = []

    def transcribe(self, audio: object, vad_filter: bool = False) -> tuple[list[object], object]:
        """Return a single mocked segment and metadata."""
        self.calls.append((audio, vad_filter))
        return [SimpleNamespace(text=self.text)], SimpleNamespace()


def test_listen_empty_audio_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty VAD output skips model loading and returns an empty string."""
    monkeypatch.setattr(stt, "record", lambda: np.empty(0, dtype=np.float32))
    monkeypatch.setattr(stt, "_model", None)

    def fail_model() -> object:
        raise AssertionError("Whisper model should not load for empty audio")

    monkeypatch.setattr(stt, "_get_model", fail_model)

    assert stt.listen() == ""


def test_listen_normal_audio_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Normal audio is sent to Whisper with VAD filtering enabled."""
    audio = np.ones(1600, dtype=np.float32)
    fake_model = _FakeModel("  Open the browser  ")
    monkeypatch.setattr(stt, "record", lambda: audio)
    monkeypatch.setattr(stt, "_get_model", lambda: fake_model)

    result = stt.listen()

    assert result == "Open the browser"
    assert fake_model.calls == [(audio, True)]


def test_listen_push_to_talk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Push-to-talk waits on the requested key before recording."""
    waited: list[str] = []
    fake_keyboard = SimpleNamespace(wait=lambda key: waited.append(key))
    monkeypatch.setitem(__import__("sys").modules, "keyboard", fake_keyboard)
    monkeypatch.setattr(stt, "listen", lambda: "Hello")

    assert stt.listen_push_to_talk("f10") == "Hello"
    assert waited == ["f10"]


def test_edge_tts_failure_uses_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Edge-tts failure delegates to the offline fallback."""
    import voice.tts as tts

    monkeypatch.setattr(tts, "_edge_speech", lambda _text, _target: False)
    monkeypatch.setattr(tts, "_piper_speech", lambda _text, _target: False)
    fallback_calls: list[str] = []
    monkeypatch.setattr(
        tts,
        "_pyttsx3_speech",
        lambda text: fallback_calls.append(text) or True,
    )

    assert tts._pyttsx3_speech("Test fallback") is True


def test_stop_speaking_halts_playback(monkeypatch: pytest.MonkeyPatch) -> None:
    """stop_speaking halts pygame and offline pyttsx3 playback."""
    import voice.tts as tts

    stopped: list[str] = []
    fake_mixer = SimpleNamespace(
        mixer=SimpleNamespace(music=SimpleNamespace(stop=lambda: stopped.append("pygame")))
    )
    monkeypatch.setattr(tts, "_ensure_mixer", lambda: fake_mixer)

    class _Engine:
        def stop(self) -> None:
            stopped.append("pyttsx3")

    monkeypatch.setattr(tts, "_pyttsx3_engine", _Engine())

    tts.stop_speaking()

    assert set(stopped) == {"pygame", "pyttsx3"}
