from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import time

import mss
import numpy as np
from PIL import Image

from flag_recognition.config import FixedRegion


@dataclass(slots=True)
class CaptureResult:
    image: Image.Image
    region: FixedRegion


class ScreenCapturer:
    def __init__(self, debug: bool = False, debug_dir: str = "debug_captures") -> None:
        self.debug = debug
        self.debug_dir = Path(debug_dir)
        if self.debug:
            self.debug_dir.mkdir(parents=True, exist_ok=True)

    def capture_region(self, region: FixedRegion) -> CaptureResult:
        if not region.is_valid():
            raise ValueError("Selected region is empty or too small.")

        monitor = {
            "left": region.left,
            "top": region.top,
            "width": region.width,
            "height": region.height,
        }
        with mss.mss() as sct:
            raw = sct.grab(monitor)
        frame = np.array(raw)[:, :, :3]
        image = Image.fromarray(frame[:, :, ::-1])

        if self.debug:
            filename = self.debug_dir / f"capture_{int(time() * 1000)}.png"
            image.save(filename)

        return CaptureResult(image=image, region=region)
