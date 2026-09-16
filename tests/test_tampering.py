"""Tests for TamperingAnalyzer (Phase 4).

All tests use synthetic images — no real identity documents.
No internet, GPU, or external APIs required.
"""
from __future__ import annotations

import numpy as np
import pytest
import cv2

from src.vision.tampering import TamperingAnalyzer


# ── Helpers ──────────────────────────────────────────────────────────────────

def _synthetic_document(width: int = 400, height: int = 300) -> np.ndarray:
    """Create a synthetic document-like BGR image with text regions."""
    img = np.full((height, width, 3), 240, dtype=np.uint8)  # light background
    # Simulate text lines
    for y in range(50, height - 30, 30):
        cv2.putText(img, "Sample Text Line 12345", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (30, 30, 30), 1)
    # Add a border
    cv2.rectangle(img, (5, 5), (width - 5, height - 5), (0, 0, 0), 2)
    return img


def _modified_document(
    base: np.ndarray,
    region: tuple[int, int, int, int] = (100, 80, 200, 130),
) -> np.ndarray:
    """Create a copy with a region filled with a distinct color."""
    modified = base.copy()
    x1, y1, x2, y2 = region
    modified[y1:y2, x1:x2] = (0, 0, 255)  # bright red patch
    return modified


# ═══════════════════════════════════════════════════════════════════════════════
# Basic initialization
# ═══════════════════════════════════════════════════════════════════════════════


class TestTamperingInit:
    def test_init(self) -> None:
        analyzer = TamperingAnalyzer()
        assert analyzer is not None

    def test_has_config(self) -> None:
        analyzer = TamperingAnalyzer()
        assert isinstance(analyzer.config, dict)
        assert "ela_jpeg_quality" in analyzer.config


# ═══════════════════════════════════════════════════════════════════════════════
# Input handling
# ═══════════════════════════════════════════════════════════════════════════════


class TestTamperingInputHandling:
    def test_none_image(self) -> None:
        analyzer = TamperingAnalyzer()
        result = analyzer.analyze(None)
        assert result["status"] == "error"
        assert result["checks"] == []
        assert result["ela_image"] is None
        assert result["overall_suspicious"] is False

    def test_empty_image(self) -> None:
        analyzer = TamperingAnalyzer()
        result = analyzer.analyze(np.array([], dtype=np.uint8))
        assert result["status"] == "error"

    def test_too_small_image(self) -> None:
        analyzer = TamperingAnalyzer()
        tiny = np.zeros((5, 5, 3), dtype=np.uint8)
        result = analyzer.analyze(tiny)
        assert result["status"] == "error"
        assert "too small" in result["message"].lower()

    def test_invalid_type(self) -> None:
        analyzer = TamperingAnalyzer()
        result = analyzer.analyze("not_an_image")
        assert result["status"] == "error"


# ═══════════════════════════════════════════════════════════════════════════════
# Valid image analysis
# ═══════════════════════════════════════════════════════════════════════════════


class TestTamperingValidImage:
    def test_color_image_success(self) -> None:
        analyzer = TamperingAnalyzer()
        img = _synthetic_document()
        result = analyzer.analyze(img)
        assert result["status"] == "success"
        assert len(result["checks"]) == 3
        assert result["ela_image"] is not None
        assert isinstance(result["suspicion_score"], float)
        assert 0.0 <= result["suspicion_score"] <= 1.0

    def test_grayscale_image(self) -> None:
        analyzer = TamperingAnalyzer()
        gray = np.full((100, 100), 128, dtype=np.uint8)
        result = analyzer.analyze(gray)
        assert result["status"] == "success"
        assert len(result["checks"]) == 3

    def test_large_image(self) -> None:
        analyzer = TamperingAnalyzer()
        large = np.full((1000, 800, 3), 200, dtype=np.uint8)
        result = analyzer.analyze(large)
        assert result["status"] == "success"

    def test_bgra_image(self) -> None:
        """Image with alpha channel should be handled."""
        analyzer = TamperingAnalyzer()
        bgra = np.full((100, 100, 4), 180, dtype=np.uint8)
        result = analyzer.analyze(bgra)
        assert result["status"] == "success"


# ═══════════════════════════════════════════════════════════════════════════════
# Return schema
# ═══════════════════════════════════════════════════════════════════════════════


