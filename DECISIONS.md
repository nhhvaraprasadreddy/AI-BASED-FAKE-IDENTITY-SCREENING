# ARCHITECTURAL DECISIONS

## Decision 001 � MVP First

### Decision

Prioritize a reliable end-to-end demonstration over theoretical sophistication.

### Reason

The project has approximately 10 days and is being developed by
beginner/intermediate developers.

Complex infrastructure and large model training are out of scope.

---

## Decision 002 � Local-First Processing

### Decision

Process identity documents locally whenever practical.

### Reason

Identity documents contain sensitive personal information.

The MVP should avoid unnecessary external document-processing services.

---

## Decision 003 � Streamlit

### Decision

Use Streamlit for the MVP interface.

### Reason

It allows rapid development of a professional demonstration UI without
requiring a separate frontend/backend stack.

---

## Decision 004 � OpenCV

### Decision

Use OpenCV for image preprocessing and visual analysis.

### Reason

It is mature, widely used, and suitable for the required MVP image-processing
tasks.

---

## Decision 005 � EasyOCR

### Decision

Initial OCR direction is EasyOCR.

### Reason

The original development session prioritized installation reliability and
simplicity on Windows.

The OCR implementation should remain replaceable.

If EasyOCR becomes technically unsuitable, evaluate the simplest compatible
alternative rather than forcing it.

---

## Decision 006 � Initial Document Types

### Decision

Start with:

- Aadhaar
- PAN Card
- Voter ID

### Reason

The hackathon requires a small demonstrable scope.

The architecture should allow additional document types later.

---

## Decision 007 � Rule-Based Risk Engine

### Decision

Use an explainable rule-based risk engine for the initial MVP.

### Reason

A rule-based system is transparent, testable, and achievable within the
10-day timeline.

The score represents screening indicators, not a calibrated probability.

---

## Decision 008 � Face Verification Deferred

### Decision

Face verification is optional and should be deferred unless it can be
implemented reliably within the remaining time.

### Reason

It can introduce substantial model, dependency, and image-quality complexity.

Core document screening has higher MVP priority.

---

## Decision 009 � Git as Project Memory

### Decision

Git and GitHub should be treated as the source of truth for project code and
development history.

### Reason

The project must remain usable if:

- Antigravity quota is exhausted
- the AI account changes
- another AI coding tool is used
- another developer takes over
- development moves to another computer

AI conversation history must not be the only source of project context.

---

## Decision 010 � AI Continuity Documentation

### Decision

Maintain:

- AGENTS.md
- PROJECT_CONTEXT.md
- ARCHITECTURE.md
- TODO.md
- DECISIONS.md
- CHANGELOG.md

### Reason

These files provide persistent context that any compatible AI agent can read
from the repository.

---

## Decision 011 � No Fake AI Results

### Decision

The application must never generate random, fabricated, or hardcoded fraud
results as if they came from real analysis.

### Reason

The project must remain technically honest and demonstrable.

Synthetic data may be used for testing, but must be clearly identified.

---

## Decision 012 � Human Review

### Decision

High-risk screening results must recommend human review.

### Reason

The system is a screening aid and must not claim definitive legal or
fraudulent-person determinations.

---

## Decision 013 � No Real Identity Documents in Git

### Decision

Real Aadhaar, PAN, Voter ID, or other sensitive identity documents must never
be committed to GitHub.

### Reason

The repository may be shared with judges, teammates, or external developers.

Synthetic or explicitly safe test data should be used instead.

---

## Decision 014 - Mocked OCR Tests

### Decision

All OCR unit tests mock easyocr.Reader. The normal test suite (pytest tests/ -v)
must work without internet access and without downloading OCR model weights.

### Reason

The baseline test suite must remain fast and reliable. Model downloads add
~100 MB of network traffic and significant latency. Tests should validate
the wrapper logic, not the underlying OCR library.

Real EasyOCR integration testing is done manually or via clearly separated
optional tests.

---

## Decision 015 - Extraction Confidence is Not 1.0

### Decision

Regex-based field extraction assigns a heuristic confidence of 0.7
(EXTRACTION_CONFIDENCE), not 1.0, to every extracted field.

