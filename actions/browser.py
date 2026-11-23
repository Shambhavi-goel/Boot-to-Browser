"""Persistent headed Chromium session using Playwright."""

from pathlib import Path
from typing import Any


class BrowserSession:
    """Manage a headed persistent Chromium browser context."""

    def __init__(self, profile_dir: str = "browser_profile") -> None:
        """Configure the persistent browser profile location."""
        self.profile_dir = profile_dir
        self._playwright: Any | None = None
        self.context: Any | None = None
        self.page: Any | None = None

    def start(self) -> Any:
        """Start headed persistent Chromium and return the first page."""
        from playwright.sync_api import sync_playwright

        profile_path = Path(self.profile_dir)
        profile_path.mkdir(parents=True, exist_ok=True)

        self._playwright = sync_playwright().start()
        self.context = self._playwright.chromium.launch_persistent_context(
            str(profile_path),
            headless=False,
        )
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        return self.page

    def open(self, url: str) -> Any:
        """Navigate the browser session to a URL."""
        if self.page is None:
            raise RuntimeError("Browser session has not been started")
        self.page.goto(url)
        return self.page

    def close(self) -> None:
        """Close the browser context and Playwright runtime."""
        if self.context is not None:
            self.context.close()
            self.context = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None
        self.page = None
