"""Tests for prompt building and Gemini-backed planning."""

import sys
from types import SimpleNamespace

from PIL import Image

from brain.planner import plan
from brain.prompts import build_user_prompt
from schema import Action, Element, Observation, StepRecord


class _FakeResponse:
    """Minimal Gemini response mock."""

    def __init__(self, text: str) -> None:
        self.text = text


class _FakeGenerativeModel:
    """Gemini model mock with configurable response sequence."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = [_FakeResponse(text) for text in responses]
        self.calls: list[list[object]] = []

    def generate_content(self, content: list[object], **kwargs: object) -> _FakeResponse:
        """Return the next mocked response."""
        self.calls.append(content)
        if len(self.calls) > len(self.responses):
            return self.responses[-1]
        return self.responses[len(self.calls) - 1]


def _observation(tmp_path, elements: list[Element] | None = None) -> Observation:
    """Create a synthetic annotated screenshot and observation."""
    image_path = tmp_path / "annotated.png"
    Image.new("RGB", (320, 180), "white").save(image_path)
    return Observation(
        image_path=str(image_path),
        elements=elements or [Element(id=1, bbox=(10, 20, 100, 80), label="Submit")],
        screen_size=(320, 180),
    )


def _mock_gemini(monkeypatch, responses: list[str]) -> _FakeGenerativeModel:
    """Install a mocked google.generativeai module and environment."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")

    fake_model = _FakeGenerativeModel(responses)
    fake_genai = SimpleNamespace(
        configure=lambda **kwargs: None,
        GenerativeModel=lambda model_name: fake_model,
    )
    monkeypatch.setitem(sys.modules, "google.generativeai", fake_genai)
    return fake_model


def test_build_user_prompt_is_compact() -> None:
    """The prompt includes the goal, last five steps, and element IDs."""
    elements = [Element(id=2, bbox=(1, 2, 3, 4), label="Search")]
    history = [
        StepRecord(
            step=1,
            action=Action(thought="Search", action="click", target_id=2),
            success=True,
            latency_ms={"plan": 100},
        )
    ]

    prompt = build_user_prompt("Open the page", elements, history)

    assert "Goal: Open the page" in prompt
    assert "1: click" in prompt
    assert "2: Search" in prompt


def test_plan_valid_json(monkeypatch, tmp_path) -> None:
    """A valid JSON response becomes an Action."""
    model = _mock_gemini(
        monkeypatch,
        ['{"thought":"Click submit","action":"click","target_id":1}'],
    )
    action = plan("Submit", _observation(tmp_path), [])

    assert action.action == "click"
    assert action.target_id == 1
    assert len(model.calls) == 1


def test_plan_fenced_json(monkeypatch, tmp_path) -> None:
    """Markdown fences are stripped before Pydantic validation."""
    _mock_gemini(
        monkeypatch,
        ['```json\n{"thought":"Wait","action":"wait"}\n```'],
    )

    action = plan("Wait", _observation(tmp_path), [])

    assert action.action == "wait"


def test_plan_retries_malformed_then_fixed(monkeypatch, tmp_path) -> None:
    """Malformed output causes one retry with the validation error appended."""
    model = _mock_gemini(
        monkeypatch,
        ["not json", '{"thought":"Done","action":"done","goal_complete":true}'],
    )

    action = plan("Finish", _observation(tmp_path), [])

    assert action.action == "done"
    assert action.goal_complete is True
    assert len(model.calls) == 2


def test_plan_total_failure_returns_ask_user(monkeypatch, tmp_path) -> None:
    """Two invalid responses return the safe fallback action."""
    _mock_gemini(monkeypatch, ["bad", "still bad"])

    action = plan("Unknown", _observation(tmp_path), [])

    assert action.action == "ask_user"
    assert action.thought == "I could not decide"
