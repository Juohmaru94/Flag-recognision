from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass

from flag_recognition.config import FixedRegion


@dataclass(slots=True)
class _DragState:
    start_x: int = 0
    start_y: int = 0
    rect_id: int | None = None


class RegionSelector:
    """Fullscreen translucent selection overlay."""

    def __init__(self, min_region_size: int = 12) -> None:
        self.min_region_size = min_region_size
        self._state = _DragState()
        self._selection: FixedRegion | None = None

    def select_region(self) -> FixedRegion | None:
        root = tk.Tk()
        root.withdraw()

        overlay = tk.Toplevel(root)
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-topmost", True)
        overlay.attributes("-alpha", 0.25)
        overlay.configure(background="black")
        overlay.title("Select flag region")
        overlay.focus_force()

        canvas = tk.Canvas(overlay, cursor="cross", bg="gray10", highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        def on_press(event: tk.Event) -> None:
            self._state.start_x = event.x
            self._state.start_y = event.y
            if self._state.rect_id is not None:
                canvas.delete(self._state.rect_id)
            self._state.rect_id = canvas.create_rectangle(
                event.x, event.y, event.x, event.y, outline="red", width=2
            )

        def on_drag(event: tk.Event) -> None:
            if self._state.rect_id is None:
                return
            canvas.coords(
                self._state.rect_id,
                self._state.start_x,
                self._state.start_y,
                event.x,
                event.y,
            )

        def on_release(event: tk.Event) -> None:
            left = min(self._state.start_x, event.x)
            top = min(self._state.start_y, event.y)
            width = abs(event.x - self._state.start_x)
            height = abs(event.y - self._state.start_y)
            if width < self.min_region_size or height < self.min_region_size:
                self._selection = None
            else:
                self._selection = FixedRegion(left=left, top=top, width=width, height=height)
            overlay.destroy()
            root.quit()

        def on_escape(_: tk.Event) -> None:
            self._selection = None
            overlay.destroy()
            root.quit()

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        overlay.bind("<Escape>", on_escape)

        root.mainloop()
        root.destroy()
        return self._selection
