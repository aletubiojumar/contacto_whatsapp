"""Playwright browser launcher.

Why this exists
--------------
On servers/SSH sessions without an X server (no $DISPLAY), launching a *headed*
Chromium will crash with:
    Missing X server or $DISPLAY
and Playwright raises TargetClosedError.

This helper automatically forces headless mode when $DISPLAY is not set,
while still allowing headed execution on desktops.

It is designed to be used as:
    with launch_browser(config) as (_, page):
        ...
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator, Tuple, Any

from playwright.sync_api import sync_playwright, Browser, Page  # type: ignore


def _should_run_headless(config: Any) -> bool:
    """Determine whether Playwright must run headless."""
    cfg_headless = bool(getattr(config, "headless", False))
    # If there's no display, we *must* be headless regardless of config.
    no_display = not os.environ.get("DISPLAY")
    return cfg_headless or no_display


@contextmanager
def launch_browser(config: Any) -> Generator[Tuple[Browser, Page], None, None]:
    """Launch Chromium and yield (browser, page).

    - Forces headless=True when $DISPLAY is missing.
    - Adds --no-sandbox (common requirement in containers).

    The caller is expected to destructure as: (_, page).
    """

    headless = _should_run_headless(config)
    slow_mo = getattr(config, "slow_mo", None)

    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(
            headless=headless,
            slow_mo=slow_mo,
            args=["--no-sandbox"],
        )
        context = browser.new_context()
        page = context.new_page()

        try:
            yield (browser, page)
        finally:
            # Close in reverse order; ignore errors on shutdown.
            try:
                context.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass
