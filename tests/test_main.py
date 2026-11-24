"""Mocked tests for the voice and text entry point."""

import sys

import pytest

import main


def test_text_mode_runs_task_and_speaks_status(monkeypatch: pytest.MonkeyPatch) -> None:
    """The --text flag runs one task without starting voice hardware."""
    spoken: list[str] = []
    monkeypatch.setattr(main, "run_task", lambda goal: {"status": "done", "steps": 1})
    monkeypatch.setattr(main, "speak", lambda text: spoken.append(text))
    monkeypatch.setattr(main, "summarize_for_speech", lambda _n: "One step completed")
    monkeypatch.setattr(sys, "argv", ["main.py", "--text", "Open browser"])

    main.main()

    assert spoken == ["Done", "One step completed"]


def test_voice_loop_handles_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Voice mode exits cleanly when push-to-talk returns quit."""
    started: list[str] = []
    stopped: list[str] = []
    spoken: list[str] = []

    monkeypatch.setattr(main, "start_killswitch", lambda: started.append("started"))
    monkeypatch.setattr(main, "stop_killswitch", lambda: stopped.append("stopped"))
    monkeypatch.setattr(main, "play_chime", lambda: None)
    monkeypatch.setattr(main, "listen_push_to_talk", lambda _key: "quit")
    monkeypatch.setattr(main, "speak", lambda text: spoken.append(text))
    monkeypatch.setattr("startup.boot.run_boot_sequence", lambda: main.speak("Co-pilot ready"))
    monkeypatch.setattr(sys, "argv", ["main.py"])

    main.main()

    assert started == ["started"]
    assert stopped == ["stopped"]
    assert spoken[:2] == ["Co-pilot ready", "Goodbye"]


def test_voice_loop_handles_task_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """A task exception speaks a short error and continues until exit."""
    transcripts = iter(["Open browser", "quit"])
    spoken: list[str] = []

    monkeypatch.setattr(main, "start_killswitch", lambda: None)
    monkeypatch.setattr(main, "stop_killswitch", lambda: None)
    monkeypatch.setattr(main, "play_chime", lambda: None)
    monkeypatch.setattr(main, "listen_push_to_talk", lambda _key: next(transcripts))
    monkeypatch.setattr(main, "run_task", lambda _goal: (_ for _ in ()).throw(RuntimeError("failed")))
    monkeypatch.setattr(main, "speak", lambda text: spoken.append(text))
    monkeypatch.setattr(
        "startup.boot.run_boot_sequence",
        lambda: main.speak("Co-pilot ready"),
    )
    monkeypatch.setattr(sys, "argv", ["main.py"])

    main.main()

    assert "Sorry, that task failed" in spoken
    assert "Goodbye" in spoken
