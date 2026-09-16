"""Centralized configuration for the SIH26188 screening system.

All document type definitions, risk scoring parameters, and application
settings are defined here. To add a new document type, add an entry to
DOCUMENT_TYPES with the required fields.
"""
from __future__ import annotations

import os
from pathlib import Path

# ── Application ──────────────────────────────────────────────────────────────
APP_NAME = "AI Document Screening System"
APP_VERSION = "0.2.1"
APP_DESCRIPTION = "AI-powered identity document screening, OCR, validation, and risk analysis"

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_DIR = DATA_DIR / "db"
SAMPLES_DIR = DATA_DIR / "samples"

# ── Database ─────────────────────────────────────────────────────────────────
DB_PATH = str(DB_DIR / "screenings.db")

# ── Preprocessing ────────────────────────────────────────────────────────────
PREPROCESSING = {
    "max_dimension": 1024,
    "denoise_strength": 10,
    "denoise_color_strength": 10,
    "adaptive_threshold_block_size": 11,
    "adaptive_threshold_c": 2,
}

# ── OCR ──────────────────────────────────────────────────────────────────────
OCR_LANGUAGES: list[str] = ["en", "hi"]  # English + Hindi for Indian documents
OCR_CONFIDENCE_THRESHOLD: float = 0.3

# ── Tampering / Anomaly Analysis ─────────────────────────────────────────────
TAMPERING = {
    "ela_jpeg_quality": 90,           # JPEG quality for ELA recompression
    "ela_scale_factor": 20,           # Amplification factor for ELA diff
    "ela_suspicious_threshold": 15.0, # Mean ELA value above which region is suspicious
    "edge_density_low": 0.02,         # Below this = suspiciously low edge content
    "edge_density_high": 0.35,        # Above this = suspiciously high edge content
    "noise_std_suspicious": 30.0,     # High-frequency noise std above which = suspicious
    "min_image_dimension": 20,        # Minimum width/height to attempt analysis
    "overall_suspicious_threshold": 0.4,  # Heuristic score above which = suspicious
}

