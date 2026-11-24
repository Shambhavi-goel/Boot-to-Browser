"""LangGraph agent loop for observe, plan, act, and verify."""

import time
from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph

from actions.desktop import AbortedError, execute
from actions.verify import screen_changed
from brain.planner import plan
from config import MAX_STEPS
from safety.gate import build_prompt, confirm_with_user, needs_confirmation
from safety.killswitch import is_aborted
from safety.log import log_action
from schema import Action, Observation, StepRecord
from vision.marks import observe
from voice.tts import speak

Status = Literal["running", "done", "failed", "aborted"]


class GraphState(TypedDict, total=False):
    """Typed state passed through the LangGraph agent loop."""

    goal: str
    history: list[StepRecord]
    observation: Observation | None
    action: Action | None
    step_count: int
    retry_count: int
    status: Status
    stage_latency_ms: dict[str, int]


def _check_aborted(state: GraphState) -> bool:
    """Set aborted status when the application kill switch is active."""
    if is_aborted():
        state["status"] = "aborted"
        speak("Stopped.")
        return True
    return False


def observe_node(state: GraphState) -> GraphState:
    """Capture and annotate the current screen."""
    if _check_aborted(state):
        return state

    started = time.perf_counter()
    observation = observe()
    state["observation"] = observation
    state.setdefault("stage_latency_ms", {})["observe"] = round(
        (time.perf_counter() - started) * 1000
    )
    return state


def plan_node(state: GraphState) -> GraphState:
    """Choose the next action from the current observation."""
    if _check_aborted(state):
        return state

    observation = state.get("observation")
    if observation is None:
        state["status"] = "failed"
        return state

    started = time.perf_counter()
    action = plan(state["goal"], observation, state.get("history", []))
    state["action"] = action
    state.setdefault("stage_latency_ms", {})["plan"] = round(
        (time.perf_counter() - started) * 1000
    )
    return state


def act_node(state: GraphState) -> GraphState:
    """Execute the planned action and advance the step count."""
    if _check_aborted(state):
        return state

    observation = state.get("observation")
    action = state.get("action")
    if observation is None or action is None:
        state["status"] = "failed"
        return state

    started = time.perf_counter()
    success = False
    try:
        success = execute(action, observation)
    except AbortedError:
        state["status"] = "aborted"
        speak("Stopped.")
        return state

    state["step_count"] = state.get("step_count", 0) + 1
    if state["step_count"] >= MAX_STEPS:
        state["status"] = "failed"

    state.setdefault("stage_latency_ms", {})["act"] = round(
        (time.perf_counter() - started) * 1000
    )

    _progress_message(action)

    record = StepRecord(
        step=state["step_count"],
        action=action,
        success=success,
        latency_ms=dict(state.get("stage_latency_ms", {})),
    )
    state.setdefault("history", []).append(record)
    log_action(record.step, record.action, record.success, record.latency_ms)
    return state


def _progress_message(action: Action) -> None:
    """Speak a short, human-readable progress message."""
    labels = {
        "click": "Clicked the target",
        "type": "Typed the requested text",
        "scroll": "Scrolled the screen",
        "press": "Pressed the requested key",
        "wait": "Waiting",
        "done": "Goal complete",
        "ask_user": "I need your help",
    }
    speak(labels.get(action.action, "Action performed"))


def verify_node(state: GraphState) -> GraphState:
    """Re-capture, verify visual change, and update loop status."""
    if _check_aborted(state):
        return state

    action = state.get("action")
    before = state.get("observation")
    if action is None:
        state["status"] = "failed"
        return state

    if action.goal_complete:
        state["status"] = "done"
        return state

    started = time.perf_counter()
    after_observation = observe()
    state["observation"] = after_observation
    state.setdefault("stage_latency_ms", {})["verify"] = round(
        (time.perf_counter() - started) * 1000
    )

    changed = False
    if before is not None:
        try:
            from PIL import Image

            with Image.open(before.image_path).convert("RGB") as before_image:
                with Image.open(after_observation.image_path).convert("RGB") as after_image:
                    changed = screen_changed(before_image, after_image)
        except (OSError, FileNotFoundError):
            changed = True

    if not changed:
        state["retry_count"] = state.get("retry_count", 0) + 1
        if state["retry_count"] >= 2:
            state["status"] = "failed"
            speak("I'm stuck.")
    else:
        state["retry_count"] = 0

    return state


def safety_gate_node(state: GraphState) -> GraphState:
    """Ask for confirmation before executing sensitive actions."""
    if _check_aborted(state):
        return state

    action = state.get("action")
    if action is None:
        state["status"] = "failed"
        return state

    if needs_confirmation(action):
        prompt = build_prompt(action)
        if not confirm_with_user(prompt):
            speak("Cancelled")
            state["status"] = "failed"
            log_action(
                state.get("step_count", 0) + 1,
                action,
                False,
                dict(state.get("stage_latency_ms", {})),
            )
    return state


def _route_after_verify(state: GraphState) -> Literal["observe", "plan", "done"]:
    """Route back to planning or stop for a terminal state."""
    if state.get("status") == "aborted":
        return "done"

    if state["step_count"] >= MAX_STEPS:
        state["status"] = "failed"
        return "done"

    recent = state.get("history", [])[-3:]
    if len(recent) == 3:
        signatures = [
            (record.action.action, record.action.target_id, record.action.text)
            for record in recent
        ]
        if len(set(signatures)) == 1:
            state["status"] = "failed"
            speak("I'm stuck.")
            return "done"

    if state.get("status") in {"done", "failed"}:
        return "done"

    if state.get("retry_count", 0) > 0:
        return "plan"

    return "observe"


def create_agent_graph():
    """Build and compile the agent state graph."""
    builder = StateGraph(GraphState)
    builder.add_node("observe", observe_node)
    builder.add_node("plan", plan_node)
    builder.add_node("safety_gate", safety_gate_node)
    builder.add_node("act", act_node)
    builder.add_node("verify", verify_node)

    builder.set_entry_point("observe")
    builder.add_edge("observe", "plan")
    builder.add_edge("plan", "safety_gate")
    builder.add_conditional_edges(
        "safety_gate",
        lambda state: "done" if state.get("status") in {"failed", "aborted"} else "act",
        {"act": "act", "done": END},
    )
    builder.add_edge("act", "verify")
    builder.add_conditional_edges(
        "verify",
        _route_after_verify,
        {"observe": "observe", "plan": "plan", "done": END},
    )

    return builder.compile()


agent_graph = create_agent_graph()
