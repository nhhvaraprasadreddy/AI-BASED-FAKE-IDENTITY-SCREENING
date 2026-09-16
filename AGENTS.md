# AI AGENT INSTRUCTIONS
# SIH26188 — AI-Based Fake Identity & Document Screening System

## ROLE

You are an AI software engineering agent working on an existing Smart India
Hackathon MVP.

You are NOT starting a new project.

The local repository, source code, tests, documentation, and Git history are
the source of truth.

## FIRST STEP — BEFORE MODIFYING CODE

Always inspect the existing project before making changes.

Read, in this order:

1. AGENTS.md
2. PROJECT_CONTEXT.md
3. ARCHITECTURE.md
4. TODO.md
5. DECISIONS.md
6. CHANGELOG.md
7. README.md

Then inspect the relevant source files and recent Git history.

Do not assume that a feature exists merely because it is mentioned in the
project requirements.

Verify the actual implementation.

## CORE DEVELOPMENT PRINCIPLES

- Build a working MVP first.
- Prefer simple and reliable solutions.
- Do not introduce unnecessary technologies.
- Do not rewrite working code unnecessarily.
- Preserve existing functionality when modifying modules.
- Keep functions reasonably small.
- Use clear names and type hints where practical.
- Centralize configuration.
- Avoid hardcoded absolute paths.
- Use proper error handling.
- Add tests for major functionality.
- Do not fabricate results.
- Do not fabricate accuracy metrics.
- Do not claim a heuristic is an AI/ML model.

## CURRENT TECHNOLOGY DIRECTION

Primary stack:

- Python
- Streamlit
- OpenCV
- EasyOCR
- NumPy
- Pandas
- Pillow
- scikit-learn where genuinely useful
- SQLite

Use pretrained models only when genuinely useful.

Do not train large models from scratch.

## SECURITY AND PRIVACY

Identity documents contain sensitive personal information.

Therefore:

- Process documents locally whenever possible.
- Never upload identity documents to external services unless explicitly
  configured and approved.
- Never log complete identity numbers.
- Never commit real identity documents to Git.
- Never commit API keys, passwords, tokens, or secrets.
- Mask sensitive information in the UI where appropriate.
- Keep uploaded documents temporary unless persistent storage is explicitly
  required.
- Clearly distinguish synthetic test documents from real documents.

## FRAUD-DETECTION DISCLAIMER

The system identifies suspicious indicators.

It does NOT legally determine:

- whether a person is fraudulent
- whether an identity belongs to a criminal
- whether a document is definitively fake

Risk scores are screening indicators for human review.

High-risk results must recommend human review.

Do not describe the risk score as a statistically calibrated probability
unless a genuine calibration process has been implemented and documented.

## AI/ML HONESTY

Clearly distinguish between:

1. OCR
2. Computer-vision analysis
3. Machine-learning models
4. Rule-based validation

Never replace a real implementation with fake or random results.

Demo/test data must be clearly labeled.

## CHANGE RULES

Before changing an existing module:

1. Read the entire relevant module.
2. Understand its current behavior.
3. Check its tests.
4. Identify dependencies.
5. Make the smallest reasonable change.
6. Run relevant tests.
7. Run the complete test suite when practical.

Never silently remove working functionality.

## GIT RULES

Use small, logical commits.

Before committing:

- Run tests.
- Review changed files.
- Ensure no secrets are included.
- Ensure no real identity documents are included.
- Ensure documentation reflects significant architectural changes.

Use descriptive commit messages.

## DOCUMENTATION CONTINUITY

After meaningful development:

- Update TODO.md.
- Update PROJECT_CONTEXT.md if project state changed.
- Update ARCHITECTURE.md if architecture changed.
- Update DECISIONS.md for important technical decisions.
- Update CHANGELOG.md for significant changes.

The project must always be understandable by another AI developer taking
over tomorrow.

## HANDOFF REQUIREMENT

At the end of a substantial development session, provide:

1. What was completed.
2. Files created.
3. Files modified.
4. Tests run and results.
5. Known issues.
6. Current task.
7. Next recommended task.

Then update the appropriate project documentation.

## 10-DAY HACKATHON RULE

Time is limited.

If a technically sophisticated feature cannot be implemented reliably within
the hackathon timeframe:

- Say so explicitly.
- Propose a simpler alternative.
- Prefer a reliable demonstrable MVP.

Do not spend excessive time optimizing theoretical sophistication.

## IMPORTANT

Do not proceed to major new features until the existing implementation is
understood.

Do not rebuild the project from scratch.

Continue the existing project.