### Reason

A regex match confirms a pattern was found in OCR text, but it does not
prove the extracted value is correct. OCR noise, misreads, and regex
over-matching mean extracted values may be wrong. 1.0 would falsely
imply certainty. The 0.7 value is a documented heuristic, not a
calibrated probability.

---

## Decision 016 - Word-Boundary Document Detection

### Decision

The document type detector uses word-boundary regex matching for single
keywords (e.g., \bpan\b) to prevent false substring matches. Multi-word
phrases use plain substring matching after normalization.

### Reason

Naive substring matching causes false positives. For example, the keyword
"pan" would incorrectly match "company" or "pandemic". Word-boundary
matching prevents this while still being simple and fast. This is a
rule-based heuristic, not a trained ML classifier.

---

## Decision 017 - Verhoeff Checksum is Structural Only

### Decision

The Aadhaar Verhoeff checksum validator only confirms structural consistency
of the 12-digit number. A valid checksum does NOT prove that the number
exists in any government database or belongs to any person.

### Reason

The project must avoid implying external verification. The Verhoeff algorithm
is a mathematical check-digit algorithm. Passing it is a necessary but not
sufficient condition for a legitimate Aadhaar number. This distinction must
be clearly communicated in all validation messages and documentation.

---

## Decision 018 - Validation Language

### Decision

Validation results use careful language: "structural validation failed",
"suspicious indicator", "potential validation issue", "human review
recommended". The system never claims "fraud detected", "document is fake",
or "person is fraudulent".

### Reason

The system is a screening aid, not a legal authority. Validation failures
are indicators that warrant human review, not proof of fraud or forgery.
This is consistent with the project's core ethical principle (Decision 012).

---

## Decision 019 - Deterministic Validation (No Invented Confidence)

### Decision

Validation checks produce deterministic passed/failed results, not
probability scores. The validator does not invent statistical confidence
values for rule-based checks.

### Reason

A regex match or Verhoeff checksum result is binary. Attaching a fabricated
probability to a deterministic check would be misleading. Validation
results use clear fields: passed, failed, status, check_name, message.

---

## Decision 020 - OCR Image Input (Grayscale for EasyOCR)

### Decision

The OCR pipeline uses the preprocessed grayscale image (not the
adaptive-threshold binary image) as input to EasyOCR.

### Reason

EasyOCR works poorly on hard-binarised images because thresholding destroys
the gradient information its internal models need. Grayscale preserves
enough visual structure for reliable text recognition while still
benefiting from denoising.
---

## Decision 021 - ELA is a Heuristic Indicator

### Decision

Error Level Analysis (ELA) is implemented as a heuristic screening indicator.
A high ELA response does NOT prove image editing. Normal images may show
elevated ELA values due to JPEG compression artifacts, edges, textures,
or format conversion.

### Reason

ELA measures compression inconsistency, which correlates with but does not
prove image manipulation. Presenting ELA as definitive proof would be
technically dishonest. Results must be accompanied by disclaimers and
recommended for human review.

---

## Decision 022 - Anomaly Score is Not a Fraud Probability

### Decision

The heuristic anomaly score is calculated as suspicious_count / total_checks.
It is a deterministic ratio, NOT a calibrated probability of fraud.

### Reason

The score aggregates binary check results. It has no statistical calibration,
training data, or validation against a ground-truth dataset. Calling it a
probability would be misleading. It is described as a "heuristic anomaly
score" throughout the codebase and documentation.

---

## Decision 023 - No External Verification for Tampering

### Decision

Image analysis is performed locally using OpenCV. No images are sent to
external APIs, cloud services, or third-party verification endpoints.

### Reason

Identity documents are sensitive. Local processing avoids privacy risks
from transmitting document images over the network. This is consistent
with the project's local-first philosophy (Decision 002).

---

## Decision 024 - Tampering Thresholds in Config

### Decision

All tampering analysis thresholds are centralized in the TAMPERING dict
in src/config.py rather than hardcoded in the analyzer.

### Reason

