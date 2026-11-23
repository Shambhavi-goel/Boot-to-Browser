"""Shared Pydantic data types for the agent loop."""

from typing import Literal

from pydantic import BaseModel


class Element(BaseModel):
    """A visually grounded element in real screen pixels."""

    id: int
    bbox: tuple[int, int, int, int]
    label: str


class Observation(BaseModel):
    """A captured screen and the elements detected in it."""

    image_path: str
    elements: list[Element]
    screen_size: tuple[int, int]


class Action(BaseModel):
    """One action planned for the next agent step."""

    thought: str
    action: Literal["click", "type", "scroll", "press", "wait", "done", "ask_user"]
    target_id: int | None = None
    text: str | None = None
    is_sensitive: bool = False
    goal_complete: bool = False


class StepRecord(BaseModel):
    """The result and timing of an agent step."""

    step: int
    action: Action
    success: bool
    latency_ms: dict[str, int]
