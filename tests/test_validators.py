"""Tests for module interfaces — verify return schemas and contracts.

Modules that have been implemented (OCR, Detector, Extractor) are
tested for their real return schema.  Modules still in stub form
(Validator, Tampering, Consistency, Risk) are tested for their stub
contracts.  OCR tests mock easyocr.Reader to avoid model downloads.
"""
from __future__ import annotations
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.documents.detector import DocumentDetector
from src.documents.extractor import FieldExtractor
from src.documents.validators import DocumentValidator
from src.ocr.engine import OCREngine
from src.vision.tampering import TamperingAnalyzer
from src.verification.consistency import ConsistencyChecker
from src.risk.scoring import RiskScorer


class TestOCREngine:
    def test_init(self) -> None:
        engine = OCREngine()
        assert engine is not None

    @patch("easyocr.Reader")
    def test_extract_returns_expected_keys(self, mock_reader_cls) -> None:
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = []
        mock_reader_cls.return_value = mock_reader

        engine = OCREngine()
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = engine.extract_text(img)
        assert isinstance(result, dict)
        assert "text" in result
        assert "confidence" in result
        assert "status" in result
        assert result["status"] in ("success", "no_text", "error")


class TestDocumentDetector:
    def test_init(self) -> None:
        detector = DocumentDetector()
        assert detector is not None

    def test_detect_returns_expected_keys(self) -> None:
        detector = DocumentDetector()
        result = detector.detect("Government of India Aadhaar UIDAI")
        assert isinstance(result, dict)
        assert "document_type" in result
        assert "document_name" in result
        assert "confidence" in result
        assert result["status"] in ("success", "no_match")


class TestFieldExtractor:
    def test_init(self) -> None:
        extractor = FieldExtractor()
        assert extractor is not None

    def test_extract_returns_expected_keys(self) -> None:
        extractor = FieldExtractor()
        result = extractor.extract("Name: John Doe\n1234 5678 9012", "aadhaar")
        assert isinstance(result, dict)
        assert "fields" in result
        assert "extraction_count" in result
        assert "total_fields" in result
        assert result["status"] in ("success", "partial", "no_fields")

    def test_extract_unknown_doc_type(self) -> None:
        extractor = FieldExtractor()
        result = extractor.extract("text", "unknown_type")
        assert isinstance(result, dict)
        assert result["total_fields"] == 0


class TestDocumentValidator:
    def test_init(self) -> None:
        validator = DocumentValidator()
        assert validator is not None

    def test_validate_returns_expected_keys(self) -> None:
        validator = DocumentValidator()
        fields = {"name": {"value": "Test", "confidence": 0.7, "label": "Name"}}
        result = validator.validate(fields, "aadhaar")
        assert isinstance(result, dict)
        assert "checks" in result
        assert "valid_count" in result
        assert "total_count" in result
        assert "all_passed" in result
        assert result["status"] in ("success", "partial", "failed", "error")


class TestTamperingAnalyzer:
    def test_init(self) -> None:
        analyzer = TamperingAnalyzer()
        assert analyzer is not None

    def test_analyze_returns_expected_keys(self) -> None:
        analyzer = TamperingAnalyzer()
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = analyzer.analyze(img)
        assert isinstance(result, dict)
        assert "checks" in result
        assert "ela_image" in result
        assert "overall_suspicious" in result
        assert "suspicion_score" in result
        assert result["status"] in ("success", "error")


class TestConsistencyChecker:
    def test_init(self) -> None:
        checker = ConsistencyChecker()
        assert checker is not None

    def test_single_doc_returns_insufficient(self) -> None:
        checker = ConsistencyChecker()
        result = checker.check([{"document_type": "aadhaar"}])
        assert result["status"] == "insufficient_documents"
        assert result["consistent"] is True

    def test_empty_list(self) -> None:
        checker = ConsistencyChecker()
        result = checker.check([])
        assert result["consistent"] is True
        assert result["status"] == "insufficient_documents"


class TestRiskScorer:
    def test_init(self) -> None:
        scorer = RiskScorer()
        assert scorer is not None

    def test_calculate_returns_expected_keys(self) -> None:
        scorer = RiskScorer()
        result = scorer.calculate(
            validation_results={"checks": [], "valid_count": 0, "total_count": 0, "all_passed": True},
            tampering_results={"checks": [], "overall_suspicious": False, "suspicion_score": 0.0},
        )
        assert isinstance(result, dict)
        assert "score" in result
        assert "level" in result
        assert "recommendation" in result
        assert "factors" in result
        assert "indicators" in result
        assert result["level"] in ("LOW", "MEDIUM", "HIGH")
        assert result["status"] == "success"

