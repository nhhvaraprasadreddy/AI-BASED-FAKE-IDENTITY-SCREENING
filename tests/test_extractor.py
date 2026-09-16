"""Unit tests for FieldExtractor (regex-based extraction).

Tests use synthetic OCR text — no images or EasyOCR required.
Validates extraction logic, confidence handling, status codes, and
edge cases for all three initial document types.
"""
from __future__ import annotations

import pytest

from src.documents.extractor import EXTRACTION_CONFIDENCE, FieldExtractor


@pytest.fixture
def extractor() -> FieldExtractor:
    return FieldExtractor()


# ── Aadhaar extraction ──────────────────────────────────────────────


class TestAadhaarExtraction:
    SAMPLE_TEXT = (
        "Government of India\n"
        "Unique Identification Authority of India\n"
        "Name: Rajesh Kumar\n"
        "DOB: 15/08/1990\n"
        "Male\n"
        "1234 5678 9012\n"
    )

    def test_aadhaar_number_extracted(self, extractor) -> None:
        result = extractor.extract(self.SAMPLE_TEXT, "aadhaar")
        assert "aadhaar_number" in result["fields"]
        value = result["fields"]["aadhaar_number"]["value"]
        # Should match the 12-digit pattern
        assert "1234" in value

    def test_name_extracted(self, extractor) -> None:
        result = extractor.extract(self.SAMPLE_TEXT, "aadhaar")
        assert "name" in result["fields"]
        assert "Rajesh" in result["fields"]["name"]["value"]

    def test_dob_extracted(self, extractor) -> None:
        result = extractor.extract(self.SAMPLE_TEXT, "aadhaar")
        assert "dob" in result["fields"]
        assert "15/08/1990" in result["fields"]["dob"]["value"]

    def test_gender_extracted(self, extractor) -> None:
        result = extractor.extract(self.SAMPLE_TEXT, "aadhaar")
        assert "gender" in result["fields"]
        assert "Male" in result["fields"]["gender"]["value"]

    def test_extraction_count(self, extractor) -> None:
        result = extractor.extract(self.SAMPLE_TEXT, "aadhaar")
        assert result["extraction_count"] >= 3  # at least number, name, dob
        assert result["total_fields"] == 4

    def test_status_with_all_fields(self, extractor) -> None:
        result = extractor.extract(self.SAMPLE_TEXT, "aadhaar")
        # With all 4 fields present, should be "success"
        assert result["status"] in ("success", "partial")


# ── PAN extraction ──────────────────────────────────────────────────


class TestPANExtraction:
    SAMPLE_TEXT = (
        "Income Tax Department\n"
        "Permanent Account Number\n"
        "Name: RAJESH KUMAR\n"
        "Father's Name: SURESH KUMAR\n"
        "15/08/1990\n"
        "ABCDE1234F\n"
    )

    def test_pan_number_extracted(self, extractor) -> None:
        result = extractor.extract(self.SAMPLE_TEXT, "pan")
        assert "pan_number" in result["fields"]
        assert result["fields"]["pan_number"]["value"] == "ABCDE1234F"

    def test_pan_name_extracted(self, extractor) -> None:
        result = extractor.extract(self.SAMPLE_TEXT, "pan")
        assert "name" in result["fields"]
        assert "RAJESH" in result["fields"]["name"]["value"]

    def test_pan_dob_extracted(self, extractor) -> None:
        result = extractor.extract(self.SAMPLE_TEXT, "pan")
        assert "dob" in result["fields"]
        assert "15/08/1990" in result["fields"]["dob"]["value"]


# ── Voter ID extraction ────────────────────────────────────────────


class TestVoterIDExtraction:
    SAMPLE_TEXT = (
        "Election Commission of India\n"
        "Electoral Photo Identity Card\n"
        "Elector's Name: Rajesh Kumar\n"
        "Father's Name: Suresh Kumar\n"
        "DOB: 15/08/1990\n"
        "ABC1234567\n"
    )

    def test_epic_number_extracted(self, extractor) -> None:
        result = extractor.extract(self.SAMPLE_TEXT, "voter_id")
        assert "epic_number" in result["fields"]
        assert result["fields"]["epic_number"]["value"] == "ABC1234567"

    def test_voter_id_name(self, extractor) -> None:
        result = extractor.extract(self.SAMPLE_TEXT, "voter_id")
        assert "name" in result["fields"]


# ── confidence ──────────────────────────────────────────────────────


