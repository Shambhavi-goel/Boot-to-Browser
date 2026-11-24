"""Tests for evaluation task loading and result summaries."""

import csv
from pathlib import Path

import eval.run_eval as runner


def test_load_tasks_contains_twelve_tasks() -> None:
    """The bundled YAML suite contains exactly twelve tasks."""
    tasks = runner.load_tasks()

    assert len(tasks) == 12
    assert all(
        {"id", "goal", "start_state", "success_check", "expected_max_steps", "sensitive"}
        <= task.keys()
        for task in tasks
    )


def test_run_evaluation_with_mocked_runner(monkeypatch, tmp_path: Path) -> None:
    """Evaluation captures completion, retries, grounding, and latencies."""
    log_path = tmp_path / "actions.jsonl"
    monkeypatch.setattr(runner, "ACTION_LOG", log_path)
    log_path.write_text(
        '{"step":1,"action":{"action":"click","target_id":1,"text":null},'
        '"result":true,"latency_ms":{"act":20}}\n'
        '{"step":2,"action":{"action":"click","target_id":1,"text":null},'
        '"result":false,"latency_ms":{"act":30}}\n',
        encoding="utf-8",
    )

    responses = iter([[], [
        {"step": 1, "action": {"action": "click", "target_id": 1, "text": None}},
        {"step": 2, "action": {"action": "click", "target_id": 1, "text": None}},
    ]])
    monkeypatch.setattr(runner, "_read_action_log", lambda: next(responses))

    tasks = [{"id": "demo", "goal": "Do demo"}]
    rows = runner.run_evaluation(
        tasks=tasks,
        runner=lambda _goal: {
            "status": "done",
            "steps": 2,
            "latencies": {"act": 50},
        },
        grounding_prompt=lambda: "y",
    )

    assert rows[0]["completed"] is True
    assert rows[0]["steps"] == 2
    assert rows[0]["retries"] >= 1
    assert rows[0]["grounding_correct"] == 2
    assert rows[0]["grounding_total"] == 2


def test_write_results_and_summarize(tmp_path: Path) -> None:
    """CSV output and summary percentages are generated from result rows."""
    rows = [
        {
            "id": "one",
            "goal": "Task one",
            "completed": True,
            "steps": 2,
            "retries": 0,
            "latencies_ms": '{"plan":100,"act":200}',
            "grounding_correct": 1,
            "grounding_total": 1,
        },
        {
            "id": "two",
            "goal": "Task two",
            "completed": False,
            "steps": 3,
            "retries": 2,
            "latencies_ms": '{"plan":300,"act":400}',
            "grounding_correct": 0,
            "grounding_total": 1,
        },
    ]

    result_path = tmp_path / "results.csv"
    runner.write_results(rows, result_path)

    with result_path.open("r", newline="", encoding="utf-8") as csv_file:
        written = list(csv.DictReader(csv_file))

    summary = runner.summarize(rows)

    assert len(written) == 2
    assert summary["grounding_accuracy"] == 50.0
    assert summary["task_completion"] == 50.0
    assert summary["latency_median_ms"] == 250.0
