"""Command-line entry point for the typed-input agent prototype."""

import argparse

from graph import agent_graph
from safety.killswitch import reset_abort
from voice.stt import listen
from voice.tts import speak


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

    result: dict[str, object] = {
        "status": final_state.get("status", "failed"),
        "steps": final_state.get("step_count", 0),
        "latencies": latencies,
    }
    speak(str(result["status"]))
    return result


def main() -> None:
    """Run one text goal or start the typed-input command loop."""
    parser = argparse.ArgumentParser(description="Boot-to-Browser agent")
    parser.add_argument("--text", help="Run one typed goal and exit")
    args = parser.parse_args()

    if args.text:
        run_task(args.text)
        return

    while True:
        goal = listen()
        if not goal:
            continue
        if goal.lower() in {"exit", "quit"}:
            return
        run_task(goal)


if __name__ == "__main__":
    main()
