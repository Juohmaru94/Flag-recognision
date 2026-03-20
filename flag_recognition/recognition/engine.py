from __future__ import annotations

import abc
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np
from PIL import Image

CANVAS_SIZE = (192, 128)
VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
QUERY_TRIM_FRACTIONS = (0.0, 0.03, 0.05, 0.08, 0.12)
GLOBAL_HIST_BINS = (12, 8, 8)
SPATIAL_GRID = (3, 2)
SPATIAL_HIST_BINS = (6, 4, 4)
COLOR_THUMBNAIL_SIZE = (64, 40)
EDGE_THUMBNAIL_SIZE = (64, 40)
DESCRIPTOR_WEIGHTS = {
    "global_hist": 0.15,
    "spatial_hist": 0.30,
    "color_thumbnail": 0.30,
    "edge_thumbnail": 0.25,
}


@dataclass(slots=True)
class MatchResult:
    country: str
    confidence: float
    top_k: list[tuple[str, float]]


@dataclass(slots=True)
class DescriptorParts:
    global_hist: np.ndarray
    spatial_hist: np.ndarray
    color_thumbnail: np.ndarray
    edge_thumbnail: np.ndarray


class RecognizerBackend(abc.ABC):
    @abc.abstractmethod
    def recognize(self, image: Image.Image, top_k: int = 3) -> MatchResult:
        raise NotImplementedError


class FlagRecognizer(RecognizerBackend):
    def __init__(self, dataset_dir: str | Path) -> None:
        self.dataset_dir = Path(dataset_dir)
        self._entries: list[tuple[str, DescriptorParts]] = []
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

    def _normalize_vector(self, vector: np.ndarray) -> np.ndarray:
        flattened = vector.astype(np.float32).flatten()
        norm = np.linalg.norm(flattened)
        return flattened if norm == 0 else flattened / norm

    def _build_descriptor(self, image: Image.Image) -> DescriptorParts:
        array = self._preprocess(image)
        hsv = cv2.cvtColor(array, cv2.COLOR_RGB2HSV)
        global_hist = cv2.calcHist([hsv], [0, 1, 2], None, GLOBAL_HIST_BINS, [0, 180, 0, 256, 0, 256])

        cell_descriptors = []
        grid_x, grid_y = SPATIAL_GRID
        height, width = array.shape[:2]
        for y_index in range(grid_y):
            for x_index in range(grid_x):
                y0 = y_index * height // grid_y
                y1 = (y_index + 1) * height // grid_y
                x0 = x_index * width // grid_x
                x1 = (x_index + 1) * width // grid_x
                cell = hsv[y0:y1, x0:x1]
                cell_hist = cv2.calcHist([cell], [0, 1, 2], None, SPATIAL_HIST_BINS, [0, 180, 0, 256, 0, 256])
                cell_descriptors.append(self._normalize_vector(cell_hist))

        color_thumbnail = cv2.resize(array, COLOR_THUMBNAIL_SIZE, interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        gray = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, threshold1=50, threshold2=150)
        edge_thumbnail = cv2.resize(edges, EDGE_THUMBNAIL_SIZE, interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0

        return DescriptorParts(
            global_hist=self._normalize_vector(global_hist),
            spatial_hist=self._normalize_vector(np.concatenate(cell_descriptors)),
            color_thumbnail=self._normalize_vector(color_thumbnail),
            edge_thumbnail=self._normalize_vector(edge_thumbnail),
        )

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

    def _iter_query_variants(self, image: Image.Image) -> Iterable[Image.Image]:
        width, height = image.size
        for trim_fraction in QUERY_TRIM_FRACTIONS:
            if trim_fraction == 0.0:
                yield image
                continue

            dx = int(width * trim_fraction)
            dy = int(height * trim_fraction)
            if dx * 2 >= width or dy * 2 >= height:
                continue

            yield image.crop((dx, dy, width - dx, height - dy))

    def _score_descriptor(self, descriptor: DescriptorParts) -> list[tuple[str, float]]:
        scored = []
        for country, reference in self._entries:
            similarity = (
                DESCRIPTOR_WEIGHTS["global_hist"] * float(np.dot(descriptor.global_hist, reference.global_hist))
                + DESCRIPTOR_WEIGHTS["spatial_hist"] * float(np.dot(descriptor.spatial_hist, reference.spatial_hist))
                + DESCRIPTOR_WEIGHTS["color_thumbnail"] * float(np.dot(descriptor.color_thumbnail, reference.color_thumbnail))
                + DESCRIPTOR_WEIGHTS["edge_thumbnail"] * float(np.dot(descriptor.edge_thumbnail, reference.edge_thumbnail))
            )
            confidence = max(0.0, min(1.0, similarity))
            scored.append((country, confidence))
        return scored

    def recognize(self, image: Image.Image, top_k: int = 3) -> MatchResult:
        best_by_country: dict[str, float] = {}

        for variant in self._iter_query_variants(image):
            descriptor = self._build_descriptor(variant)
            for country, confidence in self._score_descriptor(descriptor):
                previous = best_by_country.get(country)
                if previous is None or confidence > previous:
                    best_by_country[country] = confidence

        scored = sorted(best_by_country.items(), key=lambda item: item[1], reverse=True)
        best_country, best_confidence = scored[0]
        return MatchResult(country=best_country, confidence=best_confidence, top_k=scored[:top_k])
