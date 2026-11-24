"""Append-only JSONL logging for agent actions."""

import json
from pathlib import Path

from schema import Action

ACTION_LOG = Path("logs") / "actions.jsonl"


def log_action(
    step: int,
    action: Action,
    result: bool,
    latency_ms: dict[str, int],
) -> None:
    """Append one action record to the JSONL action log."""
    ACTION_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "step": step,
        "action": action.model_dump(),
        "result": result,
        "latency_ms": latency_ms,
    }
    with ACTION_LOG.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(record) + "\n")


def read_recent(n: int) -> list[dict[str, object]]:
    """Read the latest n action records."""
    if n <= 0 or not ACTION_LOG.exists():
        return []

    records: list[dict[str, object]] = []
    with ACTION_LOG.open("r", encoding="utf-8") as log_file:
        for line in log_file:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records[-n:]


def summarize_for_speech(n: int) -> str:
    """Summarize recent actions in a short spoken sentence."""
    records = read_recent(n)
    if not records:
        return "No recent actions."

    summaries: list[str] = []
    for record in records:
        action = record.get("action")
        action_name = action.get("action") if isinstance(action, dict) else "unknown"
        result = "succeeded" if record.get("result") is True else "failed"
        summaries.append(f"Step {record.get('step')}: {action_name} {result}")
    return "; ".join(summaries)