# ── Document Type Definitions ────────────────────────────────────────────────
DOCUMENT_TYPES: dict = {
    "aadhaar": {
        "name": "Aadhaar Card",
        "description": "Unique Identification Authority of India",
        "keywords": [
            "aadhaar", "\u0906\u0927\u093e\u0930", "uidai",
            "unique identification authority",
            "government of india", "\u092d\u093e\u0930\u0924 \u0938\u0930\u0915\u093e\u0930",
        ],
        "fields": {
            "aadhaar_number": {
                "label": "Aadhaar Number",
                "pattern": r"\d{4}\s?\d{4}\s?\d{4}",
                "format_description": "12 digits (XXXX XXXX XXXX)",
                "sensitive": True,
                "required": True,
            },
            "name": {
                "label": "Name",
                "pattern": r"(?:Name|\u0928\u093e\u092e)\s*[:;\-]?\s*([A-Za-z\s]+)",
                "format_description": "Full name in English",
                "sensitive": False,
                "required": True,
            },
            "dob": {
                "label": "Date of Birth",
                "pattern": r"(?:DOB|Date of Birth|\u091c\u0928\u094d\u092e\s*\u0924\u093f\u0925\u093f)\s*[:;\-]?\s*(\d{2}[/\-]\d{2}[/\-]\d{4})",
                "format_description": "DD/MM/YYYY",
                "sensitive": False,
                "required": False,
            },
            "gender": {
                "label": "Gender",
                "pattern": r"(?:Male|Female|Transgender|\u092a\u0941\u0930\u0941\u0937|\u092e\u0939\u093f\u0932\u093e)",
                "format_description": "Male/Female/Transgender",
                "sensitive": False,
                "required": False,
            },
        },
        "checksum_field": "aadhaar_number",
        "checksum_algorithm": "verhoeff",
    },
    "pan": {
        "name": "PAN Card",
        "description": "Permanent Account Number — Income Tax Department, India",
        "keywords": [
            "income tax", "permanent account number",
            "pan", "\u0906\u092f\u0915\u0930", "it department",
            "govt. of india", "india",
        ],
        "fields": {
            "pan_number": {
                "label": "PAN Number",
                "pattern": r"([A-Z] ?[A-Z] ?[A-Z] ?[A-Z] ?[A-Z] ?[0-9] ?[0-9] ?[0-9] ?[0-9] ?[A-Z])",
                "format_description": "10 characters (ABCDE1234F)",
                "sensitive": True,
                "required": True,
            },
            "name": {
                "label": "Name",
                "pattern": r"(?:Name|\u0928\u093e\u092e)\s*[:;\-]?\s*([A-Z][A-Za-z\s]+)",
                "format_description": "Full name in uppercase",
                "sensitive": False,
                "required": True,
            },
            "father_name": {
                "label": "Father's Name",
                "pattern": r"(?:Father|\u092a\u093f\u0924\u093e)\s*['\"]?s?\s*(?:Name)?\s*[:;\-]?\s*([A-Z][A-Za-z\s]+)",
                "format_description": "Father's full name",
                "sensitive": False,
                "required": False,
            },
            "dob": {
                "label": "Date of Birth",
                "pattern": r"(\d{2}[/\-]\d{2}[/\-]\d{4})",
                "format_description": "DD/MM/YYYY",
                "sensitive": False,
                "required": False,
            },
        },
        "checksum_field": None,
        "checksum_algorithm": None,
    },
    "voter_id": {
        "name": "Voter ID (EPIC)",
        "description": "Election Commission of India — Electoral Photo Identity Card",
        "keywords": [
            "election commission", "electoral",
            "epic", "voter", "\u0928\u093f\u0930\u094d\u0935\u093e\u091a\u0928 \u0906\u092f\u094b\u0917",
            "photo identity card", "electors",
        ],
        "fields": {
            "epic_number": {
                "label": "EPIC Number",
                "pattern": r"[A-Z]{3}\d{7}",
                "format_description": "3 letters + 7 digits (ABC1234567)",
                "sensitive": True,
                "required": True,
            },
            "name": {
                "label": "Name",
                "pattern": r"(?:Name|Elector|\u0928\u093e\u092e)\s*[:;\-]?\s*([A-Za-z\s]+)",
                "format_description": "Full name",
                "sensitive": False,
                "required": True,
            },
            "father_name": {
                "label": "Father's/Husband's Name",
                "pattern": r"(?:Father|Husband|\u092a\u093f\u0924\u093e|\u092a\u0924\u093f)\s*['\"]?s?\s*(?:Name)?\s*[:;\-]?\s*([A-Za-z\s]+)",
                "format_description": "Father's or husband's name",
                "sensitive": False,
                "required": False,
            },
            "dob": {
                "label": "Date of Birth",
                "pattern": r"(?:DOB|Date of Birth|Age)\s*[:;\-]?\s*(\d{2}[/\-]\d{2}[/\-]\d{4})",
                "format_description": "DD/MM/YYYY",
                "sensitive": False,
                "required": False,
            },
        },
        "checksum_field": None,
        "checksum_algorithm": None,
    },
}

# ── Risk Scoring ─────────────────────────────────────────────────────────────
RISK_WEIGHTS: dict[str, float] = {
    "field_validation": 0.30,
    "format_compliance": 0.20,
    "tampering_analysis": 0.35,
    "consistency": 0.15,
}

RISK_THRESHOLDS: dict[str, float] = {
    "low_max": 0.3,
    "medium_max": 0.6,
}

RISK_LEVELS: dict[str, dict] = {
    "LOW": {"label": "Low Risk", "color": "#28a745", "icon": "\u2705"},
    "MEDIUM": {"label": "Medium Risk", "color": "#ffc107", "icon": "\u26a0\ufe0f"},
    "HIGH": {"label": "High Risk", "color": "#dc3545", "icon": "\U0001f6a8"},
}

# ── Privacy ───────────────────────────────────────────────────────────────────
PRIVACY_NOTICE: str = """
**Privacy Notice**

This system processes identity documents locally on this machine.
- Documents are **not** uploaded to any external service.
- Sensitive fields (Aadhaar numbers, PAN numbers) are masked in the display.
- Screening history stores analysis results only, not original document images.
- All screening records can be deleted from the history.

This is a screening tool that identifies potential indicators of concern.
It does **not** make legal determinations about document authenticity or identity.
All findings require human review and verification through authorized channels.
"""
