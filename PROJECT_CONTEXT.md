# PROJECT CONTEXT

## Project

SIH26188 - AI-Based Fake Identity & Document Screening System

## Current Goal

Build a hackathon MVP that screens identity documents for suspicious
indicators and provides an explainable risk assessment for human review.

The system must NOT claim to legally determine whether a person is fraudulent
or whether a document is definitively fake.

## Current Development Stage

PHASE 6 COMPLETE � UI / REPORTING / POLISH (v0.2.0)

Phase 1: Project skeleton and Streamlit MVP.
Phase 2: EasyOCR integration, document detection, field extraction.
Phase 2.5: Streamlit OCR display fix (grayscale input, expanded results).
Phase 3: Document and field validation (Verhoeff, format, dates, required fields).
Phase 4: Image tampering/anomaly analysis (ELA, edge density, noise analysis).
Phase 5: Cross-document consistency + explainable rule-based risk scoring.
Phase 6: UI/reporting polish � tabbed results, JSON export, improved history, error handling.
Phase 7: Final hardening � structural detection evidence, 43 new hardening tests, demo readiness.

Current test result:

262 tests passed (43 new hardening tests added in Phase 7, 0 regressions).

## What Currently Exists

### Fully implemented components:

- Streamlit application (dashboard, screening, history, about pages)
- Image preprocessing module (OpenCV pipeline)
- SQLite database module (full CRUD)
- Utility/configuration modules (masking, formatting, risk levels)
- **OCR engine** (EasyOCR wrapper with lazy initialization)
- **Document type detector** (keyword-frequency heuristic for Aadhaar,
  PAN, Voter ID)
- **Field extractor** (regex-based extraction using patterns from config)
- **Document validator** (required fields, format checks, Verhoeff
  checksum for Aadhaar, date validation)
- **Streamlit OCR display** (grayscale image input, expanded results,
  status/error handling)
- **Streamlit validation display** (check results table, findings list)
- **Image anomaly analyzer** (ELA, edge density, noise analysis — heuristic,
  not ML)
- **Streamlit anomaly display** (indicator table, ELA image, anomaly score)
- **Cross-document consistency** (normalized name/DOB comparison across
  document types — deterministic, not ML)
- **Rule-based risk scoring** (weighted aggregation of validation, tampering,
  and consistency findings — heuristic, not probability)
- **Explainable screening report** (risk indicators, score, level,
  recommendation)

### No modules remain in stub form.

All core analysis modules are now implemented.

Future AI agents must inspect the actual source code before claiming any
feature is implemented.

## Implementation Details — Phase 2

### OCR Engine (src/ocr/engine.py)

- Wraps EasyOCR with lazy initialization (no model download at import).
- Returns structured results: text, confidence, per-region details, bbox.
- Filters regions below OCR_CONFIDENCE_THRESHOLD (0.3).
- Confidence is character-weighted average across accepted regions.
- Handles None images, empty results, and EasyOCR exceptions.
- All unit tests mock easyocr.Reader — no model downloads in test suite.

### Document Detector (src/documents/detector.py)

- Rule-based keyword-frequency heuristic — NOT a trained ML classifier.
- Uses word-boundary matching for single-word keywords to avoid false
  substring positives (e.g., "pan" does not match "company").
- Uses phrase matching for multi-word keywords.
- Requires >= 2 keyword hits to report a match.
- Returns confidence as matched_count / total_keywords.

### Field Extractor (src/documents/extractor.py)

- Applies regex patterns defined in config.py for each document type.
- Extraction confidence is set to 0.7 (EXTRACTION_CONFIDENCE), NOT 1.0.
- A regex match does not prove the extracted value is correct — OCR text
  may contain errors and patterns may capture false positives.
- Confidence is a documented heuristic, NOT a calibrated probability.
- Handles unknown document types, empty text, and partial extraction.

## Initial Document Types

1. Aadhaar
2. PAN Card
3. Voter ID

The architecture allows additional document types by editing config.py.

## Planned Workflow

User → Upload document(s) → Image preprocessing → Document type detection
→ OCR → Field extraction → Document validation → Tampering/anomaly analysis
→ Cross-document consistency → Risk engine → Explainable result → Human
review recommendation

## Current Technology Direction

