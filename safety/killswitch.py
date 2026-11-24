"""Thread-safe application abort state and interrupt listeners."""

from threading import Event, Lock, Thread

_abort_lock = Lock()
_aborted = False
_listening = False
_listener_stop = Event()
_listener_thread: Thread | None = None
_hotkey_handle: object | None = None


def is_aborted() -> bool:
    """Return whether a global abort has been requested."""
    with _abort_lock:
        return _aborted


def trigger_abort() -> None:
    """Stop speech and set the global abort flag."""
    global _aborted
    with _abort_lock:
        _aborted = True

    try:
        from voice.tts import stop_speaking

        stop_speaking()
    except (ImportError, AttributeError):
        pass

    try:
        from voice.tts import speak

        speak("Stopped.")
    except (ImportError, AttributeError):
        pass


def reset_abort() -> None:
    """Clear the global abort state."""
    global _aborted
    with _abort_lock:
        _aborted = False


def _spoken_stop_listener() -> None:
    """Listen in short chunks for the spoken word "stop"."""
    while not _listener_stop.is_set():
        try:
            import sounddevice  # noqa: F401

            reply = ""
            try:
                from voice.stt import listen

                reply = listen()
            except (ImportError, TypeError):
                return

            if "stop" in reply.lower():
                trigger_abort()
                return
        except ImportError:
            return


def start_killswitch() -> None:
    """Start the keyboard hotkey and optional spoken-stop listener."""
    global _hotkey_handle, _listener_thread, _listening

    if not _listening:
        _listening = True
        _listener_stop.clear()
        _listener_thread = Thread(target=_spoken_stop_listener, daemon=True)
        _listener_thread.start()

    try:
        import keyboard

        _hotkey_handle = keyboard.add_hotkey("ctrl+shift+x", trigger_abort)
    except ImportError:
        pass


def stop_killswitch() -> None:
    """Stop both kill-switch listening mechanisms."""
    global _hotkey_handle, _listener_thread, _listening

    _listener_stop.set()
    _listener_thread = None
    _listening = False

    if _hotkey_handle is not None:
        try:
            import keyboard

            keyboard.remove_hotkey(_hotkey_handle)
        except (ImportError, AttributeError):
            pass
        _hotkey_handle = None
