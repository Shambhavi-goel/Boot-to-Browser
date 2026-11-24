"""Tests for confirmation, kill-switch, and action logging safety modules."""

from PIL import Image

import graph
import safety.log as action_log
from safety.gate import confirm_with_user, needs_confirmation
from safety.killswitch import reset_abort, trigger_abort, is_aborted
from schema import Action, Element, Observation


def test_sensitive_keyword_detection() -> None:
    """Sensitive flags and confirmation keywords require confirmation."""
    assert needs_confirmation(Action(thought="Delete files", action="press")) is True
    assert needs_confirmation(Action(thought="Do normal task", action="click", is_sensitive=True)) is True
    assert needs_confirmation(Action(thought="Open menu", action="click")) is False


def test_confirm_with_user_no_reply(monkeypatch) -> None:
    """Empty confirmation replies are denied."""
    monkeypatch.setattr("voice.speak", lambda _text: None, raising=False)
    monkeypatch.setattr("voice.stt.listen", lambda: "")
    monkeypatch.setattr("voice.tts.speak", lambda _text: None)

    assert confirm_with_user("Continue? Say confirm.") is False


def test_confirm_with_user_accepts_confirm(monkeypatch) -> None:
    """A reply containing confirm is accepted."""
    monkeypatch.setattr("voice.tts.speak", lambda _text: None)
    monkeypatch.setattr("voice.stt.listen", lambda: "Yes, confirm")

    assert confirm_with_user("Continue? Say confirm.") is True


def test_abort_flag_toggles() -> None:
    """Trigger and reset update the thread-safe abort flag."""
    reset_abort()
    assert is_aborted() is False
    trigger_abort()
    assert is_aborted() is True
    reset_abort()
    assert is_aborted() is False


def test_action_log_round_trip(monkeypatch, tmp_path) -> None:
    """Action records append and round-trip through JSONL helpers."""
    log_path = tmp_path / "actions.jsonl"
    monkeypatch.setattr(action_log, "ACTION_LOG", log_path)
    action = Action(thought="Click submit", action="click", target_id=1)

    action_log.log_action(1, action, True, {"act": 25})
    action_log.log_action(2, action, False, {"act": 30})

    records = action_log.read_recent(2)

    assert len(records) == 2
    assert records[-1]["result"] is False
    assert "click" in action_log.summarize_for_speech(2)


def test_graph_ends_when_confirmation_denied(monkeypatch, tmp_path) -> None:
    """Denied sensitive confirmation prevents act and ends the graph."""
    from safety.killswitch import reset_abort

    reset_abort()
    image_path = tmp_path / "screen.png"
    Image.new("RGB", (320, 180), "white").save(image_path)
    observation = Observation(
        image_path=str(image_path),
        elements=[Element(id=1, bbox=(20, 20, 100, 80), label="Delete")],
        screen_size=(320, 180),
    )

    monkeypatch.setattr(graph, "observe", lambda: observation)
    monkeypatch.setattr(
        graph,
        "plan",
        lambda _goal, _obs, _history: Action(
            thought="Delete these files",
            action="press",
            text="delete",
            is_sensitive=True,
        ),
    )
    monkeypatch.setattr(graph, "confirm_with_user", lambda _prompt: False)
    monkeypatch.setattr(graph, "log_action", lambda *_args: None)
    monkeypatch.setattr(graph, "execute", lambda *_args: (_ for _ in ()).throw(AssertionError()))
    monkeypatch.setattr(graph, "speak", lambda _text: None)

    initial = {
        "goal": "Delete files",
        "history": [],
        "observation": None,
        "action": None,
        "step_count": 0,
        "retry_count": 0,
        "status": "running",
        "stage_latency_ms": {},
    }

    final = graph.agent_graph.invoke(initial)

    assert final["status"] == "failed"
    assert final["step_count"] == 0