Centralizing thresholds makes them discoverable, adjustable, and
documentable without modifying analysis logic. This follows the same
pattern used for OCR and preprocessing configuration.
---

## Decision 025 - Deterministic Rule-Based Risk Scoring

### Decision

The risk engine uses a deterministic weighted rule system. It is NOT a
trained ML model, NOT a probability model, and NOT statistically calibrated.
The score is explicitly labeled "heuristic screening score" throughout.

### Reason

The team has no training data, no validation dataset, and no calibration
methodology. Calling a weighted sum of heuristic indicators a probability
would be technically dishonest. A transparent deterministic approach is
more appropriate for a hackathon MVP.

---

## Decision 026 - Missing Data Does Not Equal Fraud

### Decision

When cross-document consistency data is unavailable (single document upload),
the consistency weight is redistributed to other components rather than
penalizing the score. Missing fields or unavailable analysis modules produce
zero risk contribution, not a penalty.

### Reason

A user uploading a single document is the normal case. It would be incorrect
to raise a risk score simply because consistency data is absent. Similarly,
OCR failures or missing fields should not be treated as evidence of fraud.

---

## Decision 027 - Normalized Name Comparison

### Decision

Cross-document name comparison uses simple deterministic normalization:
lowercase, collapse whitespace, remove common punctuation (., -, ,).
No fuzzy matching library is used.

### Reason

Simple normalization handles the most common legitimate variations
(case differences, extra spaces, punctuation) without introducing
false matches from aggressive fuzzy matching. If fuzzy matching is
needed later, it can be added with a configurable threshold.

---

## Decision 028 - Human Review Is Final Decision Point

### Decision

The system recommends human review for all risk levels. It never
recommends rejecting an applicant, confirming fraud, or making
legal determinations.

### Reason

This is a screening tool. The final decision about a person's identity
or a document's authenticity must be made by a trained human reviewer
using authorized verification channels. Automated rejection would be
both technically unjustified and ethically inappropriate.
## Decision 029 - Tabbed Results Layout

### Decision
Reorganize the screening results into 4 tabs: Screening Assessment, Fields & Validation, Image Analysis, Details.

### Rationale
A single scrolling page with all results is overwhelming for demos. Tabs reduce cognitive load while keeping all information accessible. The risk score hero display stays above tabs so the headline result is always visible.

### Status
Implemented � Phase 6

## Decision 030 - JSON Report Export

### Decision
Provide a downloadable JSON screening report using Streamlit's built-in download_button. No PDF dependencies.

### Rationale
JSON is lightweight, requires no new dependencies, preserves structured data, and can be parsed by other tools. PDF would require additional libraries (e.g., reportlab, fpdf) which increases project complexity for a hackathon prototype.

### Status
Implemented � Phase 6

## Decision 031 - User-Friendly Error Categorization

### Decision
Categorize pipeline errors into specific types (image read errors, memory errors, unexpected errors) with beginner-friendly messages. Technical details are available in a collapsed expander.

### Rationale
Raw tracebacks confuse non-technical users during demos. Categorized messages help users understand what went wrong and what to try next. Technical details remain accessible for debugging.

### Status
Implemented � Phase 6
## Decision 032 - Structural Pattern Evidence for Detection

### Decision
Add structural identifier pattern matching alongside keyword detection. Each document type has a characteristic identifier pattern (Aadhaar: 12-digit, PAN: XXXXX0000X, Voter ID: XXX0000000) that counts as one additional evidence hit.

### Rationale
OCR on documents with Hindi/regional text may not produce enough English keyword matches. Structural patterns provide language-independent evidence that helps reach the minimum detection threshold without replacing or weakening the keyword system.

### Status
Implemented — Phase 7

## Decision 033 - Hardening Over Features

### Decision
Phase 7 adds zero new features. All changes focus on robustness testing, edge-case coverage, and documentation. 43 new tests were added covering detection, extraction, tampering, risk scoring, and database edge cases.

### Rationale
The MVP has all required features from Phases 1–6. Adding more features increases risk of regressions. Hardening ensures demo reliability for SIH presentation.

### Status
Implemented — Phase 7