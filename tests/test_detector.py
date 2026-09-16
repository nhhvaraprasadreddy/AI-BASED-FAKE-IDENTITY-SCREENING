"""Unit tests for DocumentDetector (keyword-frequency heuristic).

These tests validate the detection logic directly — no OCR or image
processing is involved.  The detector receives plain text and matches
keywords from config.
"""
from __future__ import annotations

import pytest

from src.documents.detector import DocumentDetector


@pytest.fixture
def detector() -> DocumentDetector:
    return DocumentDetector()


# ── Aadhaar detection ────────────────────────────────────────────────


class TestAadhaarDetection:
    def test_detect_aadhaar_english(self, detector) -> None:
        text = "Government of India\nUnique Identification Authority\nAadhaar"
        result = detector.detect(text)
        assert result["document_type"] == "aadhaar"
        assert result["status"] == "success"
        assert result["confidence"] > 0

    def test_detect_aadhaar_uidai_keyword(self, detector) -> None:
        text = "UIDAI\nAadhaar\n1234 5678 9012"
        result = detector.detect(text)
        assert result["document_type"] == "aadhaar"

    def test_aadhaar_method_is_keyword_heuristic(self, detector) -> None:
        text = "Aadhaar UIDAI Government of India"
        result = detector.detect(text)
        assert result["method"] == "keyword_heuristic"


# ── PAN detection ────────────────────────────────────────────────────


class TestPANDetection:
    def test_detect_pan(self, detector) -> None:
        text = "Income Tax Department\nPermanent Account Number\nPAN"
        result = detector.detect(text)
        assert result["document_type"] == "pan"
        assert result["status"] == "success"

    def test_pan_word_boundary(self, detector) -> None:
        """'pan' as a word should match, but must not match 'company'."""
        text = "Income Tax PAN Department"
        result = detector.detect(text)
        assert result["document_type"] == "pan"

    def test_pan_substring_no_false_positive(self, detector) -> None:
        """'pan' inside other words should NOT trigger a match."""
        text = "company panorama Japan pandemic"
        result = detector.detect(text)
        # 'pan' should not match because it only appears as substring
        assert result["document_type"] != "pan" or result["status"] == "no_match"


# ── Voter ID detection ──────────────────────────────────────────────


class TestVoterIDDetection:
    def test_detect_voter_id(self, detector) -> None:
        text = "Election Commission of India\nElectoral Photo Identity Card\nEPIC"
        result = detector.detect(text)
        assert result["document_type"] == "voter_id"
        assert result["status"] == "success"

    def test_voter_keyword(self, detector) -> None:
        text = "Voter ID Card\nElection Commission"
        result = detector.detect(text)
        assert result["document_type"] == "voter_id"


# ── edge cases ──────────────────────────────────────────────────────


class TestDetectorEdgeCases:
    def test_empty_text(self, detector) -> None:
        result = detector.detect("")
        assert result["status"] == "no_match"
        assert result["document_type"] is None

    def test_none_like_text(self, detector) -> None:
        result = detector.detect("   ")
        assert result["status"] == "no_match"

    def test_irrelevant_text(self, detector) -> None:
        result = detector.detect("The quick brown fox jumps over the lazy dog")
        assert result["status"] == "no_match"
        assert result["document_type"] is None

    def test_single_keyword_below_threshold(self, detector) -> None:
        """One keyword is not enough — minimum is 2."""
        result = detector.detect("aadhaar")
        assert result["status"] == "no_match"

    def test_case_insensitive(self, detector) -> None:
        text = "GOVERNMENT OF INDIA AADHAAR UIDAI"
        result = detector.detect(text)
        assert result["document_type"] == "aadhaar"

    def test_return_schema(self, detector) -> None:
        result = detector.detect("some text")
        required_keys = {
            "document_type", "document_name", "confidence",
            "matched_keywords", "status", "method",
        }
        assert required_keys.issubset(result.keys())

    def test_confidence_is_ratio(self, detector) -> None:
        text = "Aadhaar UIDAI Government of India unique identification authority"
        result = detector.detect(text)
        assert result["status"] == "success"
        assert 0.0 < result["confidence"] <= 1.0

    def test_best_match_wins(self, detector) -> None:
        """When text has keywords from multiple types, most hits wins."""
        # Aadhaar has 6 keywords, PAN has 7 — we give Aadhaar more hits
        text = (
            "Aadhaar UIDAI unique identification authority "
            "Government of India Income Tax"
        )
        result = detector.detect(text)
        assert result["document_type"] == "aadhaar"
        # Aadhaar keywords matched: aadhaar, uidai,
        # unique identification authority, government of india = 4
        # PAN matched: income tax = 1
        assert len(result["matched_keywords"]) >= 3

    def test_matched_keywords_populated(self, detector) -> None:
        text = "UIDAI Aadhaar card"
        result = detector.detect(text)
        assert len(result["matched_keywords"]) >= 2

# ── Structural Evidence Tests ────────────────────────────────────────

class TestStructuralEvidence:
    def test_aadhaar_structural_pattern(self, detector) -> None:
        # Only 1 keyword ("aadhaar") + 12-digit ID
        text = "Some random text aadhaar 1234 5678 9012"
        result = detector.detect(text)
        assert result["document_type"] == "aadhaar"
        assert result["status"] == "success"
        assert "[pattern: 12-digit ID]" in result["matched_keywords"]
        assert len(result["matched_keywords"]) == 2

    def test_pan_structural_pattern(self, detector) -> None:
        # Only 1 keyword ("pan") + PAN pattern
        text = "Random words pan ABCDE1234F stuff"
        result = detector.detect(text)
        assert result["document_type"] == "pan"
        assert result["status"] == "success"
        assert "[pattern: PAN format]" in result["matched_keywords"]

    def test_voter_id_structural_pattern(self, detector) -> None:
        # Only 1 keyword ("voter") + EPIC pattern
        text = "voter ID details ABC1234567 something"
        result = detector.detect(text)
        assert result["document_type"] == "voter_id"
        assert result["status"] == "success"
        assert "[pattern: EPIC format]" in result["matched_keywords"]

    def test_multilingual_aadhaar(self, detector) -> None:
        # Hindi keyword ("आधार") + 12-digit ID
        text = "नाम: राहुल\nआधार: 987654321098"
        result = detector.detect(text)
        assert result["document_type"] == "aadhaar"
        assert result["status"] == "success"

    def test_ocr_noise_tolerance(self, detector) -> None:
        # 1 valid keyword ("uidai") + misspelled "aadhaar" (aadhaaar) + 12-digit pattern
        text = "uidai aadhaaar 111122223333"
        result = detector.detect(text)
        assert result["document_type"] == "aadhaar"
        assert result["status"] == "success"
        assert len(result["matched_keywords"]) >= 2

    def test_ambiguous_no_guess(self, detector) -> None:
        # No clear evidence
        text = "Just some text without any identifiable documents or keywords."
        result = detector.detect(text)
        assert result["status"] == "no_match"

    def test_unsupported_document(self, detector) -> None:
        # Passport-like text
        text = "Republic of India Passport Name Surname Z1234567"
        result = detector.detect(text)
        assert result["status"] == "no_match"
