# 🛡️ AI Document Screening System — SIH26188

![SIH26188](https://img.shields.io/badge/SIH-26188-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11+-green.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

> **AI-Based Fake Identity & Document Screening System** — Smart India Hackathon 2026 Project

An intelligent screening tool that analyzes identity documents and identifies potential fraud indicators through OCR, computer vision, and rule-based validation. The system produces **explainable risk assessments** for human review — it does **not** make legal determinations about document authenticity.

---

## ✨ Features

| Feature | Status | Description |
|---------|--------|-------------|
| Document Upload | ✅ Active | Multi-file upload (JPG, PNG, BMP, TIFF) |
| Image Preprocessing | ✅ Active | Resize, denoise, grayscale, deskew, adaptive threshold |
| OCR Text Extraction | 🔜 Phase 2 | EasyOCR integration (English + Hindi) |
| Document Type Detection | 🔜 Phase 2 | Keyword-based detection (Aadhaar, PAN, Voter ID) |
| Field Extraction | 🔜 Phase 2 | Regex-based identity field extraction |
| Field Validation | 🔜 Phase 2 | Format checks, Verhoeff checksum, date validation |
| Tampering Analysis | 🔜 Phase 3 | Error Level Analysis (ELA), metadata checks |
| Risk Scoring | 🔜 Phase 3 | Weighted rule-based risk engine |
| Cross-Doc Consistency | 🔜 Phase 4 | Name/DOB matching across documents |
| Screening History | ✅ Active | SQLite-backed screening log |
| Privacy Controls | ✅ Active | Field masking, local processing, privacy notice |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or compatible version
- pip (Python package manager)

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd sih26188-fake-identity-screening

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`.

> **Note:** On first run, EasyOCR will download language models (~100 MB). This is a one-time cost.

---

## 📄 Supported Document Types

| Document | ID Format | Key Fields |
|----------|-----------|------------|
| **Aadhaar Card** | 12 digits (XXXX XXXX XXXX) | Aadhaar Number, Name, DOB, Gender |
| **PAN Card** | 10 chars (ABCDE1234F) | PAN Number, Name, Father's Name, DOB |
| **Voter ID (EPIC)** | 3 letters + 7 digits | EPIC Number, Name, Father's Name, DOB |

The architecture supports adding new document types by editing `src/config.py` — no core code changes required.

---

## 📁 Project Structure

```
sih26188-fake-identity-screening/
│
├── app.py                          # Streamlit entry point
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── .gitignore
│
├── .streamlit/
│   └── config.toml                 # Dark theme configuration
│
├── src/
│   ├── __init__.py
│   ├── config.py                   # Centralized config & document type definitions
│   │
│   ├── ocr/
│   │   ├── __init__.py
│   │   └── engine.py               # OCR abstraction (EasyOCR wrapper)
│   │
│   ├── documents/
│   │   ├── __init__.py
│   │   ├── detector.py             # Document type identification
│   │   ├── extractor.py            # Regex-based field extraction
│   │   └── validators.py           # Field format & checksum validation
│   │
│   ├── vision/
│   │   ├── __init__.py
│   │   ├── preprocessing.py        # Image preprocessing pipeline
│   │   └── tampering.py            # ELA & anomaly analysis
│   │
│   ├── verification/
│   │   ├── __init__.py
│   │   └── consistency.py          # Cross-document consistency checks
│   │
│   ├── risk/
│   │   ├── __init__.py
│   │   └── scoring.py              # Weighted risk scoring engine
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   └── db.py                   # SQLite screening history
│   │
│   └── utils/
│       ├── __init__.py
│       └── helpers.py              # Masking, formatting, logging
│
├── data/
│   ├── samples/                    # Test data (clearly labeled)
│   └── db/                         # SQLite databases (runtime)
│
└── tests/
    ├── __init__.py
    ├── test_preprocessing.py
    ├── test_db.py
    └── test_validators.py
```

---

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| UI | Streamlit | Interactive web dashboard |
| Image Processing | OpenCV | Preprocessing, ELA, contour detection |
| OCR | EasyOCR | Text extraction (English + Hindi) |
| Database | SQLite | Local screening history persistence |
| Validation | Regex, Verhoeff | Format checks, checksum verification |
| ML (optional) | scikit-learn | Statistical anomaly scoring |
| Language | Python 3.11+ | Core development language |

---

## 🔒 Privacy

- All document processing is performed **locally** — no data is sent to external services
- Sensitive fields (Aadhaar numbers, PAN numbers) are **masked** in the UI
- Screening history stores analysis results only, **not** original document images
- All screening records can be deleted from the history
- File hashes (not files) are stored for deduplication

---

## ⚠️ Disclaimer

This is a **screening tool** that identifies potential indicators of concern. It does **not**:
- Make legal determinations about document authenticity
- Determine whether a person's identity is genuine
- Provide statistically calibrated fraud probabilities

All findings require **human review** and verification through authorized channels. Suspicion scores are heuristic indicators derived from rule-based analysis, not proof of fraud.

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 📋 Risk Levels

| Level | Score Range | Meaning |
|-------|-----------|---------|
| 🟢 LOW | 0.0 – 0.3 | No significant indicators of concern |
| 🟡 MEDIUM | 0.3 – 0.6 | Some indicators warrant review |
| 🔴 HIGH | 0.6 – 1.0 | Multiple indicators — recommend detailed human review |

---

## 👥 Team

*Smart India Hackathon 2026 — Team SIH26188*

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
