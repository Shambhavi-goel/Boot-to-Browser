"""Application configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL: str | None = os.getenv("GEMINI_MODEL")
MAX_STEPS: int = 20
SCREEN_MAX_WIDTH: int = 1280
LOG_DIR: str = "logs"
