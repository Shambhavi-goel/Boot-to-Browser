"""Mocked tests for desktop actions and visual verification."""

import sys
from types import SimpleNamespace

import pytest
from PIL import Image

from actions.desktop import AbortedError, execute
from actions.verify import screen_changed
from schema import Action, Element, Observation
from safety.killswitch import reset_abort, trigger_abort


def _observation() -> Observation:
    """Create an observation with one target element."""
    return Observation(
        image_path="logs/test.png",
        elements=[Element(id=7, bbox=(100, 200, 300, 400), label="Submit")],
        screen_size=(800, 600),
    )


def _mock_pyautogui(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Install a pyautogui module mock."""
    calls: list[tuple[str, tuple[object, ...]]] = []

    def record(name: str, *args: object) -> None:
        calls.append((name, args))

    pyautogui = SimpleNamespace(
        FAILSAFE=False,
        PAUSE=0,
        click=lambda *args: record("click", *args),
        write=lambda *args, **kwargs: record("write", *args),
        scroll=lambda *args: record("scroll", *args),
        press=lambda *args: record("press", *args),
        hotkey=lambda *args: record("hotkey", *args),
        calls=calls,
    )
    monkeypatch.setitem(sys.modules, "pyautogui", pyautogui)
    return pyautogui


def test_click_uses_target_centre(monkeypatch: pytest.MonkeyPatch) -> None:
    """Click sends the centre of the target bounding box."""
    reset_abort()
    pyautogui = _mock_pyautogui(monkeypatch)

    result = execute(
        Action(thought="Click submit", action="click", target_id=7),
        _observation(),
    )

    assert result is True
    assert ("click", (200, 300)) in pyautogui.calls


def test_type_clicks_target_then_types(monkeypatch: pytest.MonkeyPatch) -> None:
    """Type first clicks the target, then writes the text."""
    reset_abort()
    pyautogui = _mock_pyautogui(monkeypatch)

    result = execute(
        Action(thought="Enter text", action="type", target_id=7, text="hello"),
        _observation(),
    )

    assert result is True
    assert pyautogui.calls[0] == ("click", (200, 300))
    assert pyautogui.calls[1] == ("write", ("hello",))


def test_abort_stops_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    """The kill switch raises before pyautogui is called."""
    reset_abort()
    pyautogui = _mock_pyautogui(monkeypatch)
    trigger_abort()

    with pytest.raises(AbortedError):
        execute(
            Action(thought="Click", action="click", target_id=7),
            _observation(),
        )

    assert pyautogui.calls == []
    reset_abort()


def test_missing_target_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unknown target IDs do not perform a desktop call."""
    reset_abort()
    pyautogui = _mock_pyautogui(monkeypatch)

    result = execute(
        Action(thought="Missing", action="click", target_id=99),
        _observation(),
    )

    assert result is False
    assert pyautogui.calls == []


def test_screen_changed() -> None:
    """Downscaled images detect meaningful pixel changes."""
    before = Image.new("RGB", (320, 180), "white")
    after = Image.new("RGB", (320, 180), "black")

    assert screen_changed(before, after) is True
    assert screen_changed(before, before.copy()) is False
