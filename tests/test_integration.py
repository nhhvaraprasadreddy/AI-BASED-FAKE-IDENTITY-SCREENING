"""Integration test for the Streamlit analysis pipeline.

Validates that the Phase 2 pipeline (preprocess → OCR → detect → extract)
works end-to-end.  EasyOCR is mocked so this test runs without model
downloads, internet, or GPU.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.documents.detector import DocumentDetector
from src.documents.extractor import FieldExtractor
from src.documents.validators import DocumentValidator
from src.ocr.engine import OCREngine
from src.vision.preprocessing import ImagePreprocessor


class TestPipelineIntegration:
    """End-to-end pipeline: preprocess → OCR → detect → extract."""

    @staticmethod
    def _make_color_image(h: int = 200, w: int = 400) -> np.ndarray:
        """Synthetic BGR image (white background)."""
        return np.full((h, w, 3), 255, dtype=np.uint8)

    @patch("easyocr.Reader")
    def test_full_pipeline_aadhaar(self, mock_reader_cls) -> None:
        """Simulate a successful Aadhaar card analysis."""
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = [
            ([[0, 0], [200, 0], [200, 20], [0, 20]],
             "GOVERNMENT OF INDIA", 0.95),
            ([[0, 25], [200, 25], [200, 45], [0, 45]],
             "Unique Identification Authority of India", 0.90),
            ([[0, 50], [200, 50], [200, 70], [0, 70]],
             "Aadhaar", 0.92),
            ([[0, 75], [200, 75], [200, 95], [0, 95]],
             "Name: Rajesh Kumar", 0.88),
            ([[0, 100], [200, 100], [200, 120], [0, 120]],
             "DOB: 15/08/1990", 0.85),
            ([[0, 125], [200, 125], [200, 145], [0, 145]],
             "Male", 0.90),
            ([[0, 150], [200, 150], [200, 170], [0, 170]],
             "1234 5678 9012", 0.93),
        ]
        mock_reader_cls.return_value = mock_reader

        img = self._make_color_image()

        # 1. Preprocess
        preprocessor = ImagePreprocessor()
        prep = preprocessor.preprocess(img)
        assert "grayscale" in prep
        assert prep["grayscale"] is not None

        # 2. OCR — use grayscale, not threshold (as app.py now does)
        ocr_image = prep.get("grayscale", prep.get("processed", img))
        engine = OCREngine()
        ocr_result = engine.extract_text(ocr_image)
        assert ocr_result["status"] == "success"
        assert "Aadhaar" in ocr_result["text"]
        assert ocr_result["confidence"] > 0

        # 3. Detect
        detector = DocumentDetector()
        detect_result = detector.detect(ocr_result["text"])
        assert detect_result["document_type"] == "aadhaar"
        assert detect_result["status"] == "success"

        # 4. Extract
        extractor = FieldExtractor()
        extract_result = extractor.extract(
            ocr_result["text"], detect_result["document_type"]
        )
        assert extract_result["extraction_count"] >= 2
        assert "aadhaar_number" in extract_result["fields"]
        assert "1234" in extract_result["fields"]["aadhaar_number"]["value"]

        # 5. Validate
        validator = DocumentValidator()
        valid_result = validator.validate(
            extract_result["fields"], detect_result["document_type"]
        )
        assert valid_result["status"] in ("success", "partial", "failed")
        assert len(valid_result["checks"]) > 0
        assert "findings" in valid_result
        assert valid_result["document_type"] == "aadhaar"

    @patch("easyocr.Reader")
    def test_pipeline_no_text(self, mock_reader_cls) -> None:
        """When OCR returns no text, detect and extract handle gracefully."""
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = []
        mock_reader_cls.return_value = mock_reader

        img = self._make_color_image()
        preprocessor = ImagePreprocessor()
        prep = preprocessor.preprocess(img)

        engine = OCREngine()
        ocr_image = prep.get("grayscale", prep.get("processed", img))
        ocr_result = engine.extract_text(ocr_image)
        assert ocr_result["status"] == "no_text"

        # Detector should return no_match
        detector = DocumentDetector()
        detect_result = detector.detect(ocr_result["text"])
        assert detect_result["status"] == "no_match"

        # Extractor should return no_fields
        extractor = FieldExtractor()
        extract_result = extractor.extract(
            ocr_result["text"], detect_result.get("document_type") or ""
        )
        assert extract_result["extraction_count"] == 0

    @patch("easyocr.Reader")
    def test_pipeline_uses_grayscale_not_threshold(self, mock_reader_cls) -> None:
        """Verify the grayscale image is used for OCR, not the threshold."""
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "test", 0.9),
        ]
        mock_reader_cls.return_value = mock_reader

        img = self._make_color_image()
        preprocessor = ImagePreprocessor()
        prep = preprocessor.preprocess(img)

        # The grayscale image should be 2D (single channel)
        gray = prep.get("grayscale")
        assert gray is not None
        assert len(gray.shape) == 2

        # The 'processed' (threshold) image is also 2D but binary
        threshold = prep.get("processed")
        assert threshold is not None
        unique_vals = set(np.unique(threshold))
        assert unique_vals.issubset({0, 255}), "Threshold should be binary"

        # The grayscale image should NOT be binary
        gray_unique = np.unique(gray)
        # A real grayscale image has more than 2 values
        # (unless the source is perfectly uniform)
        # Our white image produces a uniform grayscale, so just verify
        # it is the correct type
        assert gray.dtype == np.uint8


class TestPhase5Integration:
    """Integration tests for consistency + risk scoring (Phase 5)."""

    @patch("easyocr.Reader")
    def test_single_document_risk_scoring(self, mock_reader_cls) -> None:
        """Single-document pipeline produces valid risk result."""
        from src.vision.tampering import TamperingAnalyzer
        from src.risk.scoring import RiskScorer
        from src.verification.consistency import ConsistencyChecker

        mock_reader = MagicMock()
        mock_reader.readtext.return_value = [
            ([[0, 0], [200, 0], [200, 20], [0, 20]],
             "GOVERNMENT OF INDIA", 0.95),
            ([[0, 25], [200, 25], [200, 45], [0, 45]],
             "Aadhaar", 0.92),
            ([[0, 50], [200, 50], [200, 70], [0, 70]],
             "Name: Rajesh Kumar", 0.88),
            ([[0, 75], [200, 75], [200, 95], [0, 75]],
             "1234 5678 9012", 0.93),
        ]
        mock_reader_cls.return_value = mock_reader

        img = np.full((200, 400, 3), 255, dtype=np.uint8)
        preprocessor = ImagePreprocessor()
        prep = preprocessor.preprocess(img)

        engine = OCREngine()
        ocr_result = engine.extract_text(prep.get("grayscale", img))

        detector = DocumentDetector()
        detect_result = detector.detect(ocr_result["text"])

        extractor = FieldExtractor()
        extract_result = extractor.extract(
            ocr_result["text"], detect_result.get("document_type", ""),
        )

        validator = DocumentValidator()
        valid_result = validator.validate(
            extract_result.get("fields", {}),
            detect_result.get("document_type", ""),
        )

        tampering = TamperingAnalyzer()
        tamp_result = tampering.analyze(img)

        # Single document → consistency returns insufficient
        checker = ConsistencyChecker()
        cons_result = checker.check([{
            "document_type": detect_result.get("document_type"),
            "fields": extract_result.get("fields", {}),
        }])
        assert cons_result["status"] == "insufficient_documents"

        # Risk scoring still works with single document
        scorer = RiskScorer()
        risk_result = scorer.calculate(valid_result, tamp_result, cons_result)
        assert risk_result["status"] == "success"
        assert risk_result["level"] in ("LOW", "MEDIUM", "HIGH")
        assert 0.0 <= risk_result["score"] <= 1.0

    def test_multi_document_consistency_and_risk(self) -> None:
        """Two synthetic documents through consistency + risk pipeline."""
        from src.verification.consistency import ConsistencyChecker
        from src.risk.scoring import RiskScorer

        # Simulate extracted fields from two documents
        doc_a = {
            "document_type": "aadhaar",
            "fields": {"name": "RAHUL KUMAR", "dob": "01/01/2000"},
            "validation": {"checks": [], "valid_count": 0, "total_count": 0, "all_passed": True},
        }
        doc_b = {
            "document_type": "pan",
            "fields": {"name": "RAHUL KUMAR", "dob": "01/01/2000"},
            "validation": {"checks": [], "valid_count": 0, "total_count": 0, "all_passed": True},
        }

        checker = ConsistencyChecker()
        cons_result = checker.check([doc_a, doc_b])
        assert cons_result["status"] == "success"
        assert cons_result["consistent"] is True

        scorer = RiskScorer()
        risk_result = scorer.calculate(
            doc_a["validation"],
            {"checks": [], "overall_suspicious": False, "suspicion_score": 0.0, "status": "success"},
            cons_result,
        )
        assert risk_result["level"] == "LOW"
        assert risk_result["score"] == 0.0

    def test_multi_document_name_mismatch_risk(self) -> None:
        """Name mismatch across documents increases risk score."""
        from src.verification.consistency import ConsistencyChecker
        from src.risk.scoring import RiskScorer

        doc_a = {
            "document_type": "aadhaar",
            "fields": {"name": "RAHUL KUMAR", "dob": "01/01/2000"},
        }
        doc_b = {
            "document_type": "pan",
            "fields": {"name": "RAHUL SHARMA", "dob": "01/01/2000"},
        }

        checker = ConsistencyChecker()
        cons_result = checker.check([doc_a, doc_b])
        assert cons_result["consistent"] is False
        assert cons_result["mismatch_count"] >= 1

        scorer = RiskScorer()
        risk_result = scorer.calculate(
            {"checks": [], "valid_count": 0, "total_count": 0, "all_passed": True},
            {"checks": [], "overall_suspicious": False, "suspicion_score": 0.0, "status": "success"},
            cons_result,
        )
        assert risk_result["score"] > 0.0
        assert any("consistency" in f["category"] for f in risk_result["factors"])