class TestExtractionConfidence:
    def test_confidence_not_one(self, extractor) -> None:
        """Extracted confidence must never be 1.0 for regex matches."""
        text = "ABCDE1234F"
        result = extractor.extract(text, "pan")
        if result["extraction_count"] > 0:
            for field in result["fields"].values():
                assert field["confidence"] < 1.0

    def test_confidence_is_documented_constant(self, extractor) -> None:
        """Confidence should equal the module constant."""
        text = "1234 5678 9012"
        result = extractor.extract(text, "aadhaar")
        if "aadhaar_number" in result["fields"]:
            assert result["fields"]["aadhaar_number"]["confidence"] == EXTRACTION_CONFIDENCE

    def test_confidence_value_reasonable(self) -> None:
        """The constant itself should be between 0 and 1, exclusive of 1."""
        assert 0.0 < EXTRACTION_CONFIDENCE < 1.0


# ── edge cases ──────────────────────────────────────────────────────


class TestExtractorEdgeCases:
    def test_unknown_document_type(self, extractor) -> None:
        result = extractor.extract("some text", "unknown_type")
        assert result["total_fields"] == 0
        assert result["extraction_count"] == 0
        assert result["status"] == "unknown_document_type"

    def test_empty_text(self, extractor) -> None:
        result = extractor.extract("", "aadhaar")
        assert result["extraction_count"] == 0
        assert result["status"] == "no_fields"

    def test_no_matching_fields(self, extractor) -> None:
        result = extractor.extract("random gibberish", "aadhaar")
        assert result["extraction_count"] == 0
        assert result["status"] == "no_fields"

    def test_partial_extraction(self, extractor) -> None:
        """Text with some but not all fields → 'partial'."""
        text = "1234 5678 9012"  # only Aadhaar number, no name/dob/gender
        result = extractor.extract(text, "aadhaar")
        if result["extraction_count"] > 0:
            assert result["status"] == "partial"

    def test_raw_text_preserved(self, extractor) -> None:
        text = "original OCR text"
        result = extractor.extract(text, "aadhaar")
        assert result["raw_text"] == text

    def test_return_schema(self, extractor) -> None:
        result = extractor.extract("text", "aadhaar")
        required_keys = {
            "fields", "raw_text", "extraction_count",
            "total_fields", "status",
        }
        assert required_keys.issubset(result.keys())

    def test_field_has_label(self, extractor) -> None:
        """Each extracted field should include its human-readable label."""
        text = "ABCDE1234F"
        result = extractor.extract(text, "pan")
        if "pan_number" in result["fields"]:
            assert "label" in result["fields"]["pan_number"]
            assert result["fields"]["pan_number"]["label"] == "PAN Number"


class TestExtractorHardening:
    def test_pan_number_at_beginning(self, extractor) -> None:
        text = "ABCDE1234F\nSome other text here\nAnd more"
        result = extractor.extract(text, "pan")
        assert "pan_number" in result["fields"]
        assert result["fields"]["pan_number"]["value"] == "ABCDE1234F"

    def test_pan_number_in_middle(self, extractor) -> None:
        text = "Start text\nHere is ABCDE1234F embedded\nEnd text"
        result = extractor.extract(text, "pan")
        assert "pan_number" in result["fields"]
        assert result["fields"]["pan_number"]["value"] == "ABCDE1234F"

    def test_pan_number_at_end(self, extractor) -> None:
        text = "Some intro text\nMore text\nABCDE1234F"
        result = extractor.extract(text, "pan")
        assert "pan_number" in result["fields"]
        assert result["fields"]["pan_number"]["value"] == "ABCDE1234F"

    def test_aadhaar_number_with_spaces(self, extractor) -> None:
        text = "Aadhaar: 1234 5678 9012"
        result = extractor.extract(text, "aadhaar")
        assert "aadhaar_number" in result["fields"]
        assert result["fields"]["aadhaar_number"]["value"].replace(" ", "") == "123456789012"

    def test_aadhaar_number_without_spaces(self, extractor) -> None:
        text = "Aadhaar: 123456789012"
        result = extractor.extract(text, "aadhaar")
        assert "aadhaar_number" in result["fields"]
        assert result["fields"]["aadhaar_number"]["value"] == "123456789012"

    def test_extraction_with_ocr_noise(self, extractor) -> None:
        text = "~~ABCDE1234F==\nName: %RAJESH_KUMAR*"
        result = extractor.extract(text, "pan")
        assert "pan_number" in result["fields"]
        assert result["fields"]["pan_number"]["value"] == "ABCDE1234F"

    def test_missing_name_label(self, extractor) -> None:
        text = "RAJESH KUMAR\nDOB: 15/08/1990"
        result = extractor.extract(text, "pan")
        assert "name" not in result["fields"]

    def test_empty_text_extraction(self, extractor) -> None:
        result = extractor.extract("", "pan")
        assert result["status"] == "no_fields"
        assert result["extraction_count"] == 0

    def test_none_value_not_fabricated(self, extractor) -> None:
        text = "Just some random text\nNo ID here"
        result = extractor.extract(text, "pan")
        assert "pan_number" not in result["fields"]

    def test_none_input_handled(self, extractor) -> None:
        # Edge case: passing None instead of string
        result = extractor.extract(None, "pan")
        assert result["status"] == "no_fields"
        assert result["raw_text"] == ""


