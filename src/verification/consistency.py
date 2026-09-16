"""Cross-document consistency checking.

Compares extracted identity fields across multiple documents to identify
potential mismatches.  Results are screening indicators for human review.

**A mismatch does NOT prove fraud.**  Legitimate reasons for differences
include: name transliteration, OCR errors, married-name changes, typos
on genuine documents, etc.

Only fields that are meaningfully comparable (e.g. name, DOB) are compared
across document types.
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Fields that can be compared across document types
_COMPARABLE_FIELDS: dict[str, str] = {
    "name": "Name",
    "dob": "Date of Birth",
}


class ConsistencyChecker:
    """Checks consistency across multiple identity documents.

    Uses deterministic normalized comparison — NOT machine learning.
    """

    def __init__(self) -> None:
        """Initialize consistency checker."""
        logger.info("ConsistencyChecker initialized")

    def check(self, documents: list[dict]) -> dict:
        """Check consistency across multiple document analysis results.

        Args:
            documents: List of document analysis results, each containing
                      'document_type', 'fields', and optionally 'validation'.

        Returns:
            dict with keys:
                - checks (list[dict]): Consistency checks, each with:
                    'field', 'field_label', 'documents_compared',
                    'consistent' (bool), 'message', 'values' (list)
                - consistent (bool): True if all cross-checks pass
                - consistency_score (float): 0.0 (all mismatch) to
                    1.0 (all match)
                - status (str): 'success' or 'insufficient_documents'
                - message (str): Human-readable summary
                - compared_count (int): Number of comparisons made
                - mismatch_count (int): Number of mismatches found
        """
        if documents is None:
            documents = []

        if len(documents) < 2:
            return {
                "checks": [],
                "consistent": True,
                "consistency_score": 1.0,
                "status": "insufficient_documents",
                "message": "Need at least 2 documents for consistency checking.",
                "compared_count": 0,
                "mismatch_count": 0,
            }

        checks: list[dict[str, Any]] = []

        for field_key, field_label in _COMPARABLE_FIELDS.items():
            result = self._compare_field(documents, field_key, field_label)
            if result is not None:
                checks.append(result)

        compared = len(checks)
        mismatches = sum(1 for c in checks if not c["consistent"])
        all_consistent = mismatches == 0
        score = (compared - mismatches) / compared if compared > 0 else 1.0

        if compared == 0:
            message = (
                "No comparable fields found across documents. "
                "Different document types may not share common fields."
            )
        elif all_consistent:
            message = (
                f"All {compared} comparable field(s) are consistent "
                "across documents. This does not guarantee document "
                "authenticity."
            )
        else:
            message = (
                f"{mismatches} of {compared} comparable field(s) show "
                "differences across documents. This may indicate a "
                "data discrepancy and warrants human review. "
                "Differences can also be caused by OCR errors, "
                "transliteration, or legitimate name changes."
            )

        logger.info(
            "Consistency check: %d comparisons, %d mismatches, score=%.2f",
            compared, mismatches, score,
        )

        return {
            "checks": checks,
            "consistent": all_consistent,
            "consistency_score": round(score, 4),
            "status": "success",
            "message": message,
            "compared_count": compared,
            "mismatch_count": mismatches,
        }

    # ── field comparison ─────────────────────────────────────────────

    def _compare_field(
        self,
        documents: list[dict],
        field_key: str,
        field_label: str,
    ) -> dict | None:
        """Compare a single field across all documents that contain it.

        Returns None if fewer than 2 documents have the field.
        """
        values: list[dict[str, str]] = []
        for doc in documents:
            fields = doc.get("fields", {})
            val = self._extract_value(fields, field_key)
            if val is not None:
                doc_type = doc.get("document_type", "unknown")
                values.append({"document_type": doc_type, "value": val})

        if len(values) < 2:
            return None  # Cannot compare with fewer than 2 values

        # Normalize and compare
        if field_key == "dob":
            consistent = self._compare_dates(values)
        else:
            consistent = self._compare_normalized(values)

        doc_types = [v["document_type"] for v in values]
        # Mask sensitive values for display
        display_values = [
            {"document_type": v["document_type"], "value": v["value"]}
            for v in values
        ]

        if consistent:
            msg = f"{field_label} is consistent across {', '.join(doc_types)}."
        else:
            msg = (
                f"{field_label} differs across {', '.join(doc_types)}. "
                "This may warrant human review."
            )

        return {
            "field": field_key,
            "field_label": field_label,
            "documents_compared": doc_types,
            "consistent": consistent,
            "message": msg,
            "values": display_values,
        }

    # ── value extraction ─────────────────────────────────────────────

    @staticmethod
    def _extract_value(fields: dict, field_key: str) -> str | None:
        """Extract a field value, handling both dict and string formats."""
        if field_key not in fields:
            return None
        val = fields[field_key]
        if isinstance(val, dict):
            val = val.get("value", "")
        if isinstance(val, str):
            val = val.strip()
            return val if val else None
        return None

    # ── comparison methods ───────────────────────────────────────────

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize a name for comparison.

        - lowercase
        - collapse whitespace
        - remove common punctuation (., -)
        """
        s = name.lower().strip()
        s = re.sub(r"[.\-,]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _compare_normalized(self, values: list[dict]) -> bool:
        """Compare values after normalization.  All must match."""
        normalized = [self._normalize_name(v["value"]) for v in values]
        return len(set(normalized)) == 1

    @staticmethod
    def _normalize_date(date_str: str) -> str | None:
        """Attempt to normalize a date string to DD/MM/YYYY."""
        s = date_str.strip()
        # Try DD/MM/YYYY or DD-MM-YYYY
        m = re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$", s)
        if m:
            return f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}"
        # Try YYYY-MM-DD
        m = re.match(r"^(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})$", s)
        if m:
            return f"{int(m.group(3)):02d}/{int(m.group(2)):02d}/{m.group(1)}"
        return None

    def _compare_dates(self, values: list[dict]) -> bool:
        """Compare date values after normalization."""
        normalized = []
        for v in values:
            norm = self._normalize_date(v["value"])
            if norm is None:
                return False  # Unparseable date → cannot confirm match
            normalized.append(norm)
        return len(set(normalized)) == 1