- Python
- Streamlit
- OpenCV
- EasyOCR
- NumPy
- Pandas
- Pillow
- scikit-learn where useful
- SQLite

EasyOCR was selected during initial planning because installation simplicity
was prioritized for the Windows development environment.

## Deferred Feature

Face verification should remain optional/deferred unless it can be implemented
reliably within the 10-day hackathon.

## Risk Model

Risk levels: LOW, MEDIUM, HIGH

The risk engine should initially be explainable and rule-based.

Risk scores are indicators, not proof of fraud and not calibrated
probabilities.

## Privacy

Documents may contain highly sensitive identity information.

The MVP should:

- process documents locally where possible
- avoid third-party document uploads
- avoid logging complete identity numbers
- avoid permanently storing raw documents unless necessary
- mask sensitive fields in the UI
- clearly label synthetic test data

## Current Environment

Development environment is Windows.
Python 3.13.2
Virtual environment in venv/

## Current Project Location

C:\Users\kadam\Documents\SIH26188\sih26188-fake-identity-screening

## Git Status

GitHub remote configured (origin/main).
Project has commits and is synced.

## Current Test Status

219/262 tests passed (43 new hardening tests added in Phase 7, 0 regressions).

- tests/test_db.py — 10 tests (database)
- tests/test_preprocessing.py — 11 tests (image preprocessing)
- tests/test_validators.py — 16 tests (interface contracts, all real)
- tests/test_ocr.py — 14 tests (OCR wrapper, mocked)
- tests/test_detector.py — 17 tests (document detection)
- tests/test_extractor.py — 21 tests (field extraction)
- tests/test_document_validator.py — 48 tests (Phase 3 validation)
- tests/test_integration.py — 6 tests (full pipeline + Phase 5 integration)
- tests/test_tampering.py — 33 tests (Phase 4 tampering/anomaly)
- tests/test_consistency.py — 22 tests (Phase 5 cross-document consistency)
- tests/test_risk_scoring.py — 21 tests (Phase 5 risk scoring)

All OCR tests use mocked easyocr.Reader. No model downloads required
to run the test suite. No internet access required.

A separate manual test script (tests/manual_ocr_test.py) tests the
full pipeline with real EasyOCR, including validation.

## Implementation Details — Phase 2.5

### Streamlit OCR UI Integration (app.py)

- Changed OCR input from binary-threshold image to grayscale for EasyOCR.
  Thresholding destroys gradient information that EasyOCR models need.
- Expanded OCR results section by default (was collapsed).
- Added proper status handling (success, no_text, error) in display.
- Added per-region confidence and count display.
- Updated stale "pending implementation" messages.

## Implementation Details — Phase 3

### Document Validator (src/documents/validators.py)

- Replaced 50-line stub with 484-line full implementation.
- Required-field presence checks driven by config.py `required` flags.
- Format validation using config.py `pattern` regex values.
- Aadhaar Verhoeff checksum validation (structural only — does NOT
  prove the number exists or belongs to a person).
- Date validation: format parsing (DD/MM/YYYY, DD-MM-YYYY) and
  plausibility checks (year range 1900–current).
- Input normalization: space-stripping for Aadhaar, uppercasing for PAN/EPIC.
- Edge-case handling: None input, empty fields, unknown document type,
  raw string values, empty string values.
- Return schema preserves backward compatibility: checks, valid_count,
  total_count, all_passed, status, plus new fields: findings, document_type.
- Status values: success, partial, failed, error.
- Language: uses "structural validation", "suspicious indicator",
  "human review recommended" — never claims fraud or legal determination.

### Verhoeff Algorithm

- Implemented verhoeff_validate() and verhoeff_generate() functions.
- Standard Verhoeff tables (_VERHOEFF_D, _VERHOEFF_P, _VERHOEFF_INV).
- Detects single-digit substitution and transposition errors.
- A valid checksum only proves structural consistency, NOT that the
  Aadhaar number exists in any government database.

### Streamlit Validation Display (app.py)

- Validation results shown in a table with Check/Result/Details columns.
- Validation findings displayed as a bullet list.
- Handles error/empty/no-check states gracefully.
- Shows pass/fail count caption.

## Implementation Details — Phase 4

### Image Anomaly Analyzer (src/vision/tampering.py)

