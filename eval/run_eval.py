"""Interactive evaluation runner for Boot-to-Browser tasks."""

import csv
import json
import statistics
from pathlib import Path
from typing import Callable

import main

RESULTS_PATH = Path(__file__).parent / "results.csv"
TASKS_PATH = Path(__file__).parent / "tasks.yaml"
ACTION_LOG = Path("logs") / "actions.jsonl"


def load_tasks(path: Path | None = None) -> list[dict[str, object]]:
    """Load evaluation tasks from YAML."""
    import yaml

    task_path = path or TASKS_PATH
    with task_path.open("r", encoding="utf-8") as task_file:
        data = yaml.safe_load(task_file)
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
        raise ValueError("Invalid evaluation task file")
    return data["tasks"]


def _read_action_log() -> list[dict[str, object]]:
    """Read all action JSONL records."""
    if not ACTION_LOG.exists():
        return []
    records: list[dict[str, object]] = []
    with ACTION_LOG.open("r", encoding="utf-8") as log_file:
        for line in log_file:
            if line.strip():
                records.append(json.loads(line))
    return records


def ask_grounding() -> str:
    """Ask whether an executed click was correctly grounded."""
    while True:
        reply = input("Was the last click correctly grounded? [y/n/s(skip)]: ").strip().lower()
        if reply in {"y", "n", "s", "skip"}:
            return "skip" if reply == "s" else reply
        print("Please enter y, n, or s.")


def _percentile(values: list[float], percentile: float) -> float:
    """Calculate a percentile with a simple nearest-rank method."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * percentile)))
    return ordered[index]


def run_evaluation(
    tasks: list[dict[str, object]] | None = None,
    runner: Callable[[str], dict[str, object]] = main.run_task,
    grounding_prompt: Callable[[], str] = ask_grounding,
) -> list[dict[str, object]]:
    """Run tasks and return one result row per task."""
    task_list = tasks or load_tasks()
    rows: list[dict[str, object]] = []

    for task in task_list:
        goal = str(task["goal"])
        baseline_count = len(_read_action_log())
        result = runner(goal)
        action_records = _read_action_log()[baseline_count:]

        grounding_correct = 0
        grounding_total = 0
        for record in action_records:
            action = record.get("action")
            if not isinstance(action, dict) or action.get("action") != "click":
                continue
            answer = grounding_prompt()
            if answer != "skip":
                grounding_correct += int(answer == "y")
                grounding_total += 1

        status = str(result.get("status", "failed"))
        steps = int(result.get("steps", 0))
        latencies = result.get("latencies", {})
        latency_map = latencies if isinstance(latencies, dict) else {}

        repeated_actions: list[tuple[object, object, object]] = []
        retries = 0
        for record in action_records:
            action = record.get("action")
            if isinstance(action, dict):
                signature = (action.get("action"), action.get("target_id"), action.get("text"))
                if repeated_actions and repeated_actions[-1] == signature:
                    retries += 1
                repeated_actions.append(signature)

        rows.append(
            {
                "id": task["id"],
                "goal": goal,
                "completed": status == "done",
                "steps": steps,
                "retries": retries,
                "latencies_ms": json.dumps(latency_map),
                "grounding_correct": grounding_correct,
                "grounding_total": grounding_total,
            }
        )

    return rows


def summarize(rows: list[dict[str, object]]) -> dict[str, float]:
    """Calculate grounding, completion, and latency summary statistics."""
    completed = sum(1 for row in rows if row["completed"])
    task_latencies: list[float] = []
    stage_latencies: list[float] = []

    grounding_correct = sum(int(row.get("grounding_correct", 0)) for row in rows)
    grounding_total = sum(int(row.get("grounding_total", 0)) for row in rows)

    for row in rows:
        latency_map = json.loads(str(row.get("latencies_ms", "{}")))
        task_total = 0.0
        for stage_latency in latency_map.values():
            if isinstance(stage_latency, int | float):
                value = float(stage_latency)
                stage_latencies.append(value)
                task_total += value
        if task_total:
            task_latencies.append(task_total)

    return {
        "grounding_accuracy": (grounding_correct / grounding_total * 100) if grounding_total > 0 else 0.0,
        "task_completion": (completed / len(rows) * 100) if rows else 0.0,
        "latency_median_ms": statistics.median(stage_latencies) if stage_latencies else 0.0,
        "latency_p90_ms": _percentile(stage_latencies, 0.9),
        "task_latency_median_ms": statistics.median(task_latencies) if task_latencies else 0.0,
        "task_latency_p90_ms": _percentile(task_latencies, 0.9),
    }


def write_results(rows: list[dict[str, object]], path: Path | None = None) -> None:
    """Write evaluation rows to CSV."""
    result_path = path or RESULTS_PATH
    result_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id", "goal", "completed", "steps", "retries", "latencies_ms",
        "grounding_correct", "grounding_total",
    ]
    with result_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(summary: dict[str, float]) -> None:
    """Print the evaluation summary."""
    print(f"Grounding accuracy: {summary['grounding_accuracy']:.1f}%")
    print(f"Task completion rate: {summary['task_completion']:.1f}%")
    print(f"Median latency per stage: {summary['latency_median_ms']:.1f} ms")
    print(f"P90 latency per stage: {summary['latency_p90_ms']:.1f} ms")
    print(f"Median latency per task: {summary['task_latency_median_ms']:.1f} ms")
    print(f"P90 latency per task: {summary['task_latency_p90_ms']:.1f} ms")


def main() -> None:
    """Run the interactive evaluation and write its summary."""
    rows = run_evaluation()
    write_results(rows)
    print_summary(summarize(rows))


if __name__ == "__main__":
    main()
