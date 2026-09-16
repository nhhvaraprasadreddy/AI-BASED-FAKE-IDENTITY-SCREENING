"""Document type detection via keyword-frequency heuristic.

Identifies document type (Aadhaar, PAN, Voter ID) from OCR-extracted
text by counting keyword and phrase matches against the definitions in
``src.config.DOCUMENT_TYPES``.

**This is a rule-based heuristic — NOT a trained ML document
classifier.**  Detection quality depends on OCR accuracy and the
completeness of the keyword lists.

Detection requires at least ``MINIMUM_KEYWORD_HITS`` (default 2)
matches to reduce false positives from short or noisy OCR text.
"""
from __future__ import annotations

import logging
import re

from src.config import DOCUMENT_TYPES

logger = logging.getLogger(__name__)


class DocumentDetector:
    """Identifies document type from OCR-extracted text.

    Uses keyword / phrase frequency matching — the document type whose
    keywords appear most frequently in the OCR text wins, provided the
    hit count meets the minimum threshold.
    """

    MINIMUM_KEYWORD_HITS: int = 2

    def __init__(self) -> None:
        """Initialize with document type definitions from config."""
        self.document_types = DOCUMENT_TYPES
        logger.info(
            "DocumentDetector initialized — %d types registered",
            len(self.document_types),
        )

    # ── public API ───────────────────────────────────────────────────

    def detect(self, ocr_text: str) -> dict:
        """Detect document type from OCR text.

        Args:
            ocr_text: Raw text string from OCR engine.

        Returns:
            dict with keys:
                - **document_type** (*str | None*): Config key or ``None``.
                - **document_name** (*str*): Human-readable name.
                - **confidence** (*float*): ``matched / total`` keywords.
                - **matched_keywords** (*list[str]*): Keywords that hit.
                - **status** (*str*): ``"success"`` or ``"no_match"``.
                - **method** (*str*): Always ``"keyword_heuristic"``.
        """
        if not ocr_text or not ocr_text.strip():
            logger.info("Document detector received empty text")
            return self._no_match_result("Empty or no OCR text provided.")

        normalized = self._normalize_text(ocr_text)

        best_type: str | None = None
        best_hits: int = 0
        best_keywords: list[str] = []
        best_name: str = "Unknown"

        for doc_key, doc_cfg in self.document_types.items():
            keywords = doc_cfg.get("keywords", [])
            if not keywords:
                continue

            matched: list[str] = []
            for kw in keywords:
                kw_norm = kw.strip().lower()
                if not kw_norm:
                    continue
                if self._keyword_matches(kw_norm, normalized):
                    matched.append(kw)

            structural_match = self._structural_evidence(doc_key, normalized)
            if structural_match:
                matched.append(structural_match)

            if len(matched) > best_hits:
                best_hits = len(matched)
                best_type = doc_key
                best_keywords = matched
                best_name = doc_cfg.get("name", doc_key)

        if best_hits < self.MINIMUM_KEYWORD_HITS:
            logger.info(
                "Detection: no type reached minimum %d hits (best %d)",
                self.MINIMUM_KEYWORD_HITS,
                best_hits,
            )
            return self._no_match_result(
                f"No document type matched with sufficient confidence "
                f"(best: {best_hits} keyword(s), "
                f"minimum: {self.MINIMUM_KEYWORD_HITS})."
            )

        total_kw = len(self.document_types[best_type].get("keywords", []))
        confidence = round(best_hits / total_kw, 4) if total_kw > 0 else 0.0

        logger.info(
            "Detected: %s (conf %.3f, %d/%d keywords)",
            best_type,
            confidence,
            best_hits,
            total_kw,
        )

        return {
            "document_type": best_type,
            "document_name": best_name,
            "confidence": confidence,
            "matched_keywords": best_keywords,
            "status": "success",
            "method": "keyword_heuristic",
        }

    # ── internal helpers ─────────────────────────────────────────────

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Lowercase, collapse whitespace, strip edges."""
        text = text.lower()
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _keyword_matches(keyword: str, normalized_text: str) -> bool:
        r"""Check whether *keyword* appears in *normalized_text*.

        * **Multi-word phrases** — substring match (after both sides
          are normalised) is appropriate because the phrase itself
          provides enough specificity.
        * **Single words** — word-boundary (``\b``) regex match to
          prevent false substring hits (e.g. ``"pan"`` must not match
          ``"company"`` or ``"pandemonium"``).
        """
        if " " in keyword:
            # multi-word phrase → substring match
            return keyword in normalized_text
        # single word → word-boundary match
        pattern = r"\b" + re.escape(keyword) + r"\b"
        return bool(re.search(pattern, normalized_text))

    @staticmethod
    def _structural_evidence(doc_type: str, text: str) -> str | None:
        """Check for document-specific identifier patterns in text."""
        text_upper = text.upper()
        if doc_type == "aadhaar":
            if re.search(r"\b\d{4}\s?\d{4}\s?\d{4}\b", text_upper):
                return "[pattern: 12-digit ID]"
        elif doc_type == "pan":
            if re.search(r"\b[A-Z]{5}\d{4}[A-Z]\b", text_upper):
                return "[pattern: PAN format]"
        elif doc_type == "voter_id":
            if re.search(r"\b[A-Z]{3}\d{7}\b", text_upper):
                return "[pattern: EPIC format]"
        return None

    def _no_match_result(self, message: str) -> dict:
        """Return a standard no-match result dict."""
        return {
            "document_type": None,
            "document_name": "Unknown",
            "confidence": 0.0,
            "matched_keywords": [],
            "status": "no_match",
            "method": "keyword_heuristic",
            "message": message,
        }
