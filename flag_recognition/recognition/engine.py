from __future__ import annotations

import abc
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

CANVAS_SIZE = (192, 128)
VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


@dataclass(slots=True)
class MatchResult:
    country: str
    confidence: float
    top_k: list[tuple[str, float]]


class RecognizerBackend(abc.ABC):
    @abc.abstractmethod
    def recognize(self, image: Image.Image, top_k: int = 3) -> MatchResult:
        raise NotImplementedError


class FlagRecognizer(RecognizerBackend):
    def __init__(self, dataset_dir: str | Path) -> None:
        self.dataset_dir = Path(dataset_dir)
        self._entries: list[tuple[str, np.ndarray]] = []
        self._load_dataset()

    def _load_dataset(self) -> None:
        if not self.dataset_dir.exists():
            raise FileNotFoundError(
                f"Dataset directory '{self.dataset_dir}' was not found. Add reference flag images before running."
            )

        for path in sorted(self.dataset_dir.iterdir()):
            if path.suffix.lower() not in VALID_EXTENSIONS:
                continue
            image = Image.open(path).convert("RGB")
            descriptor = self._build_descriptor(image)
            country = path.stem.replace("_", " ").replace("-", " ").title()
            self._entries.append((country, descriptor))

        if not self._entries:
            raise FileNotFoundError(
                "No reference flag images were found. Add one image per country inside the dataset directory."
            )

    def _build_descriptor(self, image: Image.Image) -> np.ndarray:
        array = self._preprocess(image)
        hsv = cv2.cvtColor(array, cv2.COLOR_RGB2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [12, 8, 8], [0, 180, 0, 256, 0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        small = cv2.resize(array, (48, 32), interpolation=cv2.INTER_AREA).astype(np.float32).flatten() / 255.0
        descriptor = np.concatenate([hist, small])
        norm = np.linalg.norm(descriptor)
        return descriptor if norm == 0 else descriptor / norm

    def _preprocess(self, image: Image.Image) -> np.ndarray:
        source = np.array(image.convert("RGB"))
        target_w, target_h = CANVAS_SIZE
        src_h, src_w = source.shape[:2]
        scale = min(target_w / src_w, target_h / src_h)
        resized = cv2.resize(source, (max(1, int(src_w * scale)), max(1, int(src_h * scale))), interpolation=cv2.INTER_AREA)
        canvas = np.full((target_h, target_w, 3), 255, dtype=np.uint8)
        y_offset = (target_h - resized.shape[0]) // 2
        x_offset = (target_w - resized.shape[1]) // 2
        canvas[y_offset:y_offset + resized.shape[0], x_offset:x_offset + resized.shape[1]] = resized
        return canvas

    def recognize(self, image: Image.Image, top_k: int = 3) -> MatchResult:
        descriptor = self._build_descriptor(image)
        scored = []
        for country, reference in self._entries:
            similarity = float(np.dot(descriptor, reference))
            confidence = max(0.0, min(1.0, (similarity + 1.0) / 2.0))
            scored.append((country, confidence))

        scored.sort(key=lambda item: item[1], reverse=True)
        best_country, best_confidence = scored[0]
        return MatchResult(country=best_country, confidence=best_confidence, top_k=scored[:top_k])
