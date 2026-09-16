"""Comprehensive tests for DocumentValidator.

All test data is SYNTHETIC — no real identity numbers are used.

Tests cover:
- Required field presence
- Format validation (Aadhaar, PAN, EPIC)
- Verhoeff checksum (valid / invalid synthetic numbers)
- Date validation (valid, impossible, malformed)
- Edge cases (unknown type, empty input, None, malformed)
- Return schema consistency
"""
from __future__ import annotations

import pytest

from src.documents.validators import (
    DocumentValidator,
    verhoeff_generate,
    verhoeff_validate,
)


@pytest.fixture
def validator() -> DocumentValidator:
    return DocumentValidator()


# ── helper ──────────────────────────────────────────────────────────


def _make_fields(**kwargs: str) -> dict:
    """Build a fields dict like FieldExtractor produces."""
    return {
        name: {"value": val, "confidence": 0.7, "label": name}
        for name, val in kwargs.items()
    }


# ═══════════════════════════════════════════════════════════════════
#  VERHOEFF ALGORITHM
# ═══════════════════════════════════════════════════════════════════


class TestVerhoeffAlgorithm:
    """Test the Verhoeff checksum functions directly."""

    def test_known_valid_number(self) -> None:
        """Verhoeff validation of a known-valid synthetic number."""
        # Generate a check digit for 11-digit base, then validate 12-digit result
        base = "12345678901"
        check = verhoeff_generate(base)
        full = base + check
        assert verhoeff_validate(full) is True

    def test_known_invalid_number(self) -> None:
        """Construct a deliberately invalid Verhoeff number."""
        base = "12345678901"
        check = verhoeff_generate(base)
        valid = base + check
        # Flip the check digit to guarantee invalidity
        bad_check = "0" if check != "0" else "1"
        invalid = base + bad_check
        assert verhoeff_validate(valid) is True
        assert verhoeff_validate(invalid) is False

    def test_single_digit_error_detected(self) -> None:
        """Verhoeff detects single-digit substitution errors."""
        base = "98765432109"
        check = verhoeff_generate(base)
        valid = base + check
        assert verhoeff_validate(valid) is True
        # Alter one digit
        corrupted = "9" + "0" + valid[2:]  # change second digit
        assert verhoeff_validate(corrupted) is False

    def test_generates_single_digit(self) -> None:
        check = verhoeff_generate("12345678901")
        assert len(check) == 1
        assert check.isdigit()

    def test_validate_with_spaces(self) -> None:
        """Spaces are stripped before validation."""
        base = "12345678901"
        check = verhoeff_generate(base)
        spaced = f"{base[:4]} {base[4:8]} {base[8:]}{check}"
        assert verhoeff_validate(spaced) is True

    def test_validate_non_digit(self) -> None:
        assert verhoeff_validate("ABCDEFGHIJKL") is False

    def test_validate_empty(self) -> None:
        assert verhoeff_validate("") is False

    def test_multiple_synthetic_numbers(self) -> None:
        """Generate and validate several synthetic Verhoeff numbers."""
        for base in ["00000000000", "11111111111", "55555555555", "99999999999"]:
            check = verhoeff_generate(base)
            assert verhoeff_validate(base + check) is True


# ═══════════════════════════════════════════════════════════════════
#  GENERAL VALIDATION
# ═══════════════════════════════════════════════════════════════════


class TestValidatorGeneral:
    def test_init(self, validator) -> None:
        assert validator is not None

    def test_unknown_document_type(self, validator) -> None:
        result = validator.validate({"name": {"value": "Test"}}, "unknown_xyz")
        assert result["status"] == "error"
        assert result["checks"] == []
        assert len(result["findings"]) > 0

    def test_empty_fields(self, validator) -> None:
        result = validator.validate({}, "aadhaar")
        assert result["status"] == "error"
        assert len(result["findings"]) > 0

    def test_none_fields(self, validator) -> None:
        result = validator.validate(None, "aadhaar")
        assert result["status"] == "error"

    def test_empty_document_type(self, validator) -> None:
        result = validator.validate({"name": {"value": "Test"}}, "")
        assert result["status"] == "error"

    def test_return_schema_keys(self, validator) -> None:
        """Verify the result contains all required keys."""
        fields = _make_fields(name="Test User", aadhaar_number="1234 5678 9012")
        result = validator.validate(fields, "aadhaar")
        required_keys = {
            "checks", "valid_count", "total_count",
            "all_passed", "status", "findings", "document_type",
        }
        assert required_keys.issubset(result.keys())

    def test_backward_compatible_keys(self, validator) -> None:
        """Ensure backward compatibility with the old stub schema."""
        fields = _make_fields(name="Test User")
        result = validator.validate(fields, "aadhaar")
        # These keys were in the original stub contract
        assert "checks" in result
        assert "valid_count" in result
        assert "total_count" in result
        assert "all_passed" in result
        assert "status" in result

    def test_checks_are_list_of_dicts(self, validator) -> None:
        fields = _make_fields(name="Test User", aadhaar_number="1234 5678 9012")
        result = validator.validate(fields, "aadhaar")
        assert isinstance(result["checks"], list)
        for chk in result["checks"]:
            assert isinstance(chk, dict)
            assert "field" in chk
            assert "check_name" in chk
            assert "passed" in chk
            assert isinstance(chk["passed"], bool)
            assert "message" in chk

    def test_valid_count_matches_checks(self, validator) -> None:
        fields = _make_fields(name="Test User", aadhaar_number="1234 5678 9012")
        result = validator.validate(fields, "aadhaar")
        passed = sum(1 for c in result["checks"] if c["passed"])
        assert result["valid_count"] == passed
        assert result["total_count"] == len(result["checks"])