class TestTamperingSchema:
    def test_top_level_keys(self) -> None:
        analyzer = TamperingAnalyzer()
        result = analyzer.analyze(_synthetic_document())
        assert "checks" in result
        assert "ela_image" in result
        assert "overall_suspicious" in result
        assert "suspicion_score" in result
        assert "status" in result
        assert "method" in result
        assert "message" in result

    def test_check_item_keys(self) -> None:
        analyzer = TamperingAnalyzer()
        result = analyzer.analyze(_synthetic_document())
        for chk in result["checks"]:
            assert "name" in chk
            assert "description" in chk
            assert "result" in chk
            assert "suspicious" in chk
            assert "details" in chk
            assert isinstance(chk["suspicious"], bool)

    def test_method_is_heuristic(self) -> None:
        analyzer = TamperingAnalyzer()
        result = analyzer.analyze(_synthetic_document())
        assert result["method"] == "heuristic_cv"

    def test_error_schema_matches(self) -> None:
        """Error results must have the same top-level keys."""
        analyzer = TamperingAnalyzer()
        result = analyzer.analyze(None)
        assert "checks" in result
        assert "ela_image" in result
        assert "overall_suspicious" in result
        assert "suspicion_score" in result
        assert "status" in result


# ═══════════════════════════════════════════════════════════════════════════════
# ELA
# ═══════════════════════════════════════════════════════════════════════════════


class TestELA:
    def test_ela_image_shape(self) -> None:
        analyzer = TamperingAnalyzer()
        img = _synthetic_document(400, 300)
        result = analyzer.analyze(img)
        ela = result["ela_image"]
        assert ela is not None
        assert ela.shape[:2] == (300, 400)

    def test_ela_image_dtype(self) -> None:
        analyzer = TamperingAnalyzer()
        result = analyzer.analyze(_synthetic_document())
        assert result["ela_image"].dtype == np.uint8

    def test_ela_deterministic(self) -> None:
        """Same image should produce same ELA metrics."""
        analyzer = TamperingAnalyzer()
        img = _synthetic_document()
        r1 = analyzer.analyze(img)
        r2 = analyzer.analyze(img)
        m1 = r1["checks"][0].get("metrics", {})
        m2 = r2["checks"][0].get("metrics", {})
        assert m1.get("ela_mean") == m2.get("ela_mean")

    def test_ela_check_has_metrics(self) -> None:
        analyzer = TamperingAnalyzer()
        result = analyzer.analyze(_synthetic_document())
        ela_check = result["checks"][0]
        assert "metrics" in ela_check
        assert "ela_mean" in ela_check["metrics"]
        assert "ela_max" in ela_check["metrics"]
        assert "ela_std" in ela_check["metrics"]


# ═══════════════════════════════════════════════════════════════════════════════
# Edge density
# ═══════════════════════════════════════════════════════════════════════════════


class TestEdgeDensity:
    def test_edge_check_present(self) -> None:
        analyzer = TamperingAnalyzer()
        result = analyzer.analyze(_synthetic_document())
        names = [c["name"] for c in result["checks"]]
        assert "Edge Density" in names

    def test_blank_image_low_density(self) -> None:
        """A perfectly blank image should have very low edge density."""
        analyzer = TamperingAnalyzer()
        blank = np.full((200, 200, 3), 128, dtype=np.uint8)
        result = analyzer.analyze(blank)
        edge_check = [c for c in result["checks"] if c["name"] == "Edge Density"][0]
        density = edge_check.get("metrics", {}).get("edge_density", 1.0)
        assert density < 0.01

    def test_edge_has_metrics(self) -> None:
        analyzer = TamperingAnalyzer()
        result = analyzer.analyze(_synthetic_document())
        edge_check = [c for c in result["checks"] if c["name"] == "Edge Density"][0]
        assert "metrics" in edge_check
        assert "edge_density" in edge_check["metrics"]


# ═══════════════════════════════════════════════════════════════════════════════
# Noise analysis
# ═══════════════════════════════════════════════════════════════════════════════


