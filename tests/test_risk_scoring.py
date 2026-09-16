"""Tests for RiskScorer (Phase 5).

All tests use synthetic data — no real identity documents.
"""
from __future__ import annotations

import pytest
from src.risk.scoring import RiskScorer


# ── Helpers ──────────────────────────────────────────────────────────────────

def _empty_validation() -> dict:
    return {"checks": [], "valid_count": 0, "total_count": 0, "all_passed": True}


def _passing_validation() -> dict:
    return {
        "checks": [
            {"field": "name", "check_name": "required_name", "passed": True, "message": "OK", "severity": "warning"},
            {"field": "number", "check_name": "format_number", "passed": True, "message": "OK", "severity": "warning"},
        ],
        "valid_count": 2, "total_count": 2, "all_passed": True,
    }


def _failing_validation() -> dict:
    return {
        "checks": [
            {"field": "name", "check_name": "required_name", "passed": True, "message": "OK", "severity": "warning"},
            {"field": "number", "check_name": "format_number", "passed": False, "message": "Invalid format", "severity": "warning"},
            {"field": "checksum", "check_name": "checksum_aadhaar", "passed": False, "message": "Checksum failed", "severity": "error"},
        ],
        "valid_count": 1, "total_count": 3, "all_passed": False,
    }


def _clean_tampering() -> dict:
    return {
        "checks": [
            {"name": "ELA", "suspicious": False},
            {"name": "Edge", "suspicious": False},
            {"name": "Noise", "suspicious": False},
        ],
        "overall_suspicious": False, "suspicion_score": 0.0, "status": "success",
    }


def _suspicious_tampering() -> dict:
    return {
        "checks": [
            {"name": "ELA", "suspicious": True, "result": "High ELA response"},
            {"name": "Edge", "suspicious": False},
            {"name": "Noise", "suspicious": True, "result": "High noise"},
        ],
        "overall_suspicious": True, "suspicion_score": 0.67, "status": "success",
    }


def _consistent_consistency() -> dict:
    return {
        "checks": [{"field": "name", "consistent": True}],
        "consistent": True, "consistency_score": 1.0, "status": "success",
    }


def _inconsistent_consistency() -> dict:
    return {
        "checks": [
            {"field": "name", "field_label": "Name", "consistent": False,
             "message": "Name differs"},
            {"field": "dob", "field_label": "DOB", "consistent": False,
             "message": "DOB differs"},
        ],
        "consistent": False, "consistency_score": 0.0, "status": "success",
    }


