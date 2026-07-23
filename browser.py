"""Playwright wrapper for https://2048game.online/."""
from __future__ import annotations

import json
import time

from playwright.sync_api import sync_playwright

from board import from_grid

URL = "https://2048game.online/"
STATE_KEY = "phaser2048_game_state"
ARROWS = ("ArrowUp", "ArrowRight", "ArrowDown", "ArrowLeft")


class Game:
    def __init__(self, headless: bool = False) -> None:
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=headless)
        self._page = self._browser.new_page()
        self._page.goto(URL)
        self._page.wait_for_load_state("load")
        self._page.locator("canvas").first.click()

    def read(self) -> dict | None:
        try:
            raw = self._page.evaluate(
                f"() => localStorage.getItem({STATE_KEY!r})"
            )
            if raw is None:
                return None
            parsed = json.loads(raw)
            return {
                "board": from_grid(parsed["grid"]),
                "score": int(parsed["score"]),
                "won": bool(parsed["won"]),
                "keepPlaying": bool(parsed["keepPlaying"]),
            }
        except Exception:
            return None

    def send(self, direction: int) -> None:
        self._page.keyboard.press(ARROWS[direction])

    def wait_for_change(self, prev_board: int, timeout_ms: int = 1500) -> bool:
        deadline = time.perf_counter() + timeout_ms / 1000.0
        while time.perf_counter() < deadline:
            state = self.read()
            if state is not None and state["board"] != prev_board:
                return True
            time.sleep(0.05)
        return False

    def dismiss_win(self) -> None:
        try:
            raw = self._page.evaluate(
                f"() => localStorage.getItem({STATE_KEY!r})"
            )
            if raw is None:
                raise RuntimeError("missing state key")
            parsed = json.loads(raw)
            parsed["keepPlaying"] = True
            self._page.evaluate(
                """([key, value]) => localStorage.setItem(key, value)""",
                [STATE_KEY, json.dumps(parsed)],
            )
            state = self.read()
            if state is not None and state["keepPlaying"]:
                return
        except Exception:
            pass
        self._page.locator("canvas").first.screenshot(path="win_overlay.png")
        print(
            "WIN OVERLAY: keepPlaying did not stick after localStorage write. "
            "Screenshot saved to win_overlay.png — manual handling needed."
        )

    def reset(self) -> None:
        self._page.evaluate(
            f"() => localStorage.removeItem({STATE_KEY!r})"
        )
        self._page.reload()
        self._page.wait_for_load_state("load")
        self._page.locator("canvas").first.click()

    def close(self) -> None:
        self._browser.close()
        self._pw.stop()
