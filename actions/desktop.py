"""Execute planned actions through the Windows desktop."""

import logging
import time

from schema import Action, Observation
from safety.killswitch import is_aborted

logger = logging.getLogger("boot_to_browser")


class AbortedError(RuntimeError):
    """Raised when the kill switch stops an action."""


def _check_aborted() -> None:
    """Raise before every guarded pyautogui call."""
    if is_aborted():
        raise AbortedError("Action aborted")


def _target_centre(action: Action, obs: Observation) -> tuple[int, int] | None:
    """Find the target element and return its real-screen centre."""
    if action.target_id is None:
        return None
    for element in obs.elements:
        if element.id == action.target_id:
            x1, y1, x2, y2 = element.bbox
            return ((x1 + x2) // 2, (y1 + y2) // 2)
    return None


def execute(action: Action, obs: Observation) -> bool:
    """Execute one desktop action and report whether it was performed."""
    import pyautogui

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1

    if action.action in {"done", "ask_user"}:
        return True

    centre = _target_centre(action, obs)
    if action.target_id is not None and centre is None:
        logger.warning("Target id %d was not found", action.target_id)
        return False

    try:
        if action.action == "click":
            if centre is None:
                logger.warning("Click action has no target id")
                return False
            _check_aborted()
            pyautogui.click(*centre)

        elif action.action == "type":
            if centre is not None:
                _check_aborted()
                pyautogui.click(*centre)
            if action.text:
                _check_aborted()
                pyautogui.write(action.text, interval=0.05)

        elif action.action == "scroll":
            direction = (action.text or "down").lower()
            amount = -600 if direction == "up" else 600
            _check_aborted()
            pyautogui.scroll(amount)

        elif action.action == "press":
            text = (action.text or "").strip()
            if not text:
                logger.warning("Press action has no key or hotkey text")
                return False
            parts = [part.strip() for part in text.split("+")]
            _check_aborted()
            if len(parts) > 1:
                pyautogui.hotkey(*parts)
            else:
                pyautogui.press(parts[0])

        elif action.action == "wait":
            _check_aborted()
            time.sleep(1)

        else:
            logger.warning("Unsupported action: %s", action.action)
            return False
    except AbortedError:
        raise

    time.sleep(0.1)
    return True
