"""Document and field validation.

Validates extracted identity fields against structural format rules
and document-specific checks (required fields, format patterns,
checksums, date validity).

**This is rule-based structural validation — NOT external government
verification.**  A valid checksum or format match only confirms that
the value is structurally consistent with the expected pattern.  It
does NOT prove the document is genuine, that the number exists in a
government database, or that it belongs to the person shown.

Validation results are deterministic indicators, not probabilities.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from src.config import DOCUMENT_TYPES

logger = logging.getLogger(__name__)

# ── Verhoeff algorithm tables ───────────────────────────────────────
# Used for Aadhaar number checksum validation.
# Reference: https://en.wikipedia.org/wiki/Verhoeff_algorithm

_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

_VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def verhoeff_validate(number: str) -> bool:
    """Validate a number string against the Verhoeff checksum.

    Args:
        number: Digit string (spaces are stripped automatically).

    Returns:
        True if the checksum is valid, False otherwise.
    """
    digits = number.replace(" ", "")
    if not digits.isdigit():
        return False
    c = 0
    for i, digit in enumerate(reversed(digits)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(digit)]]
    return c == 0


def verhoeff_generate(number: str) -> str:
    """Generate Verhoeff check digit for a number string.

    Args:
        number: Digit string without the check digit.

    Returns:
        The single check digit character.
    """
    digits = number.replace(" ", "")
    c = 0
    for i, digit in enumerate(reversed(digits)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[(i + 1) % 8][int(digit)]]
    return str(_VERHOEFF_INV[c])


class DocumentValidator:
    """Validates extracted fields against document format rules.

    Runs independent checks:
    - Required field presence
    - Field format (regex-based, config-driven)
    - Aadhaar Verhoeff checksum (structural only)
    - Date validity

    Results are deterministic indicators, not probabilities.
    """

    def __init__(self) -> None:
        """Initialize with document type definitions from config."""
        self.document_types = DOCUMENT_TYPES
        logger.info("DocumentValidator initialized")

    def validate(self, fields: dict, document_type: str) -> dict:
        """Validate extracted fields for a given document type.

        Args:
            fields: Dict of extracted fields from FieldExtractor.
                    Each value is ``{value, confidence, label}``.
            document_type: Key from ``DOCUMENT_TYPES``.

        Returns:
            dict with keys:
                - checks (list[dict]): Validation results, each with:
                    'field', 'check_name', 'passed' (bool), 'message',
                    'severity'
                - valid_count (int): Number of passed checks
                - total_count (int): Total number of checks run
                - all_passed (bool): True if every check passed
                - status (str): 'success', 'partial', 'failed', 'error'
                - findings (list[str]): Human-readable summary points
                - document_type (str): The validated document type
        """
        doc_config = self.document_types.get(document_type)

        if doc_config is None:
            logger.warning(
                "Unknown document type '%s' — cannot validate",
                document_type,
            )
            return self._result(
                checks=[],
                findings=["Unknown document type — no validation performed."],
                status="error",
                document_type=document_type,
            )

        if not fields:
            logger.info("No fields to validate for '%s'", document_type)
            return self._result(
                checks=[],
                findings=["No extracted fields to validate."],
                status="error",
                document_type=document_type,
            )

        checks: list[dict] = []
        findings: list[str] = []

        field_defs: dict[str, dict[str, Any]] = doc_config.get("fields", {})

        # ── 1. Required-field presence ───────────────────────────────
        self._check_required_fields(field_defs, fields, checks, findings)

        # ── 2. Format validation ─────────────────────────────────────
        self._check_field_formats(
            field_defs, fields, checks, findings, document_type
        )

        # ── 3. Checksum validation (Aadhaar Verhoeff) ────────────────
        self._check_checksum(doc_config, fields, checks, findings)

        # ── 4. Date validation ───────────────────────────────────────
        self._check_dates(field_defs, fields, checks, findings)

        return self._result(
            checks=checks,
            findings=findings,
            status=self._determine_status(checks),
            document_type=document_type,
        )

    # ── check implementations ────────────────────────────────────────

    def _check_required_fields(
        self,
        field_defs: dict,
        fields: dict,
        checks: list,
        findings: list,
    ) -> None:
        """Check that all required fields are present."""
        required = [
            (name, cfg)
            for name, cfg in field_defs.items()
            if cfg.get("required", False)
        ]
        if not required:
            return

        all_present = True
        for field_name, cfg in required:
            label = cfg.get("label", field_name)
            present = field_name in fields and self._has_value(fields[field_name])
            checks.append({
                "field": field_name,
                "check_name": f"Required: {label}",
                "passed": present,
                "message": (
                    f"{label} is present."
                    if present
                    else f"{label} is missing — expected for this document type."
                ),
                "severity": "error" if not present else "info",
            })
            if not present:
                all_present = False

        if all_present:
            findings.append("All required fields were extracted.")
        else:
            missing = [
                cfg.get("label", name)
                for name, cfg in required
                if name not in fields or not self._has_value(fields[name])
            ]
            findings.append(
                f"Missing required field(s): {', '.join(missing)}. "
                "This may indicate OCR issues or an unrecognised layout."
            )

    def _check_field_formats(
        self,
        field_defs: dict,
        fields: dict,
        checks: list,
        findings: list,
        document_type: str,
    ) -> None:
        """Validate extracted field values against configured patterns."""
        for field_name, cfg in field_defs.items():
            if field_name not in fields:
                continue
            value = self._get_value(fields[field_name])
            if not value:
                continue

            # Skip name and date fields for regex format checks —
            # names vary widely and dates get their own validator
            if field_name in ("name", "father_name", "dob"):
                continue

            pattern = cfg.get("pattern")
            if not pattern:
                continue

            label = cfg.get("label", field_name)
            fmt_desc = cfg.get("format_description", "")

            # Normalize value for matching
            normalized = self._normalize_for_format(value, document_type, field_name)

            try:
                match = re.fullmatch(pattern, normalized)
                passed = match is not None
            except re.error:
                passed = False

            checks.append({
                "field": field_name,
                "check_name": f"Format: {label}",
                "passed": passed,
                "message": (
                    f"{label} format is structurally valid ({fmt_desc})."
                    if passed
                    else f"{label} format does not match expected pattern ({fmt_desc}). "
                         f"This may be due to OCR errors or an invalid value."
                ),
                "severity": "warning" if not passed else "info",
            })

            if passed:
                findings.append(
                    f"{label} format is structurally valid."
                )
            else:
                findings.append(
                    f"{label} format does not match expected pattern. "
                    "Potential validation issue — human review recommended."
                )

    def _check_checksum(
        self,
        doc_config: dict,
        fields: dict,
        checks: list,
        findings: list,
    ) -> None:
        """Run checksum validation if configured (e.g. Verhoeff for Aadhaar)."""
        algorithm = doc_config.get("checksum_algorithm")
        checksum_field = doc_config.get("checksum_field")

        if not algorithm or not checksum_field:
            return

        if checksum_field not in fields:
            return

        value = self._get_value(fields[checksum_field])
        if not value:
            return

        label = doc_config.get("fields", {}).get(
            checksum_field, {}
        ).get("label", checksum_field)

        if algorithm == "verhoeff":
            digits = value.replace(" ", "")
            if not digits.isdigit() or len(digits) != 12:
                checks.append({
                    "field": checksum_field,
                    "check_name": f"Checksum: {label}",
                    "passed": False,
                    "message": (
                        f"{label} must be exactly 12 digits for checksum "
                        f"validation. Got {len(digits)} character(s)."
                    ),
                    "severity": "warning",
                })
                findings.append(
                    f"{label} could not be validated — unexpected length."
                )
                return

            passed = verhoeff_validate(digits)
            checks.append({
                "field": checksum_field,
                "check_name": f"Checksum: {label}",
                "passed": passed,
                "message": (
                    f"{label} checksum (Verhoeff) is structurally valid. "
                    "This confirms the number format, not that it exists "
                    "in any government database."
                    if passed
                    else f"{label} checksum (Verhoeff) validation failed. "
                         "This is a suspicious indicator — human review recommended."
                ),
                "severity": "warning" if not passed else "info",
            })
            if passed:
                findings.append(
                    f"{label} Verhoeff checksum is structurally valid "
                    "(structural check only — not external verification)."
                )
            else:
                findings.append(
                    f"{label} Verhoeff checksum failed — "
                    "suspicious indicator, human review recommended."
                )
        else:
            logger.warning("Unknown checksum algorithm: %s", algorithm)

    def _check_dates(
        self,
        field_defs: dict,
        fields: dict,
        checks: list,
        findings: list,
    ) -> None:
        """Validate date fields for format and plausibility."""
        for field_name, cfg in field_defs.items():
            if field_name != "dob":
                continue
            if field_name not in fields:
                continue

            value = self._get_value(fields[field_name])
            if not value:
                continue

            label = cfg.get("label", field_name)
            passed, message = self._validate_date(value, label)

            checks.append({
                "field": field_name,
                "check_name": f"Date: {label}",
                "passed": passed,
                "message": message,
                "severity": "warning" if not passed else "info",
            })

            findings.append(message)

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _has_value(field: Any) -> bool:
        """Check if a field dict contains a non-empty value."""
        if isinstance(field, dict):
            val = field.get("value", "")
            return bool(val and str(val).strip())
        return bool(field and str(field).strip())

    @staticmethod
    def _get_value(field: Any) -> str:
        """Extract the string value from a field dict or raw value."""
        if isinstance(field, dict):
            return str(field.get("value", "")).strip()
        return str(field).strip() if field else ""

    @staticmethod
    def _normalize_for_format(
        value: str, document_type: str, field_name: str
    ) -> str:
        """Normalize a value before format validation.

        For ID numbers, strip spaces so ``1234 5678 9012`` matches
        ``\\d{12}`` patterns.  For PAN, uppercase.
        """
        if field_name in ("aadhaar_number",):
            return value.replace(" ", "")
        if field_name in ("pan_number",):
            return value.replace(" ", "").upper()
        if field_name in ("epic_number",):
            return value.replace(" ", "").upper()
        return value.strip()

    @staticmethod
    def _validate_date(value: str, label: str) -> tuple[bool, str]:
        """Validate a date string for format and plausibility.

        Accepts DD/MM/YYYY or DD-MM-YYYY.
        """
        value = value.strip()
        # Try common Indian date formats
        for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
            try:
                dt = datetime.strptime(value, fmt)
                # Plausibility: year between 1900 and current year
                current_year = datetime.now().year
                if dt.year < 1900 or dt.year > current_year:
                    return (
                        False,
                        f"{label} has an implausible year ({dt.year}). "
                        "Expected between 1900 and the current year.",
                    )
                return True, f"{label} is a valid date ({value})."
            except ValueError:
                continue

        return (
            False,
            f"{label} format is not recognised ({value}). "
            "Expected DD/MM/YYYY or DD-MM-YYYY.",
        )

    @staticmethod
    def _determine_status(checks: list[dict]) -> str:
        """Classify validation outcome from check results."""
        if not checks:
            return "error"
        passed = sum(1 for c in checks if c.get("passed"))
        total = len(checks)
        if passed == total:
            return "success"
        if passed == 0:
            return "failed"
        return "partial"

    @staticmethod
    def _result(
        *,
        checks: list[dict],
        findings: list[str],
        status: str,
        document_type: str,
    ) -> dict:
        """Build the standard validation result dict."""
        passed = sum(1 for c in checks if c.get("passed"))
        total = len(checks)
        return {
            "checks": checks,
            "valid_count": passed,
            "total_count": total,
            "all_passed": passed == total and total > 0,
            "status": status,
            "findings": findings,
            "document_type": document_type,
        }
