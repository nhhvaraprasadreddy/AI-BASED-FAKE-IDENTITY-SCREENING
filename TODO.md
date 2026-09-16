# TODO

## Current Phase

PHASE 7 COMPLETE — FINAL HARDENING (v0.2.1)

## Completed

- [x] Initialize project structure
- [x] Create Streamlit application
- [x] Create SQLite persistence layer
- [x] Create image preprocessing module
- [x] Create initial module interfaces
- [x] Create initial tests
- [x] Verify Streamlit launches
- [x] Verify test suite passes
- [x] Initialize Git repository
- [x] Create AI continuity documentation
- [x] Integrate EasyOCR
- [x] Implement document type detection (keyword heuristic)
- [x] Implement field extraction (regex-based)
- [x] Add OCR tests (mocked — no model downloads in test suite)
- [x] Add document detection tests
- [x] Add field extraction tests
- [x] Update interface contract tests
- [x] Fix OCR image input (grayscale instead of threshold)
- [x] Fix OCR display in Streamlit (expanded, status handling)
- [x] Update stale "pending implementation" messages
- [x] Add integration tests (mocked full pipeline)
- [x] Create manual real-EasyOCR test script
- [x] Test real OCR on synthetic document image
- [x] Implement Aadhaar field validation (Verhoeff checksum)
- [x] Implement PAN field validation (format checks)
- [x] Implement Voter ID field validation (format checks)
- [x] Implement required-field presence checks
- [x] Implement date validation (format + plausibility)
- [x] Implement field normalization before validation
- [x] Add comprehensive validator tests (48 tests, all synthetic data)
- [x] Add validation step to integration test
- [x] Add validation display to Streamlit UI (table + findings)
- [x] Update manual OCR test with validation step
- [x] Implement ELA (Error Level Analysis) — heuristic, not ML
- [x] Implement edge density analysis
- [x] Implement high-frequency noise analysis
- [x] Add anomaly display to Streamlit UI (indicator table, ELA image)
- [x] Add tampering configuration to config.py
- [x] Add comprehensive tampering tests (33 tests, all synthetic data)
- [x] Update tampering interface contract tests
- [x] Implement cross-document consistency checker
- [x] Implement rule-based risk scoring engine
- [x] Restructure app.py pipeline for consistency → risk flow
- [x] Add explainable screening display with indicators
- [x] Add comprehensive consistency tests (22 tests)
- [x] Add comprehensive risk scoring tests (21 tests)
- [x] Add Phase 5 integration tests (3 tests)
- [x] Update all interface contract tests from stubs to real
- [x] Phase 6: Add "How It Works" intro card
- [x] Phase 6: Restructure results into 4-tab layout
- [x] Phase 6: Add JSON screening report export/download
- [x] Phase 6: Add CSS for suspicious indicators and risk hero display
- [x] Phase 6: Improve error handling with categorized messages
- [x] Phase 6: Improve history page (4 metrics, structured findings, Clear All)
- [x] Phase 6: Enhance sidebar (risk distribution, pipeline overview)
- [x] Phase 6: Version bump to 0.2.0
- [x] Phase 7: Add structural pattern evidence to detector
- [x] Phase 7: Add 7 detector hardening tests
- [x] Phase 7: Add 10 extractor hardening tests (position independence)
- [x] Phase 7: Add 11 tampering hardening tests (PNG, recompression, boundaries)
- [x] Phase 7: Add 12 risk scoring hardening tests (boundaries, invariants)
- [x] Phase 7: Add 5 database hardening tests (edge cases, roundtrips)
- [x] Phase 7: Verify risk scoring single-doc behavior (no consistency penalty)
- [x] Phase 7: Version bump to 0.2.1

## Day 2 (remaining)

- [ ] Review and polish preprocessing
- [x] Review Streamlit UI
- [x] Improve error handling
- [ ] Verify configuration management
- [ ] Prepare safe synthetic/test document data

## Day 3 (remaining)

- [x] Test OCR on representative sample images (manual integration test)
- [ ] Tune OCR confidence threshold if needed
- [ ] Improve document type detection accuracy if needed

## Day 4 (complete)

- [x] Implement Aadhaar field validation (Verhoeff checksum)
- [x] Implement PAN field validation (format checks)
- [x] Implement Voter ID field validation (format checks)
- [x] Add relevant tests

## Day 5 (partial)

- [x] Implement document validation pipeline
- [ ] Improve preprocessing for OCR
- [ ] Improve document type detection
- [x] Add validation findings to screening result

## Day 6 (complete)

- [x] Implement image anomaly/tampering analysis
- [x] Start with explainable OpenCV-based techniques
- [x] Avoid claiming tampering detection is definitive
- [x] Add tests

## Day 7 (complete)

- [x] Implement cross-document consistency
- [x] Compare extracted identity fields
- [x] Add explainable consistency findings
- [x] Add tests

## Day 8 (complete)

- [x] Implement rule-based risk scoring
- [x] Configure scoring weights centrally
- [x] Implement LOW/MEDIUM/HIGH levels
- [x] Generate explainable findings
- [x] Add human review recommendation
- [x] Add tests

## Day 9

- [ ] Integrate complete end-to-end screening workflow
- [ ] Improve screening history
- [ ] Improve privacy masking
- [ ] Add final error handling
- [ ] Run full test suite

## Day 10

- [ ] End-to-end testing
- [ ] Prepare safe demo/test cases
- [ ] Verify installation instructions
- [ ] Verify clean startup
- [ ] Verify GitHub repository
- [ ] Prepare hackathon demonstration
- [ ] Document limitations
- [ ] Final cleanup

## Optional / If Time Allows

- [ ] Face verification
- [ ] Additional document types
- [ ] More advanced computer-vision models
- [ ] Additional anomaly indicators

## Explicitly Avoid Unless Justified

- [ ] Training large models from scratch
- [ ] Complex distributed architecture
- [ ] Cloud infrastructure that is unnecessary for MVP
- [ ] Third-party document processing APIs
- [ ] Features that cannot be demonstrated locally
