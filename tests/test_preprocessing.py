"""Tests for src.vision.preprocessing — ImagePreprocessor."""
from __future__ import annotations

import numpy as np
import pytest

from src.vision.preprocessing import ImagePreprocessor


@pytest.fixture
def preprocessor() -> ImagePreprocessor:
    return ImagePreprocessor()


@pytest.fixture
def color_image() -> np.ndarray:
    """100×100 BGR image with some non‑zero content."""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[20:80, 20:80] = [200, 150, 100]  # a coloured rectangle
    return img


@pytest.fixture
def large_image() -> np.ndarray:
    """2000×1500 BGR image (larger than max_dimension)."""
    return np.zeros((1500, 2000, 3), dtype=np.uint8)


@pytest.fixture
def small_image() -> np.ndarray:
    """500×400 BGR image (smaller than max_dimension)."""
    return np.zeros((400, 500, 3), dtype=np.uint8)


class TestImagePreprocessor:
    """Suite for ImagePreprocessor methods."""

    def test_initialization(self, preprocessor: ImagePreprocessor) -> None:
        assert preprocessor is not None

    # ── resize ──────────────────────────────────────────────────────────

    def test_resize_large_image(self, preprocessor: ImagePreprocessor, large_image: np.ndarray) -> None:
        resized = preprocessor.resize_image(large_image, max_dim=1024)
        h, w = resized.shape[:2]
        assert max(h, w) <= 1024
        # Aspect ratio preserved
        assert abs(w / h - 2000 / 1500) < 0.02

    def test_resize_small_image_unchanged(self, preprocessor: ImagePreprocessor, small_image: np.ndarray) -> None:
        resized = preprocessor.resize_image(small_image, max_dim=1024)
        assert resized.shape == small_image.shape

    # ── grayscale ───────────────────────────────────────────────────────

    def test_to_grayscale_from_bgr(self, preprocessor: ImagePreprocessor, color_image: np.ndarray) -> None:
        gray = preprocessor.to_grayscale(color_image)
        assert len(gray.shape) == 2
        assert gray.shape[:2] == color_image.shape[:2]

    def test_to_grayscale_already_gray(self, preprocessor: ImagePreprocessor) -> None:
        gray_input = np.zeros((100, 100), dtype=np.uint8)
        result = preprocessor.to_grayscale(gray_input)
        assert result.shape == gray_input.shape

    # ── denoise ─────────────────────────────────────────────────────────

    def test_denoise_preserves_shape(self, preprocessor: ImagePreprocessor, color_image: np.ndarray) -> None:
        denoised = preprocessor.denoise(color_image)
        assert denoised.shape == color_image.shape

    def test_denoise_grayscale(self, preprocessor: ImagePreprocessor) -> None:
        gray = np.random.randint(0, 255, (80, 80), dtype=np.uint8)
        denoised = preprocessor.denoise(gray)
        assert denoised.shape == gray.shape

    # ── adaptive_threshold ──────────────────────────────────────────────

    def test_adaptive_threshold(self, preprocessor: ImagePreprocessor) -> None:
        gray = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        thresh = preprocessor.adaptive_threshold(gray)
        assert thresh.shape == gray.shape
        # Output should be binary (0 or 255)
        unique = np.unique(thresh)
        assert all(v in (0, 255) for v in unique)

    # ── full pipeline ───────────────────────────────────────────────────

    def test_preprocess_pipeline_keys(self, preprocessor: ImagePreprocessor, color_image: np.ndarray) -> None:
        result = preprocessor.preprocess(color_image)
        assert isinstance(result, dict)
        assert "original" in result
        assert "processed" in result
        assert "grayscale" in result
        assert "steps" in result
        assert isinstance(result["steps"], list)
        assert len(result["steps"]) >= 3  # at least resize, denoise, grayscale

    def test_preprocess_pipeline_with_large_image(self, preprocessor: ImagePreprocessor, large_image: np.ndarray) -> None:
        result = preprocessor.preprocess(large_image)
        # Processed output should be smaller than original
        proc = result["processed"]
        assert max(proc.shape[:2]) <= 1024

    def test_preprocess_handles_none(self, preprocessor: ImagePreprocessor) -> None:
        result = preprocessor.preprocess(None)
        assert isinstance(result, dict)
        assert "steps" in result
