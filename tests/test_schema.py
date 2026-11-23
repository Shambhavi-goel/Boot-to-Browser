"""Tests for shared Pydantic schemas."""

from schema import Action, Element, Observation, StepRecord


def test_element_and_observation_models() -> None:
    """Element and observation coordinates retain screen-space tuples."""
    element = Element(id=1, bbox=(10, 20, 100, 80), label="Submit")
    observation = Observation(
        image_path="logs/obs.png",
        elements=[element],
        screen_size=(1920, 1080),
    )

    assert observation.elements[0].bbox == (10, 20, 100, 80)
    assert observation.screen_size == (1920, 1080)


def test_action_and_step_record_defaults() -> None:
    """Optional action fields and sensitivity defaults are preserved."""
    action = Action(thought="Finish", action="done", goal_complete=True)
    record = StepRecord(step=1, action=action, success=True, latency_ms={"capture": 12})

    assert action.target_id is None
    assert action.text is None
    assert action.is_sensitive is False
    assert record.latency_ms["capture"] == 12