def _insufficient_consistency() -> dict:
    return {
        "checks": [], "consistent": True, "consistency_score": 1.0,
        "status": "insufficient_documents",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Initialization
# ═══════════════════════════════════════════════════════════════════════════════


class TestRiskInit:
    def test_init(self) -> None:
        scorer = RiskScorer()
        assert scorer is not None
        assert hasattr(scorer, "weights")
        assert hasattr(scorer, "thresholds")
        assert hasattr(scorer, "levels")


# ═══════════════════════════════════════════════════════════════════════════════
# No findings → LOW
# ═══════════════════════════════════════════════════════════════════════════════


class TestRiskNoFindings:
    def test_empty_everything(self) -> None:
        scorer = RiskScorer()
        result = scorer.calculate(_empty_validation(), _clean_tampering())
        assert result["score"] == 0.0
        assert result["level"] == "LOW"
        assert result["status"] == "success"

    def test_all_passing(self) -> None:
        scorer = RiskScorer()
        result = scorer.calculate(_passing_validation(), _clean_tampering())
        assert result["score"] == 0.0
        assert result["level"] == "LOW"
        assert len(result["factors"]) == 0
        assert len(result["indicators"]) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Validation indicators
# ═══════════════════════════════════════════════════════════════════════════════


class TestRiskValidation:
    def test_validation_failure_increases_score(self) -> None:
        scorer = RiskScorer()
        result = scorer.calculate(_failing_validation(), _clean_tampering())
        assert result["score"] > 0.0
        assert any("validation" in f["category"] for f in result["factors"])

    def test_validation_indicators_listed(self) -> None:
        scorer = RiskScorer()
        result = scorer.calculate(_failing_validation(), _clean_tampering())
        assert len(result["indicators"]) >= 2
        assert any("Validation" in i for i in result["indicators"])


# ═══════════════════════════════════════════════════════════════════════════════
# Tampering indicators
# ═══════════════════════════════════════════════════════════════════════════════


class TestRiskTampering:
    def test_tampering_increases_score(self) -> None:
        scorer = RiskScorer()
        result = scorer.calculate(_passing_validation(), _suspicious_tampering())
        assert result["score"] > 0.0
        assert any("tampering" in f["category"] for f in result["factors"])

    def test_tampering_error_treated_as_zero(self) -> None:
        scorer = RiskScorer()
        result = scorer.calculate(
            _passing_validation(),
            {"checks": [], "status": "error"},
        )
        assert result["score"] == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# Consistency indicators
# ═══════════════════════════════════════════════════════════════════════════════


class TestRiskConsistency:
    def test_consistency_mismatch_increases_score(self) -> None:
        scorer = RiskScorer()
        result = scorer.calculate(
            _passing_validation(),
            _clean_tampering(),
            _inconsistent_consistency(),
        )
        assert result["score"] > 0.0
        assert any("consistency" in f["category"] for f in result["factors"])

    def test_consistent_no_penalty(self) -> None:
        scorer = RiskScorer()
        result = scorer.calculate(
            _passing_validation(),
            _clean_tampering(),
            _consistent_consistency(),
        )
        assert result["score"] == 0.0

    def test_insufficient_consistency_no_penalty(self) -> None:
        scorer = RiskScorer()
        result = scorer.calculate(
            _passing_validation(),
            _clean_tampering(),
            _insufficient_consistency(),
        )
        assert result["score"] == 0.0

    def test_none_consistency_no_penalty(self) -> None:
        scorer = RiskScorer()
        result = scorer.calculate(
            _passing_validation(),
            _clean_tampering(),
            None,
        )
        assert result["score"] == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# Multiple indicators
# ═══════════════════════════════════════════════════════════════════════════════


class TestRiskMultipleIndicators:
    def test_combined_indicators(self) -> None:
        scorer = RiskScorer()
        result = scorer.calculate(
            _failing_validation(),
            _suspicious_tampering(),
            _inconsistent_consistency(),
        )
        assert result["score"] > 0.3
        assert len(result["factors"]) >= 4
        categories = {f["category"] for f in result["factors"]}
        assert "validation" in categories
        assert "tampering" in categories
        assert "consistency" in categories


# ═══════════════════════════════════════════════════════════════════════════════
# Score bounds and levels
# ═══════════════════════════════════════════════════════════════════════════════


class TestRiskScoreBounds:
    def test_score_range(self) -> None:
        scorer = RiskScorer()
        for val, tamp, cons in [
            (_empty_validation(), _clean_tampering(), None),
            (_failing_validation(), _suspicious_tampering(), _inconsistent_consistency()),
            (_passing_validation(), _clean_tampering(), _consistent_consistency()),
        ]:
            result = scorer.calculate(val, tamp, cons)
            assert 0.0 <= result["score"] <= 1.0
            assert 0 <= result["score_pct"] <= 100

    def test_deterministic(self) -> None:
        """Same inputs produce identical output."""
        scorer = RiskScorer()
        r1 = scorer.calculate(_failing_validation(), _suspicious_tampering())
        r2 = scorer.calculate(_failing_validation(), _suspicious_tampering())
        assert r1["score"] == r2["score"]
        assert r1["level"] == r2["level"]

    def test_low_level_threshold(self) -> None:
        scorer = RiskScorer()
        result = scorer.calculate(_empty_validation(), _clean_tampering())
        assert result["level"] == "LOW"


# ═══════════════════════════════════════════════════════════════════════════════
# Explainability
# ═══════════════════════════════════════════════════════════════════════════════


class TestRiskExplainability:
    def test_factors_have_category(self) -> None:
        scorer = RiskScorer()
        result = scorer.calculate(_failing_validation(), _suspicious_tampering())
        for f in result["factors"]:
            assert "category" in f
            assert "name" in f
            assert "contribution" in f
            assert "description" in f

    def test_recommendation_present(self) -> None:
        scorer = RiskScorer()
        for level_input in [
            (_empty_validation(), _clean_tampering()),
            (_failing_validation(), _suspicious_tampering()),
        ]:
            result = scorer.calculate(*level_input)
            assert isinstance(result["recommendation"], str)
            assert len(result["recommendation"]) > 10

    def test_summary_mentions_heuristic(self) -> None:
        scorer = RiskScorer()
        result = scorer.calculate(_failing_validation(), _clean_tampering())
        assert "heuristic" in result["summary"].lower()

    def test_recommendation_no_fraud_language(self) -> None:
        """Recommendation must not claim fraud."""
        scorer = RiskScorer()
        for val, tamp, cons in [
            (_empty_validation(), _clean_tampering(), None),
            (_failing_validation(), _suspicious_tampering(), _inconsistent_consistency()),
        ]:
            result = scorer.calculate(val, tamp, cons)
            rec = result["recommendation"].lower()
            assert "fraud" not in rec
            assert "fake" not in rec
            assert "forged" not in rec
            assert "reject" not in rec


# ═══════════════════════════════════════════════════════════════════════════════
# Return schema
# ═══════════════════════════════════════════════════════════════════════════════


class TestRiskSchema:
    def test_all_keys_present(self) -> None:
        scorer = RiskScorer()
        result = scorer.calculate(_failing_validation(), _suspicious_tampering())
        for key in ("score", "score_pct", "level", "level_info",
                     "factors", "indicators", "recommendation", "summary", "status"):
            assert key in result, f"Missing key: {key}"

    def test_level_info_structure(self) -> None:
        scorer = RiskScorer()
        result = scorer.calculate(_empty_validation(), _clean_tampering())
        info = result["level_info"]
        assert "label" in info
        assert "color" in info


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 7: Hardening tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestRiskHardening:
    """Phase 7 hardening tests for edge cases and design invariants."""

    def test_single_doc_no_consistency_penalty(self) -> None:
        """Single-document screening must NOT increase risk due to missing
        consistency data. Score should be the same as if consistency is
        explicitly absent."""
        scorer = RiskScorer()
        r_none = scorer.calculate(_failing_validation(), _clean_tampering(), None)
        r_insuf = scorer.calculate(
            _failing_validation(), _clean_tampering(), _insufficient_consistency()
        )
        assert r_none["score"] == r_insuf["score"]
        assert r_none["level"] == r_insuf["level"]

    def test_name_mismatch_creates_indicator(self) -> None:
        """A name mismatch in consistency should produce a visible indicator."""
        scorer = RiskScorer()
        result = scorer.calculate(
            _passing_validation(),
            _clean_tampering(),
            _inconsistent_consistency(),
        )
        indicator_text = " ".join(result["indicators"]).lower()
        assert "mismatch" in indicator_text

    def test_consistency_mismatch_increases_score(self) -> None:
        """Consistency mismatches should increase risk score compared
        to consistent documents."""
        scorer = RiskScorer()
        r_good = scorer.calculate(
            _passing_validation(),
            _clean_tampering(),
            _consistent_consistency(),
        )
        r_bad = scorer.calculate(
            _passing_validation(),
            _clean_tampering(),
            _inconsistent_consistency(),
        )
        assert r_bad["score"] > r_good["score"]

    def test_weight_normalization_sums_to_one(self) -> None:
        """Effective weights should sum to approximately 1.0."""
        scorer = RiskScorer()
        w_val = scorer.weights.get("field_validation", 0.3)
        w_fmt = scorer.weights.get("format_compliance", 0.2)
        w_tamp = scorer.weights.get("tampering_analysis", 0.35)
        w_cons = scorer.weights.get("consistency", 0.15)
        total = w_val + w_fmt + w_tamp + w_cons
        assert abs(total - 1.0) < 0.01

    def test_score_at_boundary_0_3(self) -> None:
        """Score at exactly 0.3 should be LOW."""
        scorer = RiskScorer()
        assert scorer._determine_level(0.3) == "LOW"

    def test_score_at_boundary_0_6(self) -> None:
        """Score at exactly 0.6 should be MEDIUM."""
        scorer = RiskScorer()
        assert scorer._determine_level(0.6) == "MEDIUM"

    def test_score_above_0_6_is_high(self) -> None:
        """Score above 0.6 should be HIGH."""
        scorer = RiskScorer()
        assert scorer._determine_level(0.61) == "HIGH"

    def test_all_clean_is_low(self) -> None:
        """Everything clean should produce LOW risk."""
        scorer = RiskScorer()
        result = scorer.calculate(
            _passing_validation(),
            _clean_tampering(),
            _consistent_consistency(),
        )
        assert result["level"] == "LOW"
        assert result["score"] == 0.0

    def test_all_bad_is_high(self) -> None:
        """Everything failing should produce HIGH risk."""
        scorer = RiskScorer()
        result = scorer.calculate(
            _failing_validation(),
            _suspicious_tampering(),
            _inconsistent_consistency(),
        )
        assert result["level"] in ("MEDIUM", "HIGH")
        assert result["score"] > 0.3

    def test_empty_results_no_crash(self) -> None:
        """Empty/None inputs should produce a valid low score."""
        scorer = RiskScorer()
        result = scorer.calculate({}, {}, None)
        assert result["status"] == "success"
        assert result["score"] == 0.0
        assert result["level"] == "LOW"

    def test_deterministic(self) -> None:
        """Same inputs must produce the same output."""
        scorer = RiskScorer()
        r1 = scorer.calculate(_failing_validation(), _suspicious_tampering())
        r2 = scorer.calculate(_failing_validation(), _suspicious_tampering())
        assert r1["score"] == r2["score"]
        assert r1["level"] == r2["level"]