# ═══════════════════════════════════════════════════════════════════
#  AADHAAR VALIDATION
# ═══════════════════════════════════════════════════════════════════


class TestAadhaarValidation:
    DOC_TYPE = "aadhaar"

    def _valid_aadhaar_number(self) -> str:
        """Generate a synthetic valid Verhoeff Aadhaar number."""
        base = "12345678901"
        return base + verhoeff_generate(base)

    def test_all_fields_present(self, validator) -> None:
        num = self._valid_aadhaar_number()
        fields = _make_fields(
            aadhaar_number=num,
            name="Synthetic Person",
            dob="15/08/2002",
            gender="Male",
        )
        result = validator.validate(fields, self.DOC_TYPE)
        assert result["status"] == "success"
        assert result["all_passed"] is True

    def test_missing_required_number(self, validator) -> None:
        fields = _make_fields(name="Test Person")
        result = validator.validate(fields, self.DOC_TYPE)
        # aadhaar_number is required but missing
        missing_checks = [
            c for c in result["checks"]
            if c["field"] == "aadhaar_number" and "Required" in c["check_name"]
        ]
        assert len(missing_checks) == 1
        assert missing_checks[0]["passed"] is False

    def test_missing_required_name(self, validator) -> None:
        num = self._valid_aadhaar_number()
        fields = _make_fields(aadhaar_number=num)
        result = validator.validate(fields, self.DOC_TYPE)
        name_checks = [
            c for c in result["checks"]
            if c["field"] == "name" and "Required" in c["check_name"]
        ]
        assert len(name_checks) == 1
        assert name_checks[0]["passed"] is False

    def test_valid_format_12_digits(self, validator) -> None:
        num = self._valid_aadhaar_number()
        fields = _make_fields(aadhaar_number=num, name="Test")
        result = validator.validate(fields, self.DOC_TYPE)
        format_checks = [
            c for c in result["checks"]
            if c["field"] == "aadhaar_number" and "Format" in c["check_name"]
        ]
        assert len(format_checks) == 1
        assert format_checks[0]["passed"] is True

    def test_valid_format_with_spaces(self, validator) -> None:
        num = self._valid_aadhaar_number()
        spaced = f"{num[:4]} {num[4:8]} {num[8:]}"
        fields = _make_fields(aadhaar_number=spaced, name="Test")
        result = validator.validate(fields, self.DOC_TYPE)
        format_checks = [
            c for c in result["checks"]
            if c["field"] == "aadhaar_number" and "Format" in c["check_name"]
        ]
        assert len(format_checks) == 1
        assert format_checks[0]["passed"] is True

    def test_invalid_format_too_short(self, validator) -> None:
        fields = _make_fields(aadhaar_number="1234", name="Test")
        result = validator.validate(fields, self.DOC_TYPE)
        format_checks = [
            c for c in result["checks"]
            if c["field"] == "aadhaar_number" and "Format" in c["check_name"]
        ]
        assert len(format_checks) == 1
        assert format_checks[0]["passed"] is False

    def test_invalid_format_letters(self, validator) -> None:
        fields = _make_fields(aadhaar_number="ABCD5678EFGH", name="Test")
        result = validator.validate(fields, self.DOC_TYPE)
        format_checks = [
            c for c in result["checks"]
            if c["field"] == "aadhaar_number" and "Format" in c["check_name"]
        ]
        assert len(format_checks) == 1
        assert format_checks[0]["passed"] is False

    def test_checksum_valid(self, validator) -> None:
        num = self._valid_aadhaar_number()
        fields = _make_fields(aadhaar_number=num, name="Test")
        result = validator.validate(fields, self.DOC_TYPE)
        chk_checks = [
            c for c in result["checks"]
            if "Checksum" in c["check_name"]
        ]
        assert len(chk_checks) == 1
        assert chk_checks[0]["passed"] is True

    def test_checksum_invalid(self, validator) -> None:
        # Deliberately invalid: change last digit
        num = self._valid_aadhaar_number()
        bad = num[:-1] + ("0" if num[-1] != "0" else "1")
        fields = _make_fields(aadhaar_number=bad, name="Test")
        result = validator.validate(fields, self.DOC_TYPE)
        chk_checks = [
            c for c in result["checks"]
            if "Checksum" in c["check_name"]
        ]
        assert len(chk_checks) == 1
        assert chk_checks[0]["passed"] is False

    def test_checksum_does_not_claim_authenticity(self, validator) -> None:
        num = self._valid_aadhaar_number()
        fields = _make_fields(aadhaar_number=num, name="Test")
        result = validator.validate(fields, self.DOC_TYPE)
        chk_checks = [
            c for c in result["checks"]
            if "Checksum" in c["check_name"] and c["passed"]
        ]
        if chk_checks:
            msg = chk_checks[0]["message"]
            assert "government database" in msg.lower() or "structural" in msg.lower()


