"""Thread-safe application abort state."""

from threading import Lock

_abort_lock = Lock()
_aborted = False


def is_aborted() -> bool:
    """Return whether a global abort has been requested."""
    with _abort_lock:
        return _aborted


def trigger_abort() -> None:
    """Request that pending and future actions stop."""
    global _aborted
    with _abort_lock:
        _aborted = True


def reset_abort() -> None:
    """Clear the global abort state."""
    global _aborted
    with _abort_lock:
        _aborted = False
