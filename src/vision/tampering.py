"""Image tampering and anomaly analysis.

Analyzes uploaded document images for potential visual manipulation
indicators using explainable computer-vision heuristics.

**These are heuristic indicators, NOT definitive proof of tampering.**
A high anomaly score means the image has unusual visual characteristics
that warrant human review.  It does NOT mean the document is fake.

Normal images may trigger indicators due to:
- JPEG compression artifacts
- scanner/camera noise
- low image quality
- image resizing or format conversion

Techniques used:
- Error Level Analysis (ELA)
- Edge density analysis
- High-frequency noise analysis

All thresholds are configurable via ``src.config.TAMPERING``.
"""
from __future__ import annotations

import io
import logging
from typing import Any

import cv2
import numpy as np

from src.config import TAMPERING

logger = logging.getLogger(__name__)


class TamperingAnalyzer:
    """Analyzes images for potential visual manipulation indicators.

    Uses explainable OpenCV-based heuristics — NOT a trained ML model.
    Results are screening indicators for human review.
    """

    def __init__(self) -> None:
        """Initialize with configuration from config.py."""
        self.config = TAMPERING
        logger.info("TamperingAnalyzer initialized")

    def analyze(self, image: np.ndarray) -> dict:
        """Run tampering analysis on an image.

        Args:
            image: Original (non-preprocessed) image as numpy array
                   (BGR or grayscale).

        Returns:
            dict with keys:
                - checks (list[dict]): Analysis results, each with:
                    'name', 'description', 'result' (str),
                    'suspicious' (bool), 'details' (str)
                - ela_image (np.ndarray | None): ELA visualization
                - overall_suspicious (bool): True if heuristic score
                    exceeds threshold
                - suspicion_score (float): Aggregate heuristic score
                    (0.0–1.0).  NOT a probability of fraud.
                - status (str): 'success' or 'error'
                - method (str): Always 'heuristic_cv'
                - message (str): Human-readable summary
        """
        # ── input validation ────────────────────────────────────────
        if image is None:
            return self._error_result("No image provided.")

        if not isinstance(image, np.ndarray):
            return self._error_result("Invalid image format.")

        if image.size == 0:
            return self._error_result("Empty image.")

        min_dim = self.config.get("min_image_dimension", 20)
        h, w = image.shape[:2]
        if h < min_dim or w < min_dim:
            return self._error_result(
                f"Image too small ({w}x{h}). "
                f"Minimum dimension is {min_dim}px."
            )

        # ── ensure BGR for analysis ─────────────────────────────────
        if len(image.shape) == 2:
            bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif image.shape[2] == 4:
            bgr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        else:
            bgr = image.copy()

        checks: list[dict[str, Any]] = []
        ela_image: np.ndarray | None = None

        # ── 1. Error Level Analysis ─────────────────────────────────
        ela_result = self._ela_analysis(bgr)
        checks.append(ela_result["check"])
        ela_image = ela_result.get("ela_image")

        # ── 2. Edge density analysis ────────────────────────────────
        edge_result = self._edge_density_analysis(bgr)
        checks.append(edge_result)

        # ── 3. High-frequency noise analysis ────────────────────────
        noise_result = self._noise_analysis(bgr)
        checks.append(noise_result)

        # ── aggregate score ─────────────────────────────────────────
        score = self._calculate_score(checks)
        threshold = self.config.get("overall_suspicious_threshold", 0.4)
        overall_suspicious = score >= threshold

        if overall_suspicious:
            message = (
                "Potential visual anomalies detected. "
                "This is a heuristic indicator and does not establish "
                "document manipulation. Human review recommended."
            )
        else:
            message = (
                "No significant visual anomalies detected by heuristic "
                "checks. This does not guarantee document authenticity."
            )

        logger.info(
            "Tampering analysis: score=%.3f suspicious=%s checks=%d",
            score, overall_suspicious, len(checks),
        )

        return {
            "checks": checks,
            "ela_image": ela_image,
            "overall_suspicious": overall_suspicious,
            "suspicion_score": round(score, 4),
            "status": "success",
            "method": "heuristic_cv",
            "message": message,
        }

    # ── ELA ──────────────────────────────────────────────────────────

    def _ela_analysis(self, bgr: np.ndarray) -> dict:
        """Perform Error Level Analysis.

        Re-saves the image as JPEG at a known quality, then computes
        the absolute pixel difference between original and recompressed.
        Regions that were edited after initial compression often show
        higher error levels.

        This is a HEURISTIC — normal images may also show high ELA
        due to edges, textures, or mixed compression history.
        """
        quality = self.config.get("ela_jpeg_quality", 90)
        scale = self.config.get("ela_scale_factor", 20)
        threshold = self.config.get("ela_suspicious_threshold", 40.0)

        try:
            # Encode to JPEG in memory (no disk I/O)
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            success, encoded = cv2.imencode(".jpg", bgr, encode_param)
            if not success:
                return {
                    "check": self._make_check(
                        "Error Level Analysis",
                        "Measures compression inconsistency across the image.",
                        "ELA encoding failed.",
                        suspicious=False,
                        details="Could not encode image as JPEG.",
                    ),
                    "ela_image": None,
                }

            # Decode back
            recompressed = cv2.imdecode(
                np.frombuffer(encoded, dtype=np.uint8), cv2.IMREAD_COLOR
            )

            # Compute absolute difference
            diff = cv2.absdiff(bgr, recompressed)
            ela = diff * scale
            ela = np.clip(ela, 0, 255).astype(np.uint8)

            # Metrics
            gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            mean_val = float(np.mean(gray_diff))
            max_val = float(np.max(gray_diff))
            std_val = float(np.std(gray_diff))

            suspicious = mean_val > threshold

            if suspicious:
                result_text = (
                    f"Elevated compression inconsistency detected "
                    f"(mean={mean_val:.1f}, threshold={threshold:.1f}). "
                    "This may indicate image editing or format conversion. "
                    "Human review recommended."
                )
            else:
                result_text = (
                    f"Compression levels appear consistent "
                    f"(mean={mean_val:.1f}, threshold={threshold:.1f})."
                )

            return {
                "check": self._make_check(
                    "Error Level Analysis",
                    "Measures compression inconsistency across the image.",
                    result_text,
                    suspicious=suspicious,
                    details=(
                        f"ELA mean={mean_val:.2f}, max={max_val:.2f}, "
                        f"std={std_val:.2f}, quality={quality}, "
                        f"scale={scale}"
                    ),
                    metrics={
                        "ela_mean": round(mean_val, 4),
                        "ela_max": round(max_val, 4),
                        "ela_std": round(std_val, 4),
                    },
                ),
                "ela_image": ela,
            }

        except Exception as exc:
            logger.warning("ELA analysis failed: %s", exc)
            return {
                "check": self._make_check(
                    "Error Level Analysis",
                    "Measures compression inconsistency across the image.",
                    f"ELA analysis encountered an error: {exc}",
                    suspicious=False,
                    details=str(exc),
                ),
                "ela_image": None,
            }

    # ── Edge density ─────────────────────────────────────────────────

    def _edge_density_analysis(self, bgr: np.ndarray) -> dict:
        """Analyze edge density using Canny edge detection.

        Document images typically have moderate edge density from text
        and borders.  Unusually low density may indicate a blank or
        heavily blurred region; unusually high density may indicate
        synthetic noise or artifacts.
        """
        low_thresh = self.config.get("edge_density_low", 0.02)
        high_thresh = self.config.get("edge_density_high", 0.40)

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        total_pixels = edges.shape[0] * edges.shape[1]
        edge_pixels = int(np.count_nonzero(edges))
        density = edge_pixels / total_pixels if total_pixels > 0 else 0.0

        suspicious = density < low_thresh or density > high_thresh
        if density < low_thresh:
            result_text = (
                f"Very low edge density ({density:.3f}). "
                "The image may be heavily blurred or blank. "
                "This is unusual for a document image."
            )
        elif density > high_thresh:
            result_text = (
                f"Very high edge density ({density:.3f}). "
                "This may indicate synthetic noise or heavy processing."
            )
        else:
            result_text = (
                f"Edge density is within normal range ({density:.3f})."
            )

        return self._make_check(
            "Edge Density",
            "Checks whether edge content is consistent with a typical document.",
            result_text,
            suspicious=suspicious,
            details=(
                f"density={density:.4f}, edge_pixels={edge_pixels}, "
                f"total={total_pixels}, "
                f"range=[{low_thresh}, {high_thresh}]"
            ),
            metrics={
                "edge_density": round(density, 6),
                "edge_pixels": edge_pixels,
            },
        )

    # ── Noise analysis ───────────────────────────────────────────────

    def _noise_analysis(self, bgr: np.ndarray) -> dict:
        """Estimate high-frequency noise level.

        Subtracts a Gaussian-blurred version from the image to isolate
        high-frequency components.  Unusually high noise std may indicate
        added synthetic noise or heavy JPEG artifacts.
        """
        noise_thresh = self.config.get("noise_std_suspicious", 35.0)

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        noise = gray - blurred
        noise_std = float(np.std(noise))
        noise_mean = float(np.mean(np.abs(noise)))

        suspicious = noise_std > noise_thresh

        if suspicious:
            result_text = (
                f"Elevated high-frequency noise (std={noise_std:.1f}, "
                f"threshold={noise_thresh:.1f}). "
                "This may indicate heavy compression artifacts or "
                "synthetic noise addition."
            )
        else:
            result_text = (
                f"Noise levels appear normal (std={noise_std:.1f})."
            )

        return self._make_check(
            "Noise Analysis",
            "Estimates high-frequency noise to detect unusual processing.",
            result_text,
            suspicious=suspicious,
            details=(
                f"noise_std={noise_std:.4f}, noise_mean_abs={noise_mean:.4f}, "
                f"threshold={noise_thresh}"
            ),
            metrics={
                "noise_std": round(noise_std, 4),
                "noise_mean_abs": round(noise_mean, 4),
            },
        )

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _make_check(
        name: str,
        description: str,
        result: str,
        *,
        suspicious: bool,
        details: str,
        metrics: dict | None = None,
    ) -> dict:
        """Build a standardized check result dict."""
        check: dict[str, Any] = {
            "name": name,
            "description": description,
            "result": result,
            "suspicious": suspicious,
            "details": details,
        }
        if metrics:
            check["metrics"] = metrics
        return check

    @staticmethod
    def _calculate_score(checks: list[dict]) -> float:
        """Calculate aggregate heuristic anomaly score (0.0–1.0).

        Simple approach: each suspicious check contributes equally.
        Score = (suspicious_count / total_checks).

        This is a deterministic heuristic, NOT a calibrated probability.
        """
        if not checks:
            return 0.0
        suspicious_count = sum(1 for c in checks if c.get("suspicious"))
        return suspicious_count / len(checks)

    @staticmethod
    def _error_result(message: str) -> dict:
        """Build an error/no-analysis result."""
        return {
            "checks": [],
            "ela_image": None,
            "overall_suspicious": False,
            "suspicion_score": 0.0,
            "status": "error",
            "method": "heuristic_cv",
            "message": message,
        }