# ═══════════════════════════════════════════════════════════════════
#  PAN VALIDATION
# ═══════════════════════════════════════════════════════════════════


class TestPANValidation:
    DOC_TYPE = "pan"

    def test_valid_pan(self, validator) -> None:
        fields = _make_fields(pan_number="ABCDE1234F", name="TEST USER")
        result = validator.validate(fields, self.DOC_TYPE)
        format_checks = [
            c for c in result["checks"]
            if c["field"] == "pan_number" and "Format" in c["check_name"]
        ]
        assert len(format_checks) == 1
        assert format_checks[0]["passed"] is True

    def test_invalid_pan_all_digits(self, validator) -> None:
        fields = _make_fields(pan_number="1234567890", name="TEST")
        result = validator.validate(fields, self.DOC_TYPE)
        format_checks = [
            c for c in result["checks"]
            if c["field"] == "pan_number" and "Format" in c["check_name"]
        ]
        assert len(format_checks) == 1
        assert format_checks[0]["passed"] is False

    def test_invalid_pan_too_short(self, validator) -> None:
        fields = _make_fields(pan_number="ABC12", name="TEST")
        result = validator.validate(fields, self.DOC_TYPE)
        format_checks = [
            c for c in result["checks"]
            if c["field"] == "pan_number" and "Format" in c["check_name"]
        ]
        assert len(format_checks) == 1
        assert format_checks[0]["passed"] is False

    def test_pan_lowercase_normalized(self, validator) -> None:
        """PAN is normalized to uppercase before validation."""
        fields = _make_fields(pan_number="abcde1234f", name="TEST")
        result = validator.validate(fields, self.DOC_TYPE)
        format_checks = [
            c for c in result["checks"]
            if c["field"] == "pan_number" and "Format" in c["check_name"]
        ]
        assert len(format_checks) == 1
        assert format_checks[0]["passed"] is True

    def test_no_checksum_for_pan(self, validator) -> None:
        """PAN has no checksum algorithm configured."""
        fields = _make_fields(pan_number="ABCDE1234F", name="TEST")
        result = validator.validate(fields, self.DOC_TYPE)
        chk_checks = [
            c for c in result["checks"]
            if "Checksum" in c["check_name"]
        ]
        assert len(chk_checks) == 0

    def test_missing_required_pan_number(self, validator) -> None:
        fields = _make_fields(name="TEST USER")
        result = validator.validate(fields, self.DOC_TYPE)
        missing = [
            c for c in result["checks"]
            if c["field"] == "pan_number" and not c["passed"]
        ]
        assert len(missing) == 1


# ═══════════════════════════════════════════════════════════════════
#  VOTER ID / EPIC VALIDATION
# ═══════════════════════════════════════════════════════════════════


class TestVoterIDValidation:
    DOC_TYPE = "voter_id"

    def test_valid_epic(self, validator) -> None:
        fields = _make_fields(epic_number="ABC1234567", name="Test User")
        result = validator.validate(fields, self.DOC_TYPE)
        format_checks = [
            c for c in result["checks"]
            if c["field"] == "epic_number" and "Format" in c["check_name"]
        ]
        assert len(format_checks) == 1
        assert format_checks[0]["passed"] is True

    def test_invalid_epic_format(self, validator) -> None:
        fields = _make_fields(epic_number="12345ABCDE", name="Test User")
        result = validator.validate(fields, self.DOC_TYPE)
        format_checks = [
            c for c in result["checks"]
            if c["field"] == "epic_number" and "Format" in c["check_name"]
        ]
        assert len(format_checks) == 1
        assert format_checks[0]["passed"] is False

    def test_invalid_epic_too_short(self, validator) -> None:
        fields = _make_fields(epic_number="AB123", name="Test")
        result = validator.validate(fields, self.DOC_TYPE)
        format_checks = [
            c for c in result["checks"]
            if c["field"] == "epic_number" and "Format" in c["check_name"]
        ]
        assert len(format_checks) == 1
        assert format_checks[0]["passed"] is False

    def test_no_checksum_for_voter_id(self, validator) -> None:
        fields = _make_fields(epic_number="ABC1234567", name="Test")
        result = validator.validate(fields, self.DOC_TYPE)
        chk_checks = [
            c for c in result["checks"]
            if "Checksum" in c["check_name"]
        ]
        assert len(chk_checks) == 0