class TestNoiseAnalysis:
    def test_noise_check_present(self) -> None:
        analyzer = TamperingAnalyzer()
        result = analyzer.analyze(_synthetic_document())
        names = [c["name"] for c in result["checks"]]
        assert "Noise Analysis" in names

    def test_clean_image_low_noise(self) -> None:
        """A smooth synthetic image should have low noise."""
        analyzer = TamperingAnalyzer()
        smooth = np.full((200, 200, 3), 128, dtype=np.uint8)
        result = analyzer.analyze(smooth)
        noise_check = [c for c in result["checks"] if c["name"] == "Noise Analysis"][0]
        noise_std = noise_check.get("metrics", {}).get("noise_std", 999)
        assert noise_std < 5.0

    def test_noisy_image_detected(self) -> None:
        """An image with heavy added noise should trigger the noise check."""
        analyzer = TamperingAnalyzer()
        noisy = np.full((200, 200, 3), 128, dtype=np.uint8)
        rng = np.random.RandomState(42)
        noise = rng.randint(-120, 120, noisy.shape, dtype=np.int16)
        noisy = np.clip(noisy.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        result = analyzer.analyze(noisy)
        noise_check = [c for c in result["checks"] if c["name"] == "Noise Analysis"][0]
        assert noise_check["suspicious"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# Synthetic modification comparison
# ═══════════════════════════════════════════════════════════════════════════════


class TestSyntheticModification:
    def test_modified_produces_different_ela(self) -> None:
        """A programmatically modified image should produce different
        ELA metrics compared to the unmodified original."""
        analyzer = TamperingAnalyzer()
        original = _synthetic_document()
        modified = _modified_document(original)
        r_orig = analyzer.analyze(original)
        r_mod = analyzer.analyze(modified)
        m_orig = r_orig["checks"][0].get("metrics", {}).get("ela_mean", 0)
        m_mod = r_mod["checks"][0].get("metrics", {}).get("ela_mean", 0)
        # The modified image should have a different (typically higher) ELA mean
        assert m_orig != m_mod

    def test_both_produce_valid_results(self) -> None:
        analyzer = TamperingAnalyzer()
        original = _synthetic_document()
        modified = _modified_document(original)
        for img in (original, modified):
            r = analyzer.analyze(img)
            assert r["status"] == "success"
            assert len(r["checks"]) == 3


# ═══════════════════════════════════════════════════════════════════════════════
# Score calculation
# ═══════════════════════════════════════════════════════════════════════════════


class TestScoreCalculation:
    def test_score_range(self) -> None:
        analyzer = TamperingAnalyzer()
        result = analyzer.analyze(_synthetic_document())
        assert 0.0 <= result["suspicion_score"] <= 1.0

    def test_no_checks_score_zero(self) -> None:
        """Internal: empty checks list should produce 0.0 score."""
        assert TamperingAnalyzer._calculate_score([]) == 0.0

    def test_all_suspicious_score_one(self) -> None:
        checks = [
            {"suspicious": True},
            {"suspicious": True},
            {"suspicious": True},
        ]
        assert TamperingAnalyzer._calculate_score(checks) == 1.0

    def test_no_suspicious_score_zero(self) -> None:
        checks = [
            {"suspicious": False},
            {"suspicious": False},
        ]
        assert TamperingAnalyzer._calculate_score(checks) == 0.0

    def test_partial_suspicious(self) -> None:
        checks = [
            {"suspicious": True},
            {"suspicious": False},
            {"suspicious": False},
        ]
        score = TamperingAnalyzer._calculate_score(checks)
        assert abs(score - 1 / 3) < 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# Language / honesty checks
# ═══════════════════════════════════════════════════════════════════════════════


class TestHonestyLanguage:
    def test_message_no_definitive_claim(self) -> None:
        """The message should never claim definitive fraud detection."""
        analyzer = TamperingAnalyzer()
        for img in [_synthetic_document(), np.full((100, 100, 3), 0, dtype=np.uint8)]:
            result = analyzer.analyze(img)
            msg = result.get("message", "").lower()
            assert "fake" not in msg
            assert "fraud" not in msg
            assert "forged" not in msg
            assert "definitely" not in msg

    def test_not_suspicious_message_disclaims_guarantee(self) -> None:
        analyzer = TamperingAnalyzer()
        img = _synthetic_document()
        result = analyzer.analyze(img)
        if not result["overall_suspicious"]:
            assert "does not guarantee" in result["message"].lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 7: Hardening tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestHardening:
    """Additional hardening tests for stability and edge cases."""

    def test_recompressed_image(self) -> None:
        """Recompressing a normal document image via JPEG should not crash
        and should produce valid results."""
        analyzer = TamperingAnalyzer()
        original = _synthetic_document()
        # Simulate JPEG recompression cycle
        _, buf = cv2.imencode(".jpg", original, [cv2.IMWRITE_JPEG_QUALITY, 50])
        recompressed = cv2.imdecode(np.frombuffer(buf, np.uint8), cv2.IMREAD_COLOR)
        result = analyzer.analyze(recompressed)
        assert result["status"] == "success"
        assert len(result["checks"]) == 3
        assert 0.0 <= result["suspicion_score"] <= 1.0

    def test_png_source_image(self) -> None:
        """A PNG image should be analyzable. ELA via JPEG recompression
        still works but the context is different."""
        analyzer = TamperingAnalyzer()
        # PNG does not have JPEG artifacts — should still produce valid results
        img = _synthetic_document()
        _, buf = cv2.imencode(".png", img)
        png_img = cv2.imdecode(np.frombuffer(buf, np.uint8), cv2.IMREAD_COLOR)
        result = analyzer.analyze(png_img)
        assert result["status"] == "success"
        assert len(result["checks"]) == 3

    def test_low_detail_image(self) -> None:
        """An image with very few features (mostly blank) should not crash."""
        analyzer = TamperingAnalyzer()
        # White image with a single thin line
        img = np.full((200, 200, 3), 255, dtype=np.uint8)
        cv2.line(img, (10, 100), (190, 100), (0, 0, 0), 1)
        result = analyzer.analyze(img)
        assert result["status"] == "success"

    def test_high_detail_image(self) -> None:
        """An image with lots of features should not crash or produce
        unreasonable scores."""
        analyzer = TamperingAnalyzer()
        # Dense text-like image
        img = np.full((400, 600, 3), 230, dtype=np.uint8)
        for y in range(20, 380, 12):
            for x in range(20, 580, 8):
                cv2.putText(img, "X", (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                            0.3, (30, 30, 30), 1)
        result = analyzer.analyze(img)
        assert result["status"] == "success"
        assert 0.0 <= result["suspicion_score"] <= 1.0

    def test_deterministic_behavior(self) -> None:
        """Same input should produce same output."""
        analyzer = TamperingAnalyzer()
        img = _synthetic_document()
        r1 = analyzer.analyze(img)
        r2 = analyzer.analyze(img)
        assert r1["suspicion_score"] == r2["suspicion_score"]
        assert r1["overall_suspicious"] == r2["overall_suspicious"]
        for c1, c2 in zip(r1["checks"], r2["checks"]):
            assert c1["suspicious"] == c2["suspicious"]

    def test_grayscale_input(self) -> None:
        """Grayscale images should be handled without crash."""
        analyzer = TamperingAnalyzer()
        gray = np.full((200, 200), 128, dtype=np.uint8)
        cv2.putText(gray, "Test", (50, 100), cv2.FONT_HERSHEY_SIMPLEX,
                    1.0, 30, 2)
        result = analyzer.analyze(gray)
        assert result["status"] == "success"

    def test_bgra_input(self) -> None:
        """BGRA (4-channel) images should be handled."""
        analyzer = TamperingAnalyzer()
        bgra = np.full((200, 200, 4), 128, dtype=np.uint8)
        bgra[:, :, 3] = 255  # opaque alpha
        result = analyzer.analyze(bgra)
        assert result["status"] == "success"

    def test_minimum_size_boundary(self) -> None:
        """Image at exactly the minimum size should work."""
        analyzer = TamperingAnalyzer()
        min_dim = analyzer.config.get("min_image_dimension", 20)
        img = np.full((min_dim, min_dim, 3), 128, dtype=np.uint8)
        result = analyzer.analyze(img)
        assert result["status"] == "success"

    def test_just_below_minimum_size(self) -> None:
        """Image below minimum size should return error."""
        analyzer = TamperingAnalyzer()
        min_dim = analyzer.config.get("min_image_dimension", 20)
        img = np.full((min_dim - 1, min_dim, 3), 128, dtype=np.uint8)
        result = analyzer.analyze(img)
        assert result["status"] == "error"

    def test_ela_image_returned(self) -> None:
        """ELA visualization should be returned for valid images."""
        analyzer = TamperingAnalyzer()
        result = analyzer.analyze(_synthetic_document())
        assert result["ela_image"] is not None
        assert isinstance(result["ela_image"], np.ndarray)
