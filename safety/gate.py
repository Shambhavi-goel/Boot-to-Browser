"""Confirmation checks for sensitive or ambiguous actions."""

import threading

from schema import Action

CONFIRMATION_KEYWORDS = (
    "send",
    "pay",
    "payment",
    "transfer",
    "delete",
    "remove",
    "submit",
    "confirm",
    "purchase",
    "buy",
    "password",
    "otp",
)


def needs_confirmation(action: Action) -> bool:
    """Return whether an action requires explicit user confirmation."""
    if action.is_sensitive:
        return True

    searchable = " ".join(
        value
        for value in (action.thought, action.text)
        if isinstance(value, str)
    ).lower()
    return any(keyword in searchable for keyword in CONFIRMATION_KEYWORDS)


def build_prompt(action: Action) -> str:
    """Build a clear spoken confirmation question."""
    if action.action == "type" and action.text:
        target = f"Type {action.text}?"
    elif action.thought:
        target = action.thought.rstrip(".?")
    else:
        target = f"Perform {action.action}?"
    return f"{target} Say confirm to continue."


def confirm_with_user(prompt: str) -> bool:
    """Speak a prompt and wait up to eight seconds for confirmation."""
    from voice.stt import listen
    from voice.tts import speak

    speak(prompt)

    reply: list[str] = []

    def _listen() -> None:
        reply.append(listen())

    listener = threading.Thread(target=_listen, daemon=True)
    listener.start()
    listener.join(timeout=8.0)

    if listener.is_alive() or not reply:
        return False

    answer = reply[0].lower()
    return "yes" in answer or "confirm" in answer