- Replaced 50-line stub with full implementation (~320 lines).
- Uses OpenCV-based heuristics — NOT a trained ML model.
- Three analysis techniques:
  1. Error Level Analysis (ELA): recompresses image as JPEG at configurable
     quality, computes pixel-level difference, amplifies and visualizes.
  2. Edge Density: Canny edge detection, measures ratio of edge to total
     pixels, flags unusually low or high values.
  3. High-Frequency Noise: subtracts Gaussian-blurred version to isolate
     noise, measures std deviation, flags abnormal levels.
- ELA is performed entirely in memory (no disk I/O for temporary files).
- Handles None, empty, too-small, grayscale, BGRA, and invalid input.
- Return schema preserves backward compatibility: checks, ela_image,
  overall_suspicious, suspicion_score, status.
- Added fields: method ("heuristic_cv"), message.
- Each check includes: name, description, result, suspicious, details,
  and optional metrics dict.

### Heuristic Anomaly Score

- Score = suspicious_check_count / total_checks (deterministic).
- This is NOT a probability of fraud or a calibrated confidence value.
- Overall_suspicious is true when score >= configurable threshold (0.4).
- Score calculation is transparent and explainable.

### Configuration (src/config.py)

- All thresholds centralized in TAMPERING dict:
  ela_jpeg_quality, ela_scale_factor, ela_suspicious_threshold,
  edge_density_low, edge_density_high, noise_std_suspicious,
  min_image_dimension, overall_suspicious_threshold.

### Streamlit Anomaly Display (app.py)

- Indicator results shown in table with Indicator/Status/Details columns.
- ELA visualization displayed with descriptive caption.
- Overall status shown as success/warning message.
- Shows heuristic anomaly score, method, and suspicious status.
- Updated section title from "Tampering / Anomaly Analysis" to
  "Image Anomaly Analysis".
- Handles error and empty states gracefully.

## Implementation Details — Phase 5

### Cross-Document Consistency (src/verification/consistency.py)

- Replaced 55-line stub with ~225-line full implementation.
- Deterministic normalized comparison — NOT machine learning.
- Comparable fields: name, date of birth.
- Name normalization: lowercase, collapse whitespace, remove common punctuation.
- Date normalization: supports DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD formats.
- Handles dict-style field values ({value, confidence}) and plain strings.
- Handles None input, empty list, single document, missing fields, empty values.
- Single document returns "insufficient_documents" — NOT marked as inconsistent.
- Return schema: checks, consistent, consistency_score, status, message,
  compared_count, mismatch_count.
- Each check: field, field_label, documents_compared, consistent, message, values.
- Language: "may warrant human review", "does not guarantee authenticity".

### Rule-Based Risk Scoring (src/risk/scoring.py)

- Replaced 59-line stub with ~280-line full implementation.
- Deterministic weighted rule system — NOT trained ML, NOT probability.
- Inputs: validation results, tampering results, consistency results.
- Scoring: sub-scores (0.0-1.0) for validation, tampering, consistency,
  weighted by config RISK_WEIGHTS and normalized.
- When consistency data is unavailable, its weight is redistributed to
  available components.
- Score range: 0.0-1.0 (also reported as 0-100 integer).
- Risk levels: LOW (score <= 0.3), MEDIUM (0.3 < score <= 0.6), HIGH (> 0.6).
- Explainability: every risk contribution has category, name, contribution,
  description.
- Human-readable indicators list and recommendation per level.
- Language: "suspicious indicators", "human review recommended" — never
  "fraud", "fake", "forged", "reject".

### Streamlit Integration (app.py)

- Pipeline restructured: risk scoring deferred until after consistency check.
- Consistency check runs on all documents after per-document analysis loop.
- Risk scoring receives consistency results for each document's score.
- Cross-document consistency display: table with Field/Status/Details columns.
- Risk display updated: "Screening Assessment" with heuristic score (N/100),
  risk badge, indicators list, recommendation, disclaimer.
- DB record includes consistency status alongside existing fields.

## Next Major Development Task

All core analysis modules are now implemented. Potential next steps:
- UI polish and user experience improvements
- Production hardening (error recovery, logging, performance)
- Optional face detection for photo documents
- Reporting and export features
- Documentation for end users
