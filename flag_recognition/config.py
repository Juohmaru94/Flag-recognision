from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class FixedRegion:
    left: int = 0
    top: int = 0
    width: int = 0
    height: int = 0

    def is_valid(self) -> bool:
        return self.width > 4 and self.height > 4


@dataclass(slots=True)
class AppConfig:
    hotkey: str = "ctrl+shift+s"
    fixed_region: FixedRegion = field(default_factory=FixedRegion)
    confidence_threshold: float = 0.72
    type_delay_ms: int = 200
    press_enter: bool = False
    debug: bool = False
    loop_interval_ms: int = 800
    min_region_size: int = 12
    dataset_dir: str = "assets/flags"
    debug_dir: str = "debug_captures"

    @classmethod
    def load(cls, path: str | Path) -> "AppConfig":
        config_path = Path(path)
        data: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
        fixed_region = FixedRegion(**data.get("fixed_region", {}))
        payload = {**data, "fixed_region": fixed_region}
        return cls(**payload)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
