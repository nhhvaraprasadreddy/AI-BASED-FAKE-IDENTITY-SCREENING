"""Real EasyOCR integration test using a synthetic document image.

This script creates a synthetic Aadhaar-style test image using OpenCV
putText, runs the REAL EasyOCR engine on it (not mocked), and prints
the full pipeline results.

THIS IS SYNTHETIC TEST DATA — not a real identity document.

Usage:
    venv\\Scripts\\python.exe tests/manual_ocr_test.py

Note: EasyOCR will download model weights (~100 MB) on first run.
"""
from __future__ import annotations

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np

from src.ocr.engine import OCREngine
from src.documents.detector import DocumentDetector
from src.documents.extractor import FieldExtractor
from src.documents.validators import DocumentValidator
from src.vision.preprocessing import ImagePreprocessor


def create_synthetic_aadhaar_image() -> np.ndarray:
    """Create a synthetic Aadhaar-style test image with clearly fake data.

    All data is synthetic — this is NOT a real identity document.
    """
    # White background (BGR)
    img = np.full((500, 700, 3), 255, dtype=np.uint8)

    # Add a blue header bar
    cv2.rectangle(img, (0, 0), (700, 60), (180, 100, 30), -1)

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_bold = cv2.FONT_HERSHEY_DUPLEX

    # Header text (white on blue)
    cv2.putText(img, "GOVERNMENT OF INDIA", (150, 30), font_bold, 0.7, (255, 255, 255), 2)
    cv2.putText(img, "UNIQUE IDENTIFICATION AUTHORITY OF INDIA", (80, 55), font, 0.5, (255, 255, 255), 1)

    # Body text (black on white)
    cv2.putText(img, "Aadhaar", (280, 100), font_bold, 0.9, (0, 0, 0), 2)
    cv2.putText(img, "UIDAI", (310, 130), font, 0.6, (100, 100, 100), 1)

    cv2.putText(img, "Name: Rahul Kumar", (50, 200), font, 0.7, (0, 0, 0), 2)
    cv2.putText(img, "DOB: 15/08/2002", (50, 250), font, 0.7, (0, 0, 0), 2)
    cv2.putText(img, "Male", (50, 300), font, 0.7, (0, 0, 0), 2)

    # Aadhaar number (synthetic)
    cv2.putText(img, "1234 5678 9012", (200, 400), font_bold, 1.2, (0, 0, 0), 3)

    # Footer disclaimer
    cv2.putText(img, "[SYNTHETIC TEST DOCUMENT - NOT REAL]", (120, 470), font, 0.5, (0, 0, 200), 1)

    return img


def main() -> None:
    print("=" * 60)
    print("REAL EasyOCR Integration Test — Synthetic Aadhaar Image")
    print("=" * 60)

    # 1. Create synthetic image
    print("\n[1] Creating synthetic Aadhaar test image...")
    img = create_synthetic_aadhaar_image()
    print(f"    Image shape: {img.shape}, dtype: {img.dtype}")

    # Save for inspection
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "data", "test_cases"
    )
    os.makedirs(output_path, exist_ok=True)
    save_path = os.path.join(output_path, "synthetic_aadhaar_test.png")
    cv2.imwrite(save_path, img)
    print(f"    Saved to: {save_path}")

    # 2. Preprocess
    print("\n[2] Preprocessing...")
    preprocessor = ImagePreprocessor()
    prep = preprocessor.preprocess(img)
    ocr_image = prep.get("grayscale", prep.get("processed", img))
    print(f"    OCR input shape: {ocr_image.shape}, dtype: {ocr_image.dtype}")

    # 3. OCR (REAL — not mocked)
    print("\n[3] Running EasyOCR (this may download models on first run)...")
    engine = OCREngine()
    ocr_result = engine.extract_text(ocr_image)

    print(f"    Status: {ocr_result['status']}")
    print(f"    Engine: {ocr_result.get('engine', 'N/A')}")
    print(f"    Confidence: {ocr_result.get('confidence', 0):.2%}")
    print(f"    Regions: {len(ocr_result.get('details', []))}")
    print(f"    Text:\n    ---")
    for line in (ocr_result.get("text", "") or "").split("  "):
        line = line.strip()
        if line:
            print(f"    {line}")
    print("    ---")

    if ocr_result.get("details"):
        print("\n    Per-region details:")
        for i, d in enumerate(ocr_result["details"]):
            print(f"      [{i}] conf={d['confidence']:.2f}  text=\"{d['text']}\"")

    # 4. Document detection
    print("\n[4] Document detection...")
    detector = DocumentDetector()
    detect_result = detector.detect(ocr_result.get("text", ""))
    print(f"    Type: {detect_result.get('document_type', 'None')}")
    print(f"    Name: {detect_result.get('document_name', 'Unknown')}")
    print(f"    Confidence: {detect_result.get('confidence', 0):.2%}")
    print(f"    Status: {detect_result.get('status')}")
    print(f"    Method: {detect_result.get('method', 'N/A')}")
    if detect_result.get("matched_keywords"):
        print(f"    Keywords: {', '.join(detect_result['matched_keywords'])}")

    # 5. Field extraction
    print("\n[5] Field extraction...")
    doc_type = detect_result.get("document_type") or ""
    extractor = FieldExtractor()
    extract_result = extractor.extract(ocr_result.get("text", ""), doc_type)
    print(f"    Status: {extract_result.get('status')}")
    print(f"    Extracted: {extract_result.get('extraction_count')} / {extract_result.get('total_fields')} fields")
    for fname, fdata in extract_result.get("fields", {}).items():
        print(f"      {fname}: \"{fdata['value']}\" (conf={fdata['confidence']})")

    # 6. Validation
    print("\n[6] Document validation...")
    validator = DocumentValidator()
    valid_result = validator.validate(extract_result.get("fields", {}), doc_type)
    print(f"    Status: {valid_result.get('status')}")
    print(f"    All passed: {valid_result.get('all_passed')}")
    print(f"    Checks: {valid_result.get('valid_count')}/{valid_result.get('total_count')}")
    for chk in valid_result.get("checks", []):
        icon = "[OK]" if chk["passed"] else "[FAIL]"
        print(f"      {icon} {chk['check_name']}: {chk['message']}")
    if valid_result.get("findings"):
        print("    Findings:")
        for f in valid_result["findings"]:
            print(f"      - {f}")

    # Summary
    print("\n" + "=" * 60)
    print("RESULT SUMMARY")
    print("=" * 60)
    success = (
        ocr_result["status"] == "success"
        and detect_result.get("document_type") == "aadhaar"
        and extract_result.get("extraction_count", 0) > 0
        and valid_result.get("status") in ("success", "partial")
    )
    if success:
        print("[PASS] Full pipeline: OCR -> Detection -> Extraction -> Validation")
    else:
        print("[PARTIAL] Pipeline partially working. See details above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
