"""Unit tests for OCREngine wrapper.

All tests mock ``easyocr.Reader`` so they run without downloading
model weights and without internet access.  The test suite validates
the wrapper logic — result transformation, confidence handling,
threshold filtering, and error paths — not EasyOCR itself.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.ocr.engine import OCREngine


# ── fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def dummy_image() -> np.ndarray:
    """Small blank BGR image."""
    return np.zeros((100, 200, 3), dtype=np.uint8)


def _make_engine(mock_reader_cls: MagicMock, readtext_return=None):
    """Helper: build an OCREngine whose EasyOCR Reader is mocked."""
    mock_reader = MagicMock()
    mock_reader.readtext.return_value = readtext_return or []
    mock_reader_cls.return_value = mock_reader
    return OCREngine()


# ── tests ───────────────────────────────────────────────────────────


class TestOCREngineInit:
    """Initialization does NOT trigger model download."""

    def test_default_languages(self) -> None:
        engine = OCREngine()
        assert "en" in engine.languages
        assert engine._initialized is False

    def test_custom_languages(self) -> None:
        engine = OCREngine(languages=["en"])
        assert engine.languages == ["en"]

    def test_no_reader_until_extract(self) -> None:
        engine = OCREngine()
        assert engine._reader is None


class TestOCRExtractText:
    """Result transformation, filtering, and error handling."""

    @patch("easyocr.Reader")
    def test_success_single_region(self, mock_cls, dummy_image) -> None:
        engine = _make_engine(mock_cls, [
            ([[0, 0], [100, 0], [100, 30], [0, 30]], "Hello World", 0.92),
        ])
        result = engine.extract_text(dummy_image)
        assert result["status"] == "success"
        assert result["engine"] == "easyocr"
        assert "Hello World" in result["text"]
        assert result["confidence"] == pytest.approx(0.92, abs=0.01)
        assert len(result["details"]) == 1

    @patch("easyocr.Reader")
    def test_success_multiple_regions(self, mock_cls, dummy_image) -> None:
        engine = _make_engine(mock_cls, [
            ([[0, 0], [50, 0], [50, 20], [0, 20]], "GOVERNMENT", 0.95),
            ([[0, 25], [50, 25], [50, 45], [0, 45]], "OF INDIA", 0.85),
            ([[0, 50], [50, 50], [50, 70], [0, 70]], "Aadhaar", 0.90),
        ])
        result = engine.extract_text(dummy_image)
        assert result["status"] == "success"
        assert len(result["details"]) == 3
        assert "GOVERNMENT" in result["text"]
        assert "Aadhaar" in result["text"]
        assert 0.0 < result["confidence"] <= 1.0

    @patch("easyocr.Reader")
    def test_empty_results(self, mock_cls, dummy_image) -> None:
        engine = _make_engine(mock_cls, [])
        result = engine.extract_text(dummy_image)
        assert result["status"] == "no_text"
        assert result["text"] == ""
        assert result["confidence"] == 0.0
        assert result["details"] == []

    @patch("easyocr.Reader")
    def test_confidence_threshold_filters(self, mock_cls, dummy_image) -> None:
        engine = _make_engine(mock_cls, [
            ([[0, 0], [50, 0], [50, 20], [0, 20]], "noise", 0.10),
            ([[0, 25], [50, 25], [50, 45], [0, 45]], "junk", 0.05),
        ])
        result = engine.extract_text(dummy_image)
        assert result["status"] == "no_text"
        assert result["text"] == ""
        assert len(result["details"]) == 0

    @patch("easyocr.Reader")
    def test_mixed_confidence(self, mock_cls, dummy_image) -> None:
        """Regions below threshold are excluded, above are kept."""
        engine = _make_engine(mock_cls, [
            ([[0, 0], [50, 0], [50, 20], [0, 20]], "GOOD", 0.80),
            ([[0, 25], [50, 25], [50, 45], [0, 45]], "bad", 0.10),
        ])
        result = engine.extract_text(dummy_image)
        assert result["status"] == "success"
        assert len(result["details"]) == 1
        assert result["details"][0]["text"] == "GOOD"

    def test_none_image(self) -> None:
        engine = OCREngine()
        result = engine.extract_text(None)
        assert result["status"] == "error"
        assert result["text"] == ""
        assert "None" in result.get("message", "")

    @patch("easyocr.Reader")
    def test_return_schema_keys(self, mock_cls, dummy_image) -> None:
        engine = _make_engine(mock_cls, [
            ([[0, 0], [50, 0], [50, 20], [0, 20]], "text", 0.9),
        ])
        result = engine.extract_text(dummy_image)
        required_keys = {"text", "confidence", "details", "engine", "status"}
        assert required_keys.issubset(result.keys())

    @patch("easyocr.Reader")
    def test_weighted_average_confidence(self, mock_cls, dummy_image) -> None:
        """Confidence is character-weighted, not simple average."""
        engine = _make_engine(mock_cls, [
            # 4 chars @ 0.9 = 3.6 weight
            ([[0, 0], [50, 0], [50, 20], [0, 20]], "ABCD", 0.9),
            # 1 char @ 0.5 = 0.5 weight    → total 4.1 / 5 = 0.82
            ([[0, 25], [50, 25], [50, 45], [0, 45]], "E", 0.5),
        ])
        result = engine.extract_text(dummy_image)
        assert result["confidence"] == pytest.approx(0.82, abs=0.01)

    @patch("easyocr.Reader")
    def test_reader_exception_returns_error(self, mock_cls, dummy_image) -> None:
        mock_reader = MagicMock()
        mock_reader.readtext.side_effect = ValueError("bad image")
        mock_cls.return_value = mock_reader
        engine = OCREngine()
        result = engine.extract_text(dummy_image)
        assert result["status"] == "error"

    @patch("easyocr.Reader")
    def test_detail_has_bbox(self, mock_cls, dummy_image) -> None:
        bbox = [[0, 0], [100, 0], [100, 30], [0, 30]]
        engine = _make_engine(mock_cls, [(bbox, "Hello", 0.9)])
        result = engine.extract_text(dummy_image)
        assert result["details"][0]["bbox"] == bbox

    @patch("easyocr.Reader")
    def test_text_is_stripped(self, mock_cls, dummy_image) -> None:
        engine = _make_engine(mock_cls, [
            ([[0, 0], [50, 0], [50, 20], [0, 20]], "  padded  ", 0.9),
        ])
        result = engine.extract_text(dummy_image)
        assert result["details"][0]["text"] == "padded"
