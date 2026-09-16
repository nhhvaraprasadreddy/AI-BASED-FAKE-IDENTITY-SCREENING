"""Regex-based identity-field extraction from OCR text.

Applies the regex patterns defined in ``src.config.DOCUMENT_TYPES`` to
extract structured fields (names, ID numbers, dates, etc.) from raw
OCR output.

Extraction confidence
---------------------
A successful regex match does **not** prove the extracted value is
correct — OCR text may contain errors and the regex may capture a
false positive.  Therefore, extracted fields are assigned a heuristic
confidence of ``EXTRACTION_CONFIDENCE`` (default 0.7) rather than
1.0.  This value is **not** a calibrated probability.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from src.config import DOCUMENT_TYPES

logger = logging.getLogger(__name__)

# Heuristic confidence assigned to every regex extraction.
# Rationale: a regex match confirms the *pattern* was found in OCR text,
# but OCR noise, misreads, and regex over-matching mean the extracted
# value may still be incorrect.  0.7 signals "likely but not certain".
# This is NOT a calibrated probability.
EXTRACTION_CONFIDENCE: float = 0.7


class FieldExtractor:
    """Extracts identity fields from OCR text using regex patterns.

    For each field defined in the matching ``DOCUMENT_TYPES`` entry the
    extractor compiles the associated regex, searches the OCR text, and
    returns the first match (capturing-group 1 when present, otherwise
    group 0).
    """

    def __init__(self) -> None:
        """Initialize with document type definitions from config."""
        self.document_types = DOCUMENT_TYPES
        logger.info("FieldExtractor initialized")

    # ── public API ───────────────────────────────────────────────────

    def extract(self, ocr_text: str, document_type: str) -> dict:
        """Extract fields from *ocr_text* for a given *document_type*.

        Args:
            ocr_text: Raw text from the OCR engine.
            document_type: Key from ``DOCUMENT_TYPES`` (e.g. ``'aadhaar'``).

        Returns:
            dict with keys:
                - **fields** (*dict*): Mapping of field-name →
                  ``{value, confidence, label}``.
                - **raw_text** (*str*): The original OCR text.
                - **extraction_count** (*int*): Fields successfully
                  extracted.
                - **total_fields** (*int*): Fields defined for this
                  document type.
                - **status** (*str*): ``"success"`` | ``"partial"``
                  | ``"no_fields"`` | ``"unknown_document_type"``.
        """
        doc_config = self.document_types.get(document_type)

        # ── unknown document type ────────────────────────────────────
        if doc_config is None:
            logger.warning(
                "Unknown document type '%s' — no fields to extract",
                document_type,
            )
            return {
                "fields": {},
                "raw_text": ocr_text,
                "extraction_count": 0,
                "total_fields": 0,
                "status": "unknown_document_type",
                "message": f"Unknown document type: {document_type}",
            }

        field_defs: dict[str, dict[str, Any]] = doc_config.get("fields", {})
        total = len(field_defs)

        if not ocr_text or not ocr_text.strip():
            logger.info("Empty OCR text — nothing to extract")
            return {
                "fields": {},
                "raw_text": ocr_text or "",
                "extraction_count": 0,
                "total_fields": total,
                "status": "no_fields",
                "message": "Empty OCR text provided.",
            }

        # ── run extraction ───────────────────────────────────────────
        fields: dict[str, dict] = {}

        for field_name, field_cfg in field_defs.items():
            pattern = field_cfg.get("pattern")
            if not pattern:
                continue

            value = self._extract_field(pattern, ocr_text)

            # PAN-specific fallback: if strict matching fails, look for a
            # PAN-like token and apply position-aware OCR correction.
            if value is None and field_name == "pan_number":
                _PAN_RELAXED = r"\b[A-Z]{5}[A-Z0-9]{4}[A-Z]\b"

                try:
                    # Pass 1: contiguous PAN-like token.
                    for m in re.finditer(_PAN_RELAXED, ocr_text, re.IGNORECASE):
                        candidate = m.group(0).upper()
                        corrected = self._correct_pan_digits(candidate)

                        if corrected is not None:
                            value = corrected
                            break

                    # Pass 2: OCR may insert spaces between every character,
                    # e.g. "A B C D E 1 2 3 A F".
                    if value is None:
                        _PAN_SPACED = (
                            r"\b([A-Z])\s+([A-Z])\s+([A-Z])\s+([A-Z])\s+([A-Z])"
                            r"\s+([A-Z0-9])\s+([A-Z0-9])\s+([A-Z0-9])"
                            r"\s+([A-Z0-9])\s+([A-Z])\b"
                        )

                        for m in re.finditer(
                            _PAN_SPACED, ocr_text, re.IGNORECASE
                        ):
                            candidate = "".join(m.groups()).upper()
                            corrected = self._correct_pan_digits(candidate)

                            if corrected is not None:
                                value = corrected
                                break

                except re.error:
                    pass

            if value is not None:
                # Normalize ID-number fields: collapse internal whitespace
                # and uppercase.  OCR often inserts spaces between characters
                # of printed IDs (e.g. "A B C D E 1 2 3 4 F" for PAN).
                if field_name.endswith("_number"):
                    value = re.sub(r"\s+", "", value).upper()

                # PAN-specific: correct common OCR letter→digit errors
                # at the 4 digit positions (indices 5–8).  If a position
                # cannot be mapped to a digit, reject the match entirely
                # to avoid fabricating a PAN value.
                if field_name == "pan_number" and len(value) == 10:
                    value = self._correct_pan_digits(value)
                    if value is None:
                        continue  # reject — uncorrectable OCR error

                fields[field_name] = {
                    "value": value,
                    "confidence": EXTRACTION_CONFIDENCE,
                    "label": field_cfg.get("label", field_name),
                }

        count = len(fields)
        status = self._determine_status(count, total)

        logger.info(
            "Extraction for '%s': %d / %d fields (%s)",
            document_type,
            count,
            total,
            status,
        )

        return {
            "fields": fields,
            "raw_text": ocr_text,
            "extraction_count": count,
            "total_fields": total,
            "status": status,
        }

    # ── internal helpers ─────────────────────────────────────────────

    @staticmethod
    def _extract_field(pattern: str, text: str) -> str | None:
        """Return the first match of *pattern* in *text*, or ``None``.

        If the regex contains a capturing group, group(1) is returned;
        otherwise group(0) (the full match) is used.  Leading/trailing
        whitespace is stripped.
        """
        try:
            match = re.search(pattern, text, re.IGNORECASE)
        except re.error as exc:
            logger.warning("Invalid regex pattern '%s': %s", pattern, exc)
            return None

        if match is None:
            return None

        # Prefer first capturing group when available
        if match.lastindex and match.lastindex >= 1:
            value = match.group(1)
        else:
            value = match.group(0)

        return value.strip() if value else None

    @staticmethod
    def _correct_pan_digits(pan: str) -> str | None:
        """Correct common OCR letter→digit errors at PAN digit positions.

        PAN format: AAAAA9999A — positions 5–8 must be digits.
        OCR sometimes reads digits as visually similar letters
        (e.g. 4→A, 0→O, 1→I).  This method applies a conservative
        map **only** at the 4 digit positions.

        Returns the corrected PAN, or ``None`` if any digit position
        contains a letter that cannot be safely mapped to a digit.
        This prevents fabrication of PAN values from random text.
        """
        # Conservative map: letter → digit for visually similar glyphs.
        # Only characters with a clear visual resemblance are included.
        OCR_LETTER_TO_DIGIT = {
            "O": "0",   # O ↔ 0
            "I": "1",   # I ↔ 1
            "L": "1",   # l ↔ 1
            "Z": "2",   # Z ↔ 2
            "A": "4",   # A ↔ 4  (common in sans-serif OCR)
            "S": "5",   # S ↔ 5
            "G": "6",   # G ↔ 6
            "T": "7",   # T ↔ 7  (crossbar similarity)
            "B": "8",   # B ↔ 8
        }

        chars = list(pan)
        for i in range(5, 9):  # digit positions
            if chars[i].isdigit():
                continue
            replacement = OCR_LETTER_TO_DIGIT.get(chars[i])
            if replacement is None:
                # Unknown letter at digit position — cannot safely correct
                return None
            chars[i] = replacement

        return "".join(chars)

    @staticmethod
    def _determine_status(extracted: int, total: int) -> str:
        """Classify extraction outcome."""
        if total == 0:
            return "no_fields"
        if extracted == 0:
            return "no_fields"
        if extracted >= total:
            return "success"
        return "partial"