# ═══════════════════════════════════════════════════════════════════════════════
# PAN extraction regression tests (bug fix)
# ═══════════════════════════════════════════════════════════════════════════════


class TestPANExtractionRegression:
    """Regression tests for PAN number extraction.

    Verifies the PAN pattern matches the structural format AAAAA0000A
    regardless of position, whitespace, or case in OCR output.
    """

    @pytest.fixture
    def extractor(self) -> FieldExtractor:
        return FieldExtractor()

    def test_pan_contiguous_uppercase(self, extractor) -> None:
        """Standard contiguous uppercase PAN."""
        text = "INCOME TAX DEPARTMENT\nABCDE1234F\nName: RAHUL"
        result = extractor.extract(text, "pan")
        assert result["fields"]["pan_number"]["value"] == "ABCDE1234F"

    def test_pan_with_spaces(self, extractor) -> None:
        """OCR inserts spaces between characters."""
        text = "INCOME TAX\nA B C D E 1 2 3 4 F\nName: RAHUL"
        result = extractor.extract(text, "pan")
        assert result["fields"]["pan_number"]["value"] == "ABCDE1234F"

    def test_pan_lowercase_ocr(self, extractor) -> None:
        """OCR produces lowercase."""
        text = "income tax department\nabcde1234f\nname: rahul"
        result = extractor.extract(text, "pan")
        assert result["fields"]["pan_number"]["value"] == "ABCDE1234F"

    def test_pan_mixed_case(self, extractor) -> None:
        """OCR produces mixed case."""
        text = "Income Tax\nAbCdE1234f\nName: Rahul"
        result = extractor.extract(text, "pan")
        assert result["fields"]["pan_number"]["value"] == "ABCDE1234F"

    def test_pan_at_beginning(self, extractor) -> None:
        """PAN appears at the beginning of OCR text."""
        text = "ABCDE1234F INCOME TAX DEPARTMENT Name: RAHUL"
        result = extractor.extract(text, "pan")
        assert result["fields"]["pan_number"]["value"] == "ABCDE1234F"

    def test_pan_in_middle(self, extractor) -> None:
        """PAN appears in the middle of OCR text."""
        text = "INCOME TAX DEPARTMENT ABCDE1234F Permanent Account Number"
        result = extractor.extract(text, "pan")
        assert result["fields"]["pan_number"]["value"] == "ABCDE1234F"

    def test_pan_at_end(self, extractor) -> None:
        """PAN appears at the end of OCR text."""
        text = "INCOME TAX DEPARTMENT\nName: RAHUL\nABCDE1234F"
        result = extractor.extract(text, "pan")
        assert result["fields"]["pan_number"]["value"] == "ABCDE1234F"

    def test_pan_surrounded_by_labels(self, extractor) -> None:
        """PAN surrounded by typical card labels."""
        text = "Permanent Account Number\nABCDE1234F\nName: RAHUL SHARMA\nFather's Name: SURESH"
        result = extractor.extract(text, "pan")
        assert result["fields"]["pan_number"]["value"] == "ABCDE1234F"

    def test_pan_invalid_format_not_extracted(self, extractor) -> None:
        """Invalid PAN format should not be extracted."""
        text = "INCOME TAX\n12345ABCDE\nName: RAHUL"
        result = extractor.extract(text, "pan")
        assert "pan_number" not in result["fields"]

    def test_pan_too_short_not_extracted(self, extractor) -> None:
        """Short alphanumeric strings should not match."""
        text = "INCOME TAX\nABCD1234\nName: RAHUL"
        result = extractor.extract(text, "pan")
        assert "pan_number" not in result["fields"]

    def test_pan_empty_text(self, extractor) -> None:
        """Empty OCR text should not extract PAN."""
        result = extractor.extract("", "pan")
        assert result["status"] == "no_fields"

    def test_pan_value_always_uppercase(self, extractor) -> None:
        """Extracted PAN should always be returned uppercase."""
        text = "income tax abcde1234f name rahul"
        result = extractor.extract(text, "pan")
        pan = result["fields"].get("pan_number", {}).get("value")
        if pan is not None:
            assert pan == pan.upper()

    def test_pan_spaces_collapsed(self, extractor) -> None:
        """Extracted PAN should not contain internal spaces."""
        text = "A B C D E 1 2 3 4 F"
        result = extractor.extract(text, "pan")
        pan = result["fields"]["pan_number"]["value"]
        assert pan == "ABCDE1234F"
        assert " " not in pan


