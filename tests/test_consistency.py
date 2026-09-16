"""Tests for ConsistencyChecker (Phase 5).

All tests use synthetic data — no real identity documents.
"""
from __future__ import annotations

import pytest
from src.verification.consistency import ConsistencyChecker


# ── Helpers ──────────────────────────────────────────────────────────────────

def _doc(doc_type: str, **fields) -> dict:
    """Build a minimal document result dict."""
    return {"document_type": doc_type, "fields": fields}


def _doc_with_dict_fields(doc_type: str, **fields) -> dict:
    """Build a document with dict-style field values (value/confidence)."""
    field_dict = {k: {"value": v, "confidence": 0.7} for k, v in fields.items()}
    return {"document_type": doc_type, "fields": field_dict}


# ═══════════════════════════════════════════════════════════════════════════════
# Initialization
# ═══════════════════════════════════════════════════════════════════════════════


class TestConsistencyInit:
    def test_init(self) -> None:
        checker = ConsistencyChecker()
        assert checker is not None


# ═══════════════════════════════════════════════════════════════════════════════
# Input handling
# ═══════════════════════════════════════════════════════════════════════════════


class TestConsistencyInputHandling:
    def test_none_input(self) -> None:
        checker = ConsistencyChecker()
        result = checker.check(None)
        assert result["status"] == "insufficient_documents"
        assert result["consistent"] is True

    def test_empty_list(self) -> None:
        checker = ConsistencyChecker()
        result = checker.check([])
        assert result["status"] == "insufficient_documents"
        assert result["consistent"] is True

    def test_single_document(self) -> None:
        checker = ConsistencyChecker()
        result = checker.check([_doc("aadhaar", name="Test")])
        assert result["status"] == "insufficient_documents"
        assert result["consistent"] is True
        assert result["compared_count"] == 0
        assert result["mismatch_count"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Name comparison
# ═══════════════════════════════════════════════════════════════════════════════


class TestNameConsistency:
    def test_matching_names(self) -> None:
        checker = ConsistencyChecker()
        result = checker.check([
            _doc("aadhaar", name="RAHUL KUMAR"),
            _doc("pan", name="RAHUL KUMAR"),
        ])
        assert result["status"] == "success"
        assert result["consistent"] is True
        name_check = [c for c in result["checks"] if c["field"] == "name"][0]
        assert name_check["consistent"] is True

    def test_mismatching_names(self) -> None:
        checker = ConsistencyChecker()
        result = checker.check([
            _doc("aadhaar", name="RAHUL KUMAR"),
            _doc("pan", name="RAHUL SHARMA"),
        ])
        assert result["consistent"] is False
        name_check = [c for c in result["checks"] if c["field"] == "name"][0]
        assert name_check["consistent"] is False
        assert result["mismatch_count"] >= 1

    def test_case_insensitive(self) -> None:
        checker = ConsistencyChecker()
        result = checker.check([
            _doc("aadhaar", name="rahul kumar"),
            _doc("pan", name="RAHUL KUMAR"),
        ])
        name_check = [c for c in result["checks"] if c["field"] == "name"][0]
        assert name_check["consistent"] is True

    def test_whitespace_normalization(self) -> None:
        checker = ConsistencyChecker()
        result = checker.check([
            _doc("aadhaar", name="  RAHUL   KUMAR  "),
            _doc("pan", name="RAHUL KUMAR"),
        ])
        name_check = [c for c in result["checks"] if c["field"] == "name"][0]
        assert name_check["consistent"] is True

    def test_punctuation_normalization(self) -> None:
        checker = ConsistencyChecker()
        result = checker.check([
            _doc("aadhaar", name="R. KUMAR"),
            _doc("pan", name="R KUMAR"),
        ])
        name_check = [c for c in result["checks"] if c["field"] == "name"][0]
        assert name_check["consistent"] is True

    def test_dict_format_fields(self) -> None:
        """Fields in dict format {value, confidence} should work."""
        checker = ConsistencyChecker()
        result = checker.check([
            _doc_with_dict_fields("aadhaar", name="RAHUL KUMAR"),
            _doc_with_dict_fields("pan", name="RAHUL KUMAR"),
        ])
        name_check = [c for c in result["checks"] if c["field"] == "name"][0]
        assert name_check["consistent"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# DOB comparison
# ═══════════════════════════════════════════════════════════════════════════════


class TestDOBConsistency:
    def test_matching_dob(self) -> None:
        checker = ConsistencyChecker()
        result = checker.check([
            _doc("aadhaar", name="TEST", dob="01/01/2000"),
            _doc("pan", name="TEST", dob="01/01/2000"),
        ])
        dob_check = [c for c in result["checks"] if c["field"] == "dob"][0]
        assert dob_check["consistent"] is True

    def test_mismatching_dob(self) -> None:
        checker = ConsistencyChecker()
        result = checker.check([
            _doc("aadhaar", name="TEST", dob="01/01/2000"),
            _doc("pan", name="TEST", dob="15/06/1995"),
        ])
        dob_check = [c for c in result["checks"] if c["field"] == "dob"][0]
        assert dob_check["consistent"] is False

    def test_different_date_formats(self) -> None:
        """DD/MM/YYYY vs DD-MM-YYYY should match."""
        checker = ConsistencyChecker()
        result = checker.check([
            _doc("aadhaar", name="TEST", dob="01/01/2000"),
            _doc("pan", name="TEST", dob="01-01-2000"),
        ])
        dob_check = [c for c in result["checks"] if c["field"] == "dob"][0]
        assert dob_check["consistent"] is True

    def test_iso_format_comparison(self) -> None:
        """YYYY-MM-DD vs DD/MM/YYYY should match."""
        checker = ConsistencyChecker()
        result = checker.check([
            _doc("aadhaar", name="TEST", dob="2000-01-15"),
            _doc("pan", name="TEST", dob="15/01/2000"),
        ])
        dob_check = [c for c in result["checks"] if c["field"] == "dob"][0]
        assert dob_check["consistent"] is True

    def test_malformed_date(self) -> None:
        """Unparseable date should result in inconsistent (cannot confirm)."""
        checker = ConsistencyChecker()
        result = checker.check([
            _doc("aadhaar", name="TEST", dob="01/01/2000"),
            _doc("pan", name="TEST", dob="not-a-date"),
        ])
        dob_check = [c for c in result["checks"] if c["field"] == "dob"][0]
        assert dob_check["consistent"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# Missing / edge cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestConsistencyEdgeCases:
    def test_no_comparable_fields(self) -> None:
        """Documents with no shared comparable fields."""
        checker = ConsistencyChecker()
        result = checker.check([
            _doc("aadhaar", aadhaar_number="1234"),
            _doc("pan", pan_number="ABCDE1234F"),
        ])
        assert result["status"] == "success"
        assert result["consistent"] is True
        assert result["compared_count"] == 0

    def test_one_doc_missing_name(self) -> None:
        """Only one doc has name → no name comparison."""
        checker = ConsistencyChecker()
        result = checker.check([
            _doc("aadhaar", name="RAHUL KUMAR"),
            _doc("pan"),  # no name field
        ])
        name_checks = [c for c in result["checks"] if c["field"] == "name"]
        assert len(name_checks) == 0  # Cannot compare

    def test_empty_name_value(self) -> None:
        """Empty string name should be treated as missing."""
        checker = ConsistencyChecker()
        result = checker.check([
            _doc("aadhaar", name="RAHUL KUMAR"),
            _doc("pan", name=""),
        ])
        name_checks = [c for c in result["checks"] if c["field"] == "name"]
        assert len(name_checks) == 0

    def test_three_documents(self) -> None:
        """Three documents with matching names."""
        checker = ConsistencyChecker()
        result = checker.check([
            _doc("aadhaar", name="RAHUL KUMAR"),
            _doc("pan", name="RAHUL KUMAR"),
            _doc("voter_id", name="RAHUL KUMAR"),
        ])
        name_check = [c for c in result["checks"] if c["field"] == "name"][0]
        assert name_check["consistent"] is True
        assert len(name_check["documents_compared"]) == 3


# ═══════════════════════════════════════════════════════════════════════════════
# Return schema
# ═══════════════════════════════════════════════════════════════════════════════


class TestConsistencySchema:
    def test_success_schema(self) -> None:
        checker = ConsistencyChecker()
        result = checker.check([
            _doc("aadhaar", name="TEST"),
            _doc("pan", name="TEST"),
        ])
        assert "checks" in result
        assert "consistent" in result
        assert "consistency_score" in result
        assert "status" in result
        assert "message" in result
        assert "compared_count" in result
        assert "mismatch_count" in result
        assert isinstance(result["consistent"], bool)
        assert isinstance(result["consistency_score"], float)

    def test_check_item_schema(self) -> None:
        checker = ConsistencyChecker()
        result = checker.check([
            _doc("aadhaar", name="TEST"),
            _doc("pan", name="TEST"),
        ])
        for chk in result["checks"]:
            assert "field" in chk
            assert "field_label" in chk
            assert "documents_compared" in chk
            assert "consistent" in chk
            assert "message" in chk
            assert "values" in chk

    def test_consistency_score_range(self) -> None:
        checker = ConsistencyChecker()
        result = checker.check([
            _doc("aadhaar", name="A", dob="01/01/2000"),
            _doc("pan", name="B", dob="02/02/2001"),
        ])
        assert 0.0 <= result["consistency_score"] <= 1.0
