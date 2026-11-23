"""Gemini-backed action planning for the vision-guided agent loop."""

import json
import logging
import os
import time
from typing import Any

from dotenv import load_dotenv
from PIL import Image
from pydantic import ValidationError

from brain.prompts import SYSTEM_PROMPT, build_user_prompt
from schema import Action, Observation, StepRecord

logger = logging.getLogger("boot_to_browser")
load_dotenv()

_FALLBACK_ACTION = Action(action="ask_user", thought="I could not decide")


def _strip_markdown_fence(text: str) -> str:
    """Strip a surrounding Markdown JSON fence when present."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 2:
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            return "\n".join(lines).strip()
    return stripped


def _is_rate_limit(error: Exception) -> bool:
    """Detect common HTTP 429 and quota/rate-limit exceptions."""
    status_code = getattr(error, "status_code", None)
    code = getattr(error, "code", None)
    message = str(error).lower()
    return status_code == 429 or code == 429 or "429" in message or "rate limit" in message


def _generate_once(model: Any, prompt: str, image: Image.Image) -> str:
    """Call Gemini once with a 20-second timeout."""
    response = model.generate_content(
        [SYSTEM_PROMPT, prompt, image],
        generation_config={"response_mime_type": "application/json"},
        request_options={"timeout": 20},
    )
    return str(response.text)


def _generate(model: Any, prompt: str, image: Image.Image) -> str:
    """Generate content, retrying once when Gemini reports rate limiting."""
    try:
        return _generate_once(model, prompt, image)
    except Exception as error:
        if not _is_rate_limit(error):
            raise
        logger.warning("Gemini rate limit encountered; retrying once")
        time.sleep(1)
        return _generate_once(model, prompt, image)


def plan(goal: str, obs: Observation, history: list[StepRecord]) -> Action:
    """Choose the next action from the goal, annotated screenshot, and history."""
    started = time.perf_counter()
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL")

    if not api_key or not model_name:
        logger.error("Gemini planner configuration is missing")
        return _FALLBACK_ACTION.model_copy(deep=True)

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        prompt = build_user_prompt(goal, obs.elements, history)

        with Image.open(obs.image_path).convert("RGB") as image:
            last_error: Exception | str = "No valid JSON response"
            for attempt in range(2):
                attempt_prompt = prompt
                if attempt == 1:
                    attempt_prompt = f"{prompt}\nPrevious response error: {last_error}"

                try:
                    raw_text = _generate(model, attempt_prompt, image)
                    cleaned = _strip_markdown_fence(raw_text)
                    action = Action.model_validate(json.loads(cleaned))
                    latency_ms = round((time.perf_counter() - started) * 1000)
                    logger.info("brain.plan_latency_ms=%d", latency_ms)
                    return action
                except (json.JSONDecodeError, ValidationError) as error:
                    last_error = error
                    logger.warning(
                        "Gemini response validation failed (attempt %d)", attempt + 1
                    )
                except Exception:
                    logger.exception("Gemini planning request failed")
                    break

        latency_ms = round((time.perf_counter() - started) * 1000)
        logger.info("brain.plan_latency_ms=%d", latency_ms)
        return _FALLBACK_ACTION.model_copy(deep=True)
    except Exception:
        logger.exception("Gemini planner could not initialize")
        latency_ms = round((time.perf_counter() - started) * 1000)
        logger.info("brain.plan_latency_ms=%d", latency_ms)
        return _FALLBACK_ACTION.model_copy(deep=True)