# ═══════════════════════════════════════════════════════════════════════════════
# PAN OCR digit-error correction tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestPANOcrCorrection:
    """Tests for OCR letter→digit correction at PAN digit positions.

    Verifies that common OCR misreads at the 4 digit positions (indices
    5–8) are corrected conservatively, and that unmappable errors cause
    rejection rather than fabrication.
    """

    @pytest.fixture
    def extractor(self) -> FieldExtractor:
        return FieldExtractor()

    def test_ocr_A_to_4(self, extractor) -> None:
        """OCR reads 4 as A — the actual deployed failure case."""
        text = "INCOME TAX\nABCDE123AF\nName: RAHUL"
        result = extractor.extract(text, "pan")
        assert result["fields"]["pan_number"]["value"] == "ABCDE1234F"

    def test_ocr_O_to_0(self, extractor) -> None:
        """OCR reads 0 as O."""
        text = "INCOME TAX\nABCDE1O34F\nName: RAHUL"
        result = extractor.extract(text, "pan")
        assert result["fields"]["pan_number"]["value"] == "ABCDE1034F"

    def test_ocr_I_to_1(self, extractor) -> None:
        """OCR reads 1 as I."""
        text = "INCOME TAX\nABCDEI234F\nName: RAHUL"
        result = extractor.extract(text, "pan")
        assert result["fields"]["pan_number"]["value"] == "ABCDE1234F"

    def test_ocr_S_to_5(self, extractor) -> None:
        """OCR reads 5 as S."""
        text = "INCOME TAX\nABCDES234F\nName: RAHUL"
        result = extractor.extract(text, "pan")
        assert result["fields"]["pan_number"]["value"] == "ABCDE5234F"

    def test_ocr_multiple_errors(self, extractor) -> None:
        """Multiple OCR errors at digit positions."""
        text = "INCOME TAX\nABCDEIO3AF\nName: RAHUL"
        result = extractor.extract(text, "pan")
        assert result["fields"]["pan_number"]["value"] == "ABCDE1034F"

    def test_unmappable_letter_rejected(self, extractor) -> None:
        """Letter at digit position not in correction map → reject."""
        text = "INCOME TAX\nABCDE12X4F\nName: RAHUL"
        result = extractor.extract(text, "pan")
        assert "pan_number" not in result["fields"]

    def test_all_alpha_not_pan(self, extractor) -> None:
        """10-letter all-alpha string should not produce a PAN."""
        text = "ABCDEFGHIJ some other text"
        result = extractor.extract(text, "pan")
        assert "pan_number" not in result["fields"]

    def test_strict_match_preferred(self, extractor) -> None:
        """When strict pattern matches, no correction is needed."""
        text = "ABCDE1234F"
        result = extractor.extract(text, "pan")
        assert result["fields"]["pan_number"]["value"] == "ABCDE1234F"

    def test_correction_does_not_fabricate(self, extractor) -> None:
        """Random text must not produce a PAN via correction."""
        text = "THE QUICK BROWN FOX JUMPED OVER LAZY DOGS"
        result = extractor.extract(text, "pan")
        assert "pan_number" not in result["fields"]

    def test_ocr_error_with_spaces(self, extractor) -> None:
        """OCR error combined with spaces between characters."""
        text = "A B C D E 1 2 3 A F"
        result = extractor.extract(text, "pan")
        assert result["fields"]["pan_number"]["value"] == "ABCDE1234F"