# ═══════════════════════════════════════════════════════════════════
#  DATE VALIDATION
# ═══════════════════════════════════════════════════════════════════


class TestDateValidation:
    def test_valid_date(self, validator) -> None:
        fields = _make_fields(
            aadhaar_number="123456789012", name="Test", dob="15/08/2002"
        )
        result = validator.validate(fields, "aadhaar")
        date_checks = [
            c for c in result["checks"] if "Date" in c["check_name"]
        ]
        assert len(date_checks) == 1
        assert date_checks[0]["passed"] is True

    def test_valid_date_dash_format(self, validator) -> None:
        fields = _make_fields(
            aadhaar_number="123456789012", name="Test", dob="15-08-2002"
        )
        result = validator.validate(fields, "aadhaar")
        date_checks = [
            c for c in result["checks"] if "Date" in c["check_name"]
        ]
        assert len(date_checks) == 1
        assert date_checks[0]["passed"] is True

    def test_impossible_date_month_13(self, validator) -> None:
        fields = _make_fields(
            aadhaar_number="123456789012", name="Test", dob="15/13/2002"
        )
        result = validator.validate(fields, "aadhaar")
        date_checks = [
            c for c in result["checks"] if "Date" in c["check_name"]
        ]
        assert len(date_checks) == 1
        assert date_checks[0]["passed"] is False

    def test_impossible_date_day_32(self, validator) -> None:
        fields = _make_fields(
            aadhaar_number="123456789012", name="Test", dob="32/01/2002"
        )
        result = validator.validate(fields, "aadhaar")
        date_checks = [
            c for c in result["checks"] if "Date" in c["check_name"]
        ]
        assert len(date_checks) == 1
        assert date_checks[0]["passed"] is False

    def test_malformed_date(self, validator) -> None:
        fields = _make_fields(
            aadhaar_number="123456789012", name="Test", dob="not-a-date"
        )
        result = validator.validate(fields, "aadhaar")
        date_checks = [
            c for c in result["checks"] if "Date" in c["check_name"]
        ]
        assert len(date_checks) == 1
        assert date_checks[0]["passed"] is False

    def test_implausible_year(self, validator) -> None:
        fields = _make_fields(
            aadhaar_number="123456789012", name="Test", dob="01/01/1800"
        )
        result = validator.validate(fields, "aadhaar")
        date_checks = [
            c for c in result["checks"] if "Date" in c["check_name"]
        ]
        assert len(date_checks) == 1
        assert date_checks[0]["passed"] is False

    def test_no_date_field_no_crash(self, validator) -> None:
        """If dob is not extracted, no date check should run."""
        fields = _make_fields(aadhaar_number="123456789012", name="Test")
        result = validator.validate(fields, "aadhaar")
        date_checks = [
            c for c in result["checks"] if "Date" in c["check_name"]
        ]
        assert len(date_checks) == 0


# ═══════════════════════════════════════════════════════════════════
#  EDGE CASES
# ═══════════════════════════════════════════════════════════════════


class TestValidatorEdgeCases:
    def test_field_with_empty_value(self, validator) -> None:
        """Field exists but value is empty string."""
        fields = {"aadhaar_number": {"value": "", "confidence": 0.7, "label": "x"}}
        result = validator.validate(fields, "aadhaar")
        # Should not crash
        assert "status" in result

    def test_field_as_raw_string(self, validator) -> None:
        """If field value is a plain string instead of dict."""
        fields = {"name": "Test User", "aadhaar_number": "123456789012"}
        result = validator.validate(fields, "aadhaar")
        assert "status" in result
        assert len(result["checks"]) > 0

    def test_findings_are_list_of_strings(self, validator) -> None:
        fields = _make_fields(name="Test", aadhaar_number="123456789012")
        result = validator.validate(fields, "aadhaar")
        assert isinstance(result["findings"], list)
        for f in result["findings"]:
            assert isinstance(f, str)

    def test_status_values(self, validator) -> None:
        """Status must be one of the documented values."""
        fields = _make_fields(name="Test", aadhaar_number="123456789012")
        result = validator.validate(fields, "aadhaar")
        assert result["status"] in ("success", "partial", "failed", "error")
