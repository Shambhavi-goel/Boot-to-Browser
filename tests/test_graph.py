"""Mocked tests for the LangGraph agent loop."""

from PIL import Image

import graph
from schema import Action, Element, Observation
from safety.killswitch import reset_abort, trigger_abort


def _observation(tmp_path, name: str = "before.png") -> Observation:
    """Create a synthetic observation and image file."""
    image_path = tmp_path / name
    Image.new("RGB", (320, 180), "white").save(image_path)
    return Observation(
        image_path=str(image_path),
        elements=[Element(id=1, bbox=(20, 20, 120, 80), label="Search")],
        screen_size=(320, 180),
    )


def _initial_state(goal: str = "Complete task") -> dict:
    """Return a fresh running graph state."""
    return {
        "goal": goal,
        "history": [],
        "observation": None,
        "action": None,
        "step_count": 0,
        "retry_count": 0,
        "status": "running",
        "stage_latency_ms": {},
    }


def test_happy_path(monkeypatch, tmp_path) -> None:
    """Observe, plan a complete action, act, and finish."""
    reset_abort()
    observation = _observation(tmp_path)
    monkeypatch.setattr(graph, "observe", lambda: observation)
    monkeypatch.setattr(
        graph,
        "plan",
        lambda _goal, _obs, _history: Action(
            thought="Finished visibly",
            action="done",
            goal_complete=True,
        ),
    )
    monkeypatch.setattr(graph, "execute", lambda _action, _obs: True)
    monkeypatch.setattr(graph, "speak", lambda _text: None)

    final = graph.agent_graph.invoke(_initial_state())

    assert final["status"] == "done"
    assert final["step_count"] == 1


def test_retry_then_fail(monkeypatch, tmp_path) -> None:
    """Two unchanged observations end the loop with failed and stuck status."""
    reset_abort()
    before = _observation(tmp_path, "before.png")
    after = _observation(tmp_path, "after.png")
    observations = iter([before, after, after])
    monkeypatch.setattr(graph, "observe", lambda: next(observations))
    monkeypatch.setattr(
        graph,
        "plan",
        lambda _goal, _obs, _history: Action(
            thought="Try the same action",
            action="click",
            target_id=1,
        ),
    )
    monkeypatch.setattr(graph, "execute", lambda _action, _obs: True)
    monkeypatch.setattr(graph, "screen_changed", lambda _before, _after: False)
    monkeypatch.setattr(graph, "speak", lambda _text: None)

    final = graph.agent_graph.invoke(_initial_state())

    assert final["status"] == "failed"
    assert final["retry_count"] == 2


def test_step_cap(monkeypatch, tmp_path) -> None:
    """A changed screen is still stopped at the maximum step count."""
    reset_abort()
    observation = _observation(tmp_path)
    monkeypatch.setattr(graph, "observe", lambda: observation)
    monkeypatch.setattr(
        graph,
        "plan",
        lambda _goal, _obs, _history: Action(
            thought="Scroll",
            action="scroll",
            text="down",
        ),
    )
    monkeypatch.setattr(graph, "execute", lambda _action, _obs: True)
    monkeypatch.setattr(graph, "screen_changed", lambda _before, _after: True)
    monkeypatch.setattr(graph, "speak", lambda _text: None)
    monkeypatch.setattr(graph, "MAX_STEPS", 1)

    final = graph.agent_graph.invoke(_initial_state())

    assert final["status"] == "failed"
    assert final["step_count"] == 1


def test_abort(monkeypatch, tmp_path) -> None:
    """The abort flag stops execution before an observe action."""
    reset_abort()
    observation = _observation(tmp_path)
    monkeypatch.setattr(graph, "observe", lambda: observation)
    monkeypatch.setattr(graph, "speak", lambda _text: None)
    trigger_abort()

    final = graph.agent_graph.invoke(_initial_state())

    assert final["status"] == "aborted"
    assert final["step_count"] == 0
    reset_abort()
