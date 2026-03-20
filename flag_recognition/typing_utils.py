from __future__ import annotations

import logging
import time

import pyautogui

logger = logging.getLogger(__name__)
pyautogui.FAILSAFE = False


class Typer:
    def __init__(self, delay_ms: int = 200, press_enter: bool = False) -> None:
        self.delay_ms = delay_ms
        self.press_enter = press_enter

    def type_text(self, text: str) -> None:
        try:
            time.sleep(self.delay_ms / 1000.0)
            pyautogui.write(text, interval=0.01)
            if self.press_enter:
                pyautogui.press("enter")
        except Exception:  # noqa: BLE001
            logger.exception("Typing failed")
            raise
