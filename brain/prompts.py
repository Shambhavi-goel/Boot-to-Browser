"""Prompts for the Gemini computer-action planner."""

from schema import Element, Observation, StepRecord

SYSTEM_PROMPT = """You operate a computer for a blind user. The screenshot has numbered boxes.
Return exactly ONE next action as JSON matching the Action schema, nothing else.
Set is_sensitive=true for sending, paying, deleting, submitting.
Use ask_user if unsure.
Use done with goal_complete=true only when the goal is visibly achieved.
Never type passwords or OTPs; use ask_user instead."""


def build_user_prompt(
    goal: str,
    elements: list[Element],
    history: list[StepRecord],
) -> str:
    """Build a compact prompt containing the goal, recent history, and visible elements."""
    recent_history = history[-5:]
    history_lines = [
        f"{record.step}: {record.action.action}"
        + (f" target={record.action.target_id}" if record.action.target_id is not None else "")
        + (f" success={str(record.success).lower()}" if record.success is False else "")
        for record in recent_history
    ]

    element_lines = [f"{element.id}: {element.label}" for element in elements]
    history_text = "\n".join(history_lines) if history_lines else "none"
    elements_text = "\n".join(element_lines) if element_lines else "none"

    return (
        f"Goal: {goal}\n"
        f"Last 5 steps:\n{history_text}\n"
        f"Elements:\n{elements_text}"
    )
