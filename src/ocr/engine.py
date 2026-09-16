"""OCR engine wrapper using EasyOCR.

Provides a clean, engine-agnostic interface for text extraction from
document images.  The underlying engine is EasyOCR (a pretrained deep
learning OCR model) — this wrapper does NOT train any custom model.

The reader is lazily initialized on first ``extract_text`` call to avoid
model-download costs during import or test collection.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from src.config import OCR_CONFIDENCE_THRESHOLD, OCR_LANGUAGES

logger = logging.getLogger(__name__)


class OCREngine:
    """Abstraction layer for OCR processing.

    Wraps EasyOCR behind a stable dict-based interface so the OCR
    library can be replaced without rewriting calling code.
    """

    def __init__(self, languages: Optional[list[str]] = None) -> None:
        """Initialize OCR engine configuration.

        Args:
            languages: Language codes for EasyOCR (e.g. ``['en', 'hi']``).
                       Defaults to ``OCR_LANGUAGES`` from config.
        """
        self.languages = languages or list(OCR_LANGUAGES)
        self.confidence_threshold = OCR_CONFIDENCE_THRESHOLD
        self._reader = None
        self._initialized = False
        logger.info("OCREngine created — languages: %s", self.languages)

    # ── lazy init ────────────────────────────────────────────────────

    def _ensure_initialized(self) -> None:
        """Lazy-initialize the EasyOCR reader.

        Downloads model weights on first run (~100 MB, one-time).
        Uses CPU mode (``gpu=False``) for maximum portability.
        """
        if self._initialized:
            return
        try:
            import easyocr  # noqa: delay import

            self._reader = easyocr.Reader(
                self.languages, gpu=False, verbose=False
            )
            self._initialized = True
            logger.info(
                "EasyOCR reader initialized — languages: %s", self.languages
            )
        except Exception as exc:
            logger.error("Failed to initialize EasyOCR: %s", exc)
            raise RuntimeError(
                f"OCR engine initialization failed: {exc}"
            ) from exc

    # ── public API ───────────────────────────────────────────────────

    def extract_text(self, image: np.ndarray) -> dict:
        """Extract text from a preprocessed document image.

        Args:
            image: Preprocessed image as numpy array (BGR or grayscale).

        Returns:
            dict with keys:
                - **text** (*str*): Concatenated extracted text.
                - **confidence** (*float*): Character-weighted average
                  confidence across accepted regions (0.0–1.0).
                - **details** (*list[dict]*): Per-region results, each
                  containing ``text``, ``confidence``, and ``bbox``.
                - **engine** (*str*): ``"easyocr"``.
                - **status** (*str*): ``"success"``, ``"no_text"``,
                  or ``"error"``.
                - **message** (*str*, optional): Human-readable note.
        """
        if image is None:
            logger.warning("OCR received None image")
            return self._error_result("Received None image")

        try:
            self._ensure_initialized()

            # EasyOCR readtext → list of (bbox, text, confidence)
            raw_results = self._reader.readtext(image)

            if not raw_results:
                logger.info("OCR found no text in image")
                return {
                    "text": "",
                    "confidence": 0.0,
                    "details": [],
                    "engine": "easyocr",
                    "status": "no_text",
                    "message": "No text detected in image.",
                }

            # Filter regions below the confidence threshold
            details: list[dict] = []
            for bbox, text, conf in raw_results:
                if conf >= self.confidence_threshold:
                    details.append(
                        {
                            "text": text.strip(),
                            "confidence": round(float(conf), 4),
                            "bbox": bbox,
                        }
                    )

            if not details:
                logger.info(
                    "OCR: all %d regions below confidence threshold %.2f",
                    len(raw_results),
                    self.confidence_threshold,
                )
                return {
                    "text": "",
                    "confidence": 0.0,
                    "details": [],
                    "engine": "easyocr",
                    "status": "no_text",
                    "message": (
                        f"Text detected but all regions below confidence "
                        f"threshold ({self.confidence_threshold})."
                    ),
                }

            # Concatenate text; compute character-weighted average conf
            full_text = " ".join(d["text"] for d in details)
            total_weighted = sum(
                d["confidence"] * len(d["text"]) for d in details
            )
            total_chars = sum(len(d["text"]) for d in details)
            avg_confidence = (
                round(total_weighted / total_chars, 4)
                if total_chars > 0
                else 0.0
            )

            logger.info(
                "OCR extracted %d regions, %d chars, avg conf %.3f",
                len(details),
                total_chars,
                avg_confidence,
            )

            return {
                "text": full_text,
                "confidence": avg_confidence,
                "details": details,
                "engine": "easyocr",
                "status": "success",
            }

        except RuntimeError:
            raise  # propagate init failures
        except Exception as exc:
            logger.error("OCR extraction failed: %s", exc)
            return self._error_result(str(exc))

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _error_result(message: str) -> dict:
        """Return a standard error-result dict."""
        return {
            "text": "",
            "confidence": 0.0,
            "details": [],
            "engine": "easyocr",
            "status": "error",
            "message": message,
        }
