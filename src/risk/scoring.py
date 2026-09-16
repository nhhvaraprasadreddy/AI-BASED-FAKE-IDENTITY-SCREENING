"""Explainable rule-based risk scoring.

Combines findings from validation, tampering analysis, and cross-document
consistency into a single heuristic screening score with explainable
contributing indicators.

**This is a deterministic rule-based scoring system, NOT a trained ML
model and NOT a calibrated probability.**  The score is a heuristic
aggregation of screening indicators designed to assist human reviewers.
"""
from __future__ import annotations

import logging
from typing import Any

from src.config import RISK_WEIGHTS, RISK_THRESHOLDS, RISK_LEVELS

logger = logging.getLogger(__name__)


class RiskScorer:
    """Calculates aggregate risk scores from analysis results.

    Uses weighted deterministic rules — NOT machine learning.
    The output is a heuristic screening indicator for human review.
    """

    def __init__(self) -> None:
        """Initialize with risk configuration from config."""
        self.weights = RISK_WEIGHTS
        self.thresholds = RISK_THRESHOLDS
        self.levels = RISK_LEVELS
        logger.info("RiskScorer initialized")

    def calculate(
        self,
        validation_results: dict,
        tampering_results: dict,
        consistency_results: dict | None = None,
    ) -> dict:
        """Calculate overall risk score from component analyses.

        Args:
            validation_results: Output from DocumentValidator.validate()
            tampering_results: Output from TamperingAnalyzer.analyze()
            consistency_results: Output from ConsistencyChecker.check(),
                               or None if single-document screening.

        Returns:
            dict with keys:
                - score (float): Overall risk score (0.0-1.0)
                - score_pct (int): Score as 0-100 integer
                - level (str): 'LOW', 'MEDIUM', or 'HIGH'
                - level_info (dict): Color and icon for the level
                - factors (list[dict]): Contributing risk factors
                - indicators (list[str]): Human-readable indicator list
                - recommendation (str): Human-readable recommendation
                - summary (str): One-line risk summary
                - status (str): 'success'
        """
        factors: list[dict[str, Any]] = []
        indicators: list[str] = []

        # ── 1. Validation findings ──────────────────────────────────
        val_score = self._score_validation(
            validation_results, factors, indicators,
        )

        # ── 2. Tampering findings ───────────────────────────────────
        tamp_score = self._score_tampering(
            tampering_results, factors, indicators,
        )

        # ── 3. Consistency findings ─────────────────────────────────
        cons_score = self._score_consistency(
            consistency_results, factors, indicators,
        )

        # ── Weighted aggregation ────────────────────────────────────
        w_val = self.weights.get("field_validation", 0.3)
        w_fmt = self.weights.get("format_compliance", 0.2)
        w_tamp = self.weights.get("tampering_analysis", 0.35)
        w_cons = self.weights.get("consistency", 0.15)

        # Combine validation + format into one validation weight
        w_val_total = w_val + w_fmt

        # If consistency data not available, redistribute its weight
        if consistency_results is None or \
           consistency_results.get("status") == "insufficient_documents":
            active_total = w_val_total + w_tamp
            if active_total > 0:
                w_val_total = w_val_total / active_total
                w_tamp = w_tamp / active_total
            w_cons = 0.0
        else:
            total = w_val_total + w_tamp + w_cons
            if total > 0:
                w_val_total /= total
                w_tamp /= total
                w_cons /= total

        raw_score = (
            val_score * w_val_total
            + tamp_score * w_tamp
            + cons_score * w_cons
        )
        # Clamp to 0.0 – 1.0
        score = max(0.0, min(1.0, raw_score))
        score = round(score, 4)
        score_pct = round(score * 100)

        # ── Determine level ─────────────────────────────────────────
        level = self._determine_level(score)
        recommendation = self._recommendation(level)
        level_info = self.levels.get(level, self.levels["LOW"])

        summary = (
            f"Heuristic screening score: {score_pct}/100 — "
            f"Risk level: {level}. "
            "This is a deterministic heuristic, not a probability of fraud."
        )

        logger.info(
            "Risk scoring: score=%.4f (%d/100) level=%s factors=%d",
            score, score_pct, level, len(factors),
        )

        return {
            "score": score,
            "score_pct": score_pct,
            "level": level,
            "level_info": level_info,
            "factors": factors,
            "indicators": indicators,
            "recommendation": recommendation,
            "summary": summary,
            "status": "success",
        }

    # ── Validation scoring ───────────────────────────────────────────

    def _score_validation(
        self,
        results: dict,
        factors: list[dict],
        indicators: list[str],
    ) -> float:
        """Score validation results.  Returns 0.0 (clean) to 1.0 (all failed)."""
        if not results:
            return 0.0

        checks = results.get("checks", [])
        if not checks:
            return 0.0

        total = len(checks)
        failed = sum(1 for c in checks if not c.get("passed", True))

        if failed == 0:
            return 0.0

        sub_score = failed / total

        # Build per-check indicators
        for c in checks:
            if not c.get("passed", True):
                check_name = c.get("check_name", c.get("field", "unknown"))
                severity = c.get("severity", "warning")
                msg = c.get("message", "Validation failed")
                weight = 0.25 if severity == "error" else 0.15
                factors.append({
                    "category": "validation",
                    "name": check_name,
                    "contribution": round(weight * 100),
                    "description": msg,
                })
                indicators.append(f"Validation: {msg}")

        return sub_score

    # ── Tampering scoring ────────────────────────────────────────────

    def _score_tampering(
        self,
        results: dict,
        factors: list[dict],
        indicators: list[str],
    ) -> float:
        """Score tampering results.  Returns 0.0 (clean) to 1.0 (all suspicious)."""
        if not results or results.get("status") == "error":
            return 0.0

        checks = results.get("checks", [])
        if not checks:
            return 0.0

        total = len(checks)
        suspicious = sum(1 for c in checks if c.get("suspicious"))

        if suspicious == 0:
            return 0.0

        sub_score = suspicious / total

        for c in checks:
            if c.get("suspicious"):
                name = c.get("name", "unknown")
                detail = c.get("result", "Suspicious indicator")
                weight = 0.15
                factors.append({
                    "category": "tampering",
                    "name": name,
                    "contribution": round(weight * 100),
                    "description": f"Potential image anomaly: {name}",
                })
                indicators.append(f"Image anomaly: {detail}")

        return sub_score

    # ── Consistency scoring ──────────────────────────────────────────

    def _score_consistency(
        self,
        results: dict | None,
        factors: list[dict],
        indicators: list[str],
    ) -> float:
        """Score consistency results.  Returns 0.0 (consistent) to 1.0 (all mismatch)."""
        if results is None:
            return 0.0
        if results.get("status") == "insufficient_documents":
            return 0.0

        checks = results.get("checks", [])
        if not checks:
            return 0.0

        total = len(checks)
        mismatches = sum(1 for c in checks if not c.get("consistent", True))

        if mismatches == 0:
            return 0.0

        sub_score = mismatches / total

        for c in checks:
            if not c.get("consistent", True):
                field = c.get("field_label", c.get("field", "unknown"))
                weight = 0.20
                factors.append({
                    "category": "consistency",
                    "name": f"{field} mismatch",
                    "contribution": round(weight * 100),
                    "description": c.get("message", f"{field} differs across documents"),
                })
                indicators.append(f"Cross-document: {field} mismatch")

        return sub_score

    # ── helpers ──────────────────────────────────────────────────────

    def _determine_level(self, score: float) -> str:
        """Map score to risk level using configured thresholds."""
        low_max = self.thresholds.get("low_max", 0.3)
        medium_max = self.thresholds.get("medium_max", 0.6)
        if score <= low_max:
            return "LOW"
        if score <= medium_max:
            return "MEDIUM"
        return "HIGH"

    @staticmethod
    def _recommendation(level: str) -> str:
        """Generate human-review recommendation based on risk level."""
        recs = {
            "LOW": (
                "Low number of suspicious indicators. "
                "Continue normal review process."
            ),
            "MEDIUM": (
                "Some suspicious indicators were identified. "
                "Additional verification is recommended."
            ),
            "HIGH": (
                "Multiple suspicious indicators were identified. "
                "Human review is strongly recommended before "
                "proceeding with this document."
            ),
        }
        return recs.get(level, recs["LOW"])
