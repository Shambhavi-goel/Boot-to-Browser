"""Voice-driven command-line entry point for the autonomous agent."""

import argparse
import logging

from graph import agent_graph
from safety.killswitch import reset_abort, start_killswitch, stop_killswitch
from safety.log import summarize_for_speech
from voice.stt import listen_push_to_talk
from voice.tts import play_chime, speak

logger = logging.getLogger("boot_to_browser")


def run_task(goal: str) -> dict[str, object]:
    """Run one goal through the agent graph and return summary information."""
    reset_abort()
    initial_state = {
        "goal": goal,
        "history": [],
        "observation": None,
        "action": None,
        "step_count": 0,
        "retry_count": 0,
        "status": "running",
        "stage_latency_ms": {},
    }
    final_state = agent_graph.invoke(initial_state)

    latencies: dict[str, int] = {}
    for record in final_state.get("history", []):
        for stage, latency in record.latency_ms.items():
            latencies.setdefault(stage, 0)
            latencies[stage] += latency

    return {
        "status": final_state.get("status", "failed"),
        "steps": final_state.get("step_count", 0),
        "latencies": latencies,
    }


def _status_message(status: object) -> str:
    """Translate a graph status into a short spoken status."""
    if status == "done":
        return "Done"
    if status == "aborted":
        return "Stopped"
    return "I'm stuck"


def main() -> None:
    """Run one text goal or start the voice command loop."""
    parser = argparse.ArgumentParser(description="Boot-to-Browser agent")
    parser.add_argument("--text", help="Run one typed goal and exit")
    args = parser.parse_args()

    if args.text:
        try:
            result = run_task(args.text)
            speak(_status_message(result.get("status")))
            speak(summarize_for_speech(5))
        except Exception:
            logger.exception("Text task failed")
            speak("Sorry, that task failed")
        return

    start_killswitch()
    from startup.boot import run_boot_sequence

    run_boot_sequence()

    try:
        while True:
            try:
                goal = listen_push_to_talk("f9")
                if not goal:
                    continue

                if goal.lower().strip() in {"exit", "quit"}:
                    speak("Goodbye")
                    return

                result = run_task(goal)
                speak(_status_message(result.get("status")))
                speak(summarize_for_speech(5))
            except Exception:
                logger.exception("Voice task failed")
                speak("Sorry, that task failed")
    finally:
        stop_killswitch()


if __name__ == "__main__":
    main()
