# ARCHITECTURE

## System Purpose

SIH26188 is a local-first identity-document screening MVP.

The system analyzes uploaded identity documents, extracts information,
checks document/field consistency, identifies suspicious visual indicators,
calculates an explainable screening risk level, and recommends human review
when appropriate.

The system does not make a legal determination that a document is fake or
that a person is fraudulent.

## Architectural Style

The project uses a modular pipeline.

User Interface
    ?
Application Orchestration
    ?
Image Preprocessing
    ?
Document Detection
    ?
OCR
    ?
Field Extraction
    ?
Validation
    ?
Visual Anomaly Analysis
    ?
Cross-Document Consistency
    ?
Risk Scoring
    ?
Explainable Report
    ?
Persistence

Each major responsibility should remain independently testable.

## Current Directory Structure

sih26188-fake-identity-screening/
¦
+-- app.py
+-- requirements.txt
+-- README.md
+-- AGENTS.md
+-- PROJECT_CONTEXT.md
+-- ARCHITECTURE.md
+-- TODO.md
+-- DECISIONS.md
+-- CHANGELOG.md
+-- .gitignore
¦
+-- src/
¦   +-- __init__.py
¦   +-- config.py
¦   ¦
¦   +-- ocr/
¦   ¦   +-- __init__.py
¦   ¦   +-- engine.py
¦   ¦
¦   +-- documents/
¦   ¦   +-- __init__.py
¦   ¦   +-- detector.py
¦   ¦   +-- extractor.py
¦   ¦   +-- validators.py
¦   ¦
¦   +-- vision/
¦   ¦   +-- __init__.py
¦   ¦   +-- preprocessing.py
¦   ¦   +-- tampering.py
¦   ¦
¦   +-- verification/
¦   ¦   +-- __init__.py
¦   ¦   +-- consistency.py
¦   ¦
¦   +-- risk/
¦   ¦   +-- __init__.py
¦   ¦   +-- scoring.py
¦   ¦
¦   +-- database/
¦   ¦   +-- __init__.py
¦   ¦   +-- db.py
¦   ¦
¦   +-- utils/
¦       +-- __init__.py
¦       +-- helpers.py
¦
+-- data/
¦   +-- samples/
¦   +-- test_cases/
¦
+-- tests/

The exact structure may evolve if there is a strong technical reason.

## Module Responsibilities

### app.py

Streamlit presentation and application orchestration.

It should not contain the implementation of every screening algorithm.

### src/config.py

Central configuration.

Examples:

- application settings
- database path
- upload limits
- supported document types
- risk thresholds
- OCR configuration

Avoid hardcoded absolute paths.

### src/ocr/

Responsible for OCR engine integration.

The OCR implementation must expose a clean interface so that the OCR library
can be replaced without rewriting the rest of the application.

Current direction: EasyOCR.

### src/documents/detector.py

Determines the likely document type.

Initial target:

- Aadhaar
- PAN
- Voter ID

Detection should provide evidence/confidence information where appropriate.

It should not pretend to identify a document with certainty.

### src/documents/extractor.py

Converts OCR output into structured fields.

Examples may include:

- name
- date of birth
- document number
- address
- gender

Only fields relevant to the supported document should be extracted.

### src/documents/validators.py

Performs document-specific format and consistency checks.

Examples:

- expected field presence
- document number format
- checksum where applicable
- date format
- impossible values
- expected text patterns

Validation failures are suspicious indicators, not proof of fraud.

### src/vision/preprocessing.py

Image preparation for OCR and visual analysis.

Possible operations:

- resizing
- grayscale conversion
- denoising
- thresholding
- contrast improvement
- cropping

### src/vision/tampering.py

Analyzes visual anomalies.

Potential MVP techniques:

- image quality checks
- compression inconsistencies
- error-level analysis where appropriate
- suspicious regions
- metadata-related indicators where safely available

Results must be described as indicators.

### src/verification/consistency.py

Compares information across multiple submitted documents.

Examples:

- name mismatch
- date-of-birth mismatch
- inconsistent document information

### src/risk/scoring.py

Combines screening indicators into an explainable risk assessment.

Initial approach should be rule-based.

Example:

Indicator
    ?
Weight
    ?
Risk contribution
    ?
Total screening score
    ?
LOW / MEDIUM / HIGH

The score is not a probability unless genuine statistical calibration is later
implemented.

### src/database/db.py

SQLite persistence for screening history.

Do not permanently store raw identity documents unless explicitly required.

Avoid storing unnecessary sensitive information.

### src/utils/

Shared helper functions.

Do not place unrelated business logic here merely for convenience.

## Data Flow

A typical screening request should follow:

1. User uploads one or more documents.
2. Application validates file type and size.
3. Image is loaded safely.
4. Image preprocessing runs.
5. Document type is detected.
6. OCR extracts text.
7. Structured fields are extracted.
8. Document-specific validation runs.
9. Visual anomaly analysis runs.
10. Cross-document consistency is checked.
11. Risk engine combines findings.
12. Explainable report is generated.
13. Appropriate information is stored in screening history.
14. UI displays masked information and findings.

## Error Handling

Failures in one stage should be handled explicitly.

Examples:

- invalid image
- unreadable document
- OCR failure
- unsupported document
- missing field
- database failure

The application should provide a useful user-facing message without exposing
internal stack traces unnecessarily.

## Testing Strategy

Each major module should have unit tests.

The complete test suite should be run before significant commits.

Tests should verify behavior rather than merely checking that functions exist.

## Extensibility

New document types should preferably be implemented by adding document-specific
logic rather than rewriting the entire pipeline.

The architecture should allow:

- additional document detectors
- additional field extractors
- additional validators
- additional OCR engines
- additional anomaly-analysis techniques

## Security Boundary

The MVP is designed as a local-first prototype.

External APIs or cloud services must not be introduced silently.

If a future implementation requires an external service, it must be explicitly
documented, configurable, and privacy-reviewed.

## Current Architectural Status

The following modules are fully implemented:

- app.py — Streamlit UI and pipeline orchestration
- src/config.py — centralized configuration and document type definitions
- src/vision/preprocessing.py — OpenCV image preprocessing pipeline
- src/database/db.py — SQLite screening history (full CRUD)
- src/utils/helpers.py — privacy masking, formatting, logging
- src/ocr/engine.py — EasyOCR wrapper with lazy initialization
- src/documents/detector.py — keyword-frequency document type heuristic
- src/documents/extractor.py — regex-based field extraction
- src/documents/validators.py — document field validation (Verhoeff, format, dates)
- src/vision/tampering.py — image anomaly analysis (ELA, edge density, noise — heuristic CV)
- src/verification/consistency.py — cross-document consistency (normalized name/DOB comparison)
- src/risk/scoring.py — weighted rule-based risk scoring engine

All core analysis modules are now implemented. No stubs remain.

Future agents must inspect actual source code before claiming functionality
is implemented.
