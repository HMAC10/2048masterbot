"""Playwright wrapper for https://2048game.online/."""
from __future__ import annotations

import json
import time

from playwright.sync_api import sync_playwright

from board import from_grid, move as board_move

URL = "https://2048game.online/"
STATE_KEY = "phaser2048_game_state"
ARROWS = ("ArrowUp", "ArrowRight", "ArrowDown", "ArrowLeft")


class Game:
    def __init__(self, headless: bool = False) -> None:
        self._headless = headless
        self.dismiss_route: str | None = None
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

    def _board_accepts_move(self) -> bool:
        state = self.read()
        if state is None:
            return False
        board = state["board"]
        for d in range(4):
            new_board, _ = board_move(board, d)
            if new_board == board:
                continue
            self.send(d)
            return self.wait_for_change(board)
        return False

    def dismiss_win(self, manual_ok: bool = True) -> bool:
        """Dismiss the win overlay. True if play can continue."""
        self.dismiss_route = None

        # 1. localStorage route
        try:
            raw = self._page.evaluate(
                f"() => localStorage.getItem({STATE_KEY!r})"
            )
            if raw is not None:
                parsed = json.loads(raw)
                parsed["keepPlaying"] = True
                self._page.evaluate(
                    """([key, value]) => localStorage.setItem(key, value)""",
                    [STATE_KEY, json.dumps(parsed)],
                )
                time.sleep(0.4)
                if self._board_accepts_move():
                    self.dismiss_route = "localStorage"
                    return True
        except Exception:
            pass

        # 2. DOM button route
        try:
            clicked = False
            btn = self._page.locator("a.keep-playing-button")
            if btn.count() > 0 and btn.first.is_visible():
                btn.first.click()
                clicked = True
            else:
                handle = self._page.evaluate_handle(
                    """() => {
                        const re = /keep going|continue|keep playing/i;
                        const nodes = document.querySelectorAll(
                            'a, button, [role="button"]'
                        );
                        for (const el of nodes) {
                            const t = (el.innerText || '').trim();
                            if (!re.test(t)) continue;
                            const r = el.getBoundingClientRect();
                            const st = getComputedStyle(el);
                            if (r.width <= 0 || r.height <= 0) continue;
                            if (st.visibility === 'hidden' || st.display === 'none')
                                continue;
                            return el;
                        }
                        return null;
                    }"""
                )
                el = handle.as_element()
                if el is not None:
                    el.click()
                    clicked = True
            if clicked:
                time.sleep(0.6)
                if self._board_accepts_move():
                    self.dismiss_route = "dom"
                    return True
        except Exception:
            pass

        # 3. Manual route
        if manual_ok and not self._headless:
            print("========================================")
            print('WIN OVERLAY. Click "Keep going" in the browser.')
            print("Waiting up to 120 seconds. Ctrl+C to stop.")
            print("========================================", flush=True)
            deadline = time.perf_counter() + 120.0
            while time.perf_counter() < deadline:
                if self._board_accepts_move():
                    print("Resuming", flush=True)
                    self.dismiss_route = "manual"
                    return True
                time.sleep(0.5)
            self.dismiss_route = "failed"
            return False

        # 4. Headless / no-manual failure
        try:
            self._page.locator("canvas").first.screenshot(path="win_overlay.png")
        except Exception:
            pass
        self.dismiss_route = "failed"
        return False

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
