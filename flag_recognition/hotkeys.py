from __future__ import annotations

import keyboard


class HotkeyRegistrationError(RuntimeError):
    pass


class GlobalHotkeyManager:
    def __init__(self) -> None:
        self._handles: list[str] = []

    def register(self, hotkey: str, callback) -> None:
        try:
            handle = keyboard.add_hotkey(hotkey, callback, suppress=False, trigger_on_release=False)
        except Exception as exc:  # noqa: BLE001
            raise HotkeyRegistrationError(
                f"Failed to register hotkey '{hotkey}'. Try running with administrator rights or choose another hotkey."
            ) from exc
        self._handles.append(handle)

    def wait(self) -> None:
        keyboard.wait()

    def cleanup(self) -> None:
        for handle in self._handles:
            keyboard.remove_hotkey(handle)
        self._handles.clear()
