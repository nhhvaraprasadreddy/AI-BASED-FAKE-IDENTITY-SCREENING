"""SIH26188 — AI-Based Fake Identity & Document Screening System.

Streamlit entry point. Run with: streamlit run app.py
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
from datetime import datetime
from typing import Any

import numpy as np
import streamlit as st
from PIL import Image

from src.config import (
    APP_NAME,
    APP_VERSION,
    APP_DESCRIPTION,
    DOCUMENT_TYPES,
    RISK_LEVELS,
    PRIVACY_NOTICE,
    OCR_LANGUAGES,
    DB_PATH,
)
from src.utils.helpers import (
    setup_logging,
    mask_sensitive_field,
    format_risk_level,
    get_risk_color,
    format_timestamp,
)
from src.database.db import ScreeningDatabase
from src.vision.preprocessing import ImagePreprocessor
from src.ocr.engine import OCREngine
from src.documents.detector import DocumentDetector
from src.documents.extractor import FieldExtractor
from src.documents.validators import DocumentValidator
from src.vision.tampering import TamperingAnalyzer
from src.verification.consistency import ConsistencyChecker
from src.risk.scoring import RiskScorer

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = setup_logging("app")

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — professional dark‑themed security dashboard
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* ═══════════════════════════════════════════════════════════════════════
   MODERN SECURITY DASHBOARD
   ═══════════════════════════════════════════════════════════════════════ */
:root {
    --bg: #080b12;
    --panel: #101522;
    --panel-2: #141a29;
    --border: #263149;
    --muted: #8b97ad;
    --text: #f5f7fb;
    --blue: #4f9cff;
    --blue-2: #7c6cff;
    --green: #2dd4a8;
    --amber: #f6c453;
    --red: #ff5d73;
}

/* App background */
.stApp { background: radial-gradient(circle at 20% 0%, #111a32 0%, #080b12 38%, #080b12 100%); }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1450px; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0c111d 0%, #080b12 100%);
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.4rem; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 { color: var(--text); }
[data-testid="stSidebar"] .stRadio > label { color: var(--muted); }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] { gap: 7px; }
[data-testid="stSidebar"] .stRadio label {
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 8px 10px;
    transition: .2s ease;
}
[data-testid="stSidebar"] .stRadio label:hover { background: #151d2d; border-color: var(--border); }

/* Brand block */
.brand-card {
    padding: 16px 14px;
    border: 1px solid var(--border);
    border-radius: 16px;
    background: linear-gradient(145deg, #151d30, #0d121e);
    margin-bottom: 14px;
    box-shadow: 0 12px 35px rgba(0,0,0,.18);
}
.brand-icon {
    display: inline-flex; width: 40px; height: 40px; align-items: center; justify-content: center;
    border-radius: 12px; background: linear-gradient(135deg, var(--blue), var(--blue-2));
    font-size: 20px; margin-right: 10px; vertical-align: middle;
}
.brand-title { font-weight: 800; font-size: 1rem; color: var(--text); vertical-align: middle; }
.brand-sub { color: var(--muted); font-size: .75rem; margin-top: 9px; }

/* Hero */
.main-header {
    position: relative; overflow: hidden;
    background: linear-gradient(135deg, rgba(25,35,58,.96), rgba(14,19,31,.96));
    padding: 28px 30px;
    border: 1px solid #2b3a5a;
    border-radius: 20px;
    margin-bottom: 18px;
    box-shadow: 0 18px 50px rgba(0,0,0,.22);
}
.main-header::after {
    content: ""; position: absolute; width: 280px; height: 280px; right: -90px; top: -160px;
    background: radial-gradient(circle, rgba(79,156,255,.24), transparent 68%);
}
.main-header h1 { color: var(--text); margin: 0; font-size: 2rem; font-weight: 800; letter-spacing: -.5px; }
.main-header p { color: #aeb9cb; margin: 9px 0 0; font-size: .92rem; }
.version-badge { background: linear-gradient(135deg,var(--blue),var(--blue-2)); color: #fff; padding: 4px 10px; border-radius: 999px; font-size: .7rem; vertical-align: middle; margin-left: 8px; }

/* Section headings */
.section-title { font-size: 1.15rem; font-weight: 750; color: var(--text); margin: 8px 0 10px; }
.section-kicker { color: var(--blue); text-transform: uppercase; letter-spacing: 1.2px; font-size: .7rem; font-weight: 800; }

/* Feature cards */
.feature-card {
    height: 100%; min-height: 145px; padding: 18px;
    background: linear-gradient(145deg, #121a2a, #0d121d);
    border: 1px solid var(--border); border-radius: 16px;
    box-shadow: 0 12px 30px rgba(0,0,0,.12);
}
.feature-icon { font-size: 1.45rem; margin-bottom: 8px; }
.feature-card h4 { margin: 0 0 6px; color: var(--text); font-size: .98rem; }
.feature-card p { margin: 0; color: var(--muted); font-size: .8rem; line-height: 1.5; }

/* Upload zone */
.upload-card {
    background: linear-gradient(145deg, rgba(20,28,45,.96), rgba(12,17,28,.96));
    border: 1px solid #2b3a5a; border-radius: 18px; padding: 18px; margin: 12px 0 18px;
}

/* Metrics */
[data-testid="stMetric"] {
    background: linear-gradient(145deg, #121a2a, #0e131f);
    border: 1px solid var(--border); border-radius: 14px; padding: 14px 16px;
}
[data-testid="stMetricLabel"] { color: var(--muted) !important; }
[data-testid="stMetricValue"] { color: var(--text) !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 6px; background: transparent; }
.stTabs [data-baseweb="tab"] { border-radius: 10px; padding: 9px 14px; }
.stTabs [aria-selected="true"] { background: #18243a; }

/* Buttons */
.stButton > button, .stDownloadButton > button {
    border-radius: 10px; border: 1px solid #30405f; min-height: 42px; font-weight: 700;
    transition: transform .15s ease, box-shadow .15s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(0,0,0,.18); }

/* Risk badges */
.risk-badge { display:inline-flex; align-items:center; gap:6px; padding:6px 13px; border-radius:999px; font-weight:800; font-size:.78rem; letter-spacing:.2px; }
.risk-low { background:rgba(45,212,168,.12); color:#57e3c0; border:1px solid rgba(45,212,168,.35); }
.risk-medium { background:rgba(246,196,83,.12); color:#ffd66f; border:1px solid rgba(246,196,83,.35); }
.risk-high { background:rgba(255,93,115,.12); color:#ff8192; border:1px solid rgba(255,93,115,.35); }

/* Result / module cards */
.result-section, .intro-card, .module-status, .privacy-banner, .download-area {
    background: linear-gradient(145deg, #111827, #0d121c); border:1px solid var(--border); border-radius:14px;
}
.result-section { padding: 16px 18px; margin: 10px 0; }
.result-section h4 { color: #72b0ff; border-bottom:1px solid var(--border); padding-bottom:8px; }
.intro-card { padding: 20px; margin-bottom: 18px; }
.intro-card h4 { color:#72b0ff; margin-top:0; }
.module-status { padding: 11px 14px; margin: 6px 0; }
.module-status .status-dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:8px; box-shadow:0 0 10px currentColor; }
.status-active { background:var(--green); color:var(--green); }
.status-pending { background:var(--amber); color:var(--amber); }
.status-stub { background:#718096; color:#718096; }

/* Risk hero */
.risk-hero { text-align:center; padding:18px 10px; background:linear-gradient(145deg,#141c2d,#0d121d); border:1px solid var(--border); border-radius:16px; }
.risk-hero .score-value { font-size:3.1rem; font-weight:900; line-height:1; }
.risk-hero .score-label { font-size:.75rem; color:var(--muted); margin-top:6px; }
.score-low { color:#57e3c0; } .score-medium { color:#ffd66f; } .score-high { color:#ff8192; }

/* Indicators */
.indicator-suspicious, .indicator-normal { border-radius:10px; padding:10px 12px; margin:7px 0; font-size:.85rem; }
.indicator-suspicious { background:rgba(255,93,115,.08); border-left:3px solid var(--red); }
.indicator-normal { background:rgba(45,212,168,.07); border-left:3px solid var(--green); }

/* Tables / expanders */
[data-testid="stExpander"] { border:1px solid var(--border); border-radius:12px; background:#0d121d; }
[data-testid="stDataFrame"] { border-radius:12px; overflow:hidden; }

/* Privacy */
.privacy-banner { border-left:3px solid var(--blue); padding:12px 14px; color:var(--muted); font-size:.78rem; }

/* Footer */
.footer-text { color:#66748c; font-size:.72rem; text-align:center; padding-top:20px; border-top:1px solid var(--border); margin-top:28px; }

/* File uploader */
[data-testid="stFileUploader"] section { background:#0e1522; border:1px dashed #38527d; border-radius:14px; }

/* Alerts */
.stAlert { border-radius:12px; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Cached resources
# ---------------------------------------------------------------------------
@st.cache_resource
def get_database() -> ScreeningDatabase:
    """Singleton database connection."""
    return ScreeningDatabase(db_path=DB_PATH)


@st.cache_resource
def get_ocr_engine() -> OCREngine:
    """Singleton OCR engine (lazy‑initialised)."""
    return OCREngine(languages=OCR_LANGUAGES)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def file_hash(file_bytes: bytes) -> str:
    """SHA‑256 hex digest of file contents."""
    return hashlib.sha256(file_bytes).hexdigest()[:16]


def np_image_to_pil(image: np.ndarray) -> Image.Image:
    """Convert a numpy array (BGR or grayscale) to a PIL Image for display."""
    if image is None:
        return Image.new("RGB", (100, 100), (30, 30, 30))
    if len(image.shape) == 2:
        return Image.fromarray(image, mode="L")
    if image.shape[2] == 3:
        # OpenCV BGR → RGB
        return Image.fromarray(image[:, :, ::-1])
    return Image.fromarray(image)


def render_risk_badge(level: str) -> str:
    """Return HTML for a coloured risk badge."""
    css_class = f"risk-{level.lower()}" if level.upper() in RISK_LEVELS else "risk-medium"
    info = RISK_LEVELS.get(level.upper(), RISK_LEVELS["MEDIUM"])
    return f'<span class="risk-badge {css_class}">{info["icon"]} {info["label"]}</span>'


def render_module_status(name: str, status: str) -> str:
    """Return HTML for a module status indicator."""
    if status == "not_implemented":
        dot_class = "status-stub"
        label = "Pending"
    elif status == "success":
        dot_class = "status-active"
        label = "Active"
    else:
        dot_class = "status-pending"
        label = status.replace("_", " ").title()
    return (
        f'<div class="module-status">'
        f'<span class="status-dot {dot_class}"></span>'
        f'<strong>{name}</strong> — <em>{label}</em>'
        f'</div>'
    )


# ═══════════════════════════════════════════════════════════════════════════
# PAGES
# ═══════════════════════════════════════════════════════════════════════════

def page_screening() -> None:
    """Main document screening page."""
    # Premium hero header
    st.markdown(
        f'<div class="main-header">'
        f'<div class="section-kicker">SECURE DOCUMENT INTELLIGENCE</div>'
        f'<h1>🛡️ {APP_NAME} <span class="version-badge">v{APP_VERSION}</span></h1>'
        f"<p>{APP_DESCRIPTION}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Quick overview cards
    st.markdown('<div class="section-kicker">SCREENING WORKFLOW</div><div class="section-title">From document upload to explainable risk assessment</div>', unsafe_allow_html=True)
    feature_cols = st.columns(5)
    features = [
        ("📤", "Upload", "Add one or more document images."),
        ("🔎", "Detect", "Identify the document type automatically."),
        ("📝", "Extract", "Read and structure identity fields with OCR."),
        ("🔬", "Inspect", "Check image anomalies and consistency."),
        ("⚖️", "Score", "Combine checks into an explainable risk score."),
    ]
    for col, (icon, title, desc) in zip(feature_cols, features):
        with col:
            st.markdown(f'<div class="feature-card"><div class="feature-icon">{icon}</div><h4>{title}</h4><p>{desc}</p></div>', unsafe_allow_html=True)

    with st.expander("🔒 Privacy & responsible-use notice", expanded=False):
        st.markdown(PRIVACY_NOTICE)

    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-kicker">START A NEW SCREENING</div><div class="section-title">Upload identity document images</div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Select identity document image(s)",
        type=["jpg", "jpeg", "png", "bmp", "tiff"],
        accept_multiple_files=True,
        help="Supported formats: JPG, PNG, BMP, TIFF. Max 10 MB per file.",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    if not uploaded_files:
        st.info("👆 Upload one or more identity document images to begin screening.")
        _render_supported_docs_summary()
        return

    # Show thumbnails
    thumb_cols = st.columns(min(len(uploaded_files), 4))
    for idx, uf in enumerate(uploaded_files):
        with thumb_cols[idx % len(thumb_cols)]:
            img = Image.open(uf)
            st.image(img, caption=uf.name, use_container_width=True)
            uf.seek(0)  # reset after read

    st.divider()

    # ── Analyze button ─────────────────────────────────────────────────────
    if st.button("🔍 Analyze Document(s)", type="primary", use_container_width=True):
        db = get_database()
        ocr_engine = get_ocr_engine()

        all_doc_results: list[dict[str, Any]] = []

        for uf in uploaded_files:
            st.markdown(f"---\n### 📄 Analysis: `{uf.name}`")

            try:
                raw_bytes = uf.read()
                uf.seek(0)
                fhash = file_hash(raw_bytes)

                pil_img = Image.open(io.BytesIO(raw_bytes))
                if pil_img.mode == "RGBA":
                    pil_img = pil_img.convert("RGB")
                img_array = np.array(pil_img)

                # ── Pipeline ───────────────────────────────────────────────
                with st.status("Running analysis pipeline…", expanded=True) as status_bar:
                    # 1. Preprocessing
                    st.write("🖼️ Preprocessing image…")
                    preprocessor = ImagePreprocessor()
                    prep = preprocessor.preprocess(img_array)

                    # 2. OCR
                    # Use grayscale (not threshold) image — EasyOCR works
                    # poorly on hard-binarised images because thresholding
                    # destroys the gradient information its models need.
                    st.write("📝 Extracting text (OCR)…")
                    ocr_image = (
                        prep.get("grayscale")       # best: denoised grayscale
                        if prep.get("grayscale") is not None
                        else prep.get("processed", img_array)
                    )
                    ocr_result = ocr_engine.extract_text(ocr_image)

                    # 3. Document detection
                    st.write("🔍 Detecting document type…")
                    detector = DocumentDetector()
                    detect_result = detector.detect(ocr_result.get("text", ""))
                    doc_type = detect_result.get("document_type")

                    # 4. Field extraction
                    st.write("📋 Extracting identity fields…")
                    extractor = FieldExtractor()
                    
                    extract_result = extractor.extract(ocr_result.get("text", ""), doc_type or "")

                    # 5. Validation
                    st.write("✅ Validating fields…")
                    validator = DocumentValidator()
                    valid_result = validator.validate(extract_result.get("fields", {}), doc_type or "")

                    # 6. Tampering analysis
                    st.write("🔬 Analyzing for tampering indicators…")
                    tampering = TamperingAnalyzer()
                    tamp_result = tampering.analyze(img_array)

                    # Risk scoring deferred until after consistency check
                    risk_result = None

                    status_bar.update(label="✅ Analysis complete", state="complete")

                # Collect per-document results for consistency
                all_doc_results.append({
                    "document_type": doc_type,
                    "fields": extract_result.get("fields", {}),
                    "validation": valid_result,
                    "tampering": tamp_result,
                    # These are needed for rendering and DB save
                    "_prep": prep,
                    "_ocr": ocr_result,
                    "_detect": detect_result,
                    "_extract": extract_result,
                    "_valid": valid_result,
                    "_tamp": tamp_result,
                    "_doc_type": doc_type,
                    "_fhash": fhash,
                })

            except (OSError, IOError) as exc:
                logger.exception("Image read error for %s", uf.name)
                st.error(
                    f"❌ Could not read **{uf.name}**. The file may be corrupted "
                    f"or in an unsupported format. Please try a different image."
                )
            except MemoryError:
                logger.exception("Memory error processing %s", uf.name)
                st.error(
                    f"❌ **{uf.name}** is too large to process. "
                    f"Please use a smaller image (recommended: under 5 MB)."
                )
            except Exception as exc:
                logger.exception("Error processing %s", uf.name)
                st.error(
                    f"❌ An unexpected error occurred while processing **{uf.name}**. "
                    f"Please try a different image or check the file format."
                )
                with st.expander("Technical details", expanded=False):
                    st.code(str(exc))

        # ── Cross-document consistency ──────────────────────────────────
        checker = ConsistencyChecker()
        consistency_result = checker.check(all_doc_results)

        # ── Risk scoring + display per document ─────────────────────────
        scorer = RiskScorer()

        for doc_data in all_doc_results:
            valid_result = doc_data["_valid"]
            tamp_result = doc_data["_tamp"]
            risk_result = scorer.calculate(
                valid_result, tamp_result, consistency_result,
            )

            module_statuses = {
                "OCR Engine": doc_data["_ocr"].get("status", "unknown"),
                "Document Detector": doc_data["_detect"].get("status", "unknown"),
                "Field Extractor": doc_data["_extract"].get("status", "unknown"),
                "Field Validator": valid_result.get("status", "unknown"),
                "Tampering Analyzer": tamp_result.get("status", "unknown"),
                "Risk Scorer": risk_result.get("status", "unknown"),
            }

            # Display results for this document
            try:
                _render_results(
                    prep=doc_data["_prep"],
                    ocr_result=doc_data["_ocr"],
                    detect_result=doc_data["_detect"],
                    extract_result=doc_data["_extract"],
                    valid_result=valid_result,
                    tamp_result=tamp_result,
                    risk_result=risk_result,
                    module_statuses=module_statuses,
                    doc_type=doc_data["_doc_type"],
                )
            except Exception as render_exc:
                logger.exception("Error in _render_results")
                st.error(f"❌ Error rendering results: {render_exc}")

            # Save to DB
            level = risk_result.get("level", "LOW")
            screening_record = {
                "timestamp": format_timestamp(),
                "document_type": doc_data["_doc_type"],
                "document_name": doc_data["_detect"].get("document_name", "Unknown"),
                "risk_score": risk_result.get("score", 0.0),
                "risk_level": level,
                "recommendation": risk_result.get("recommendation", ""),
                "findings": {
                    "ocr": {"status": doc_data["_ocr"].get("status"), "confidence": doc_data["_ocr"].get("confidence")},
                    "detection": {"type": doc_data["_doc_type"], "confidence": doc_data["_detect"].get("confidence")},
                    "extraction": {"count": doc_data["_extract"].get("extraction_count"), "total": doc_data["_extract"].get("total_fields")},
                    "validation": {"valid": valid_result.get("valid_count"), "total": valid_result.get("total_count"), "checks": valid_result.get("checks", [])},
                    "tampering": {"suspicious": tamp_result.get("overall_suspicious"), "score": tamp_result.get("suspicion_score"), "checks": tamp_result.get("checks", [])},
                    "risk": {"score": risk_result.get("score"), "level": level, "factors": risk_result.get("factors", [])},
                    "consistency": {"status": consistency_result.get("status"), "consistent": consistency_result.get("consistent")},
                },
                "file_hash": doc_data["_fhash"],
            }
            sid = db.save_screening(screening_record)
            if sid and sid > 0:
                st.caption(f"💾 Screening saved (ID: {sid})")

            # ── Report download ──────────────────────────────────────────
            report = {
                "report_type": "SIH26188 Document Screening Report",
                "generated_at": format_timestamp(),
                "document_type": doc_data["_doc_type"],
                "document_name": doc_data["_detect"].get("document_name", "Unknown"),
                "screening": {
                    "heuristic_score": risk_result.get("score_pct", 0),
                    "heuristic_score_raw": risk_result.get("score", 0.0),
                    "risk_level": level,
                    "recommendation": risk_result.get("recommendation", ""),
                    "indicators": risk_result.get("indicators", []),
                    "factors": risk_result.get("factors", []),
                    "summary": risk_result.get("summary", ""),
                },
                "extracted_fields": {
                    fname: (fval.get("value", str(fval)) if isinstance(fval, dict) else str(fval))
                    for fname, fval in doc_data["_extract"].get("fields", {}).items()
                },
                "validation": {
                    "status": valid_result.get("status"),
                    "passed": valid_result.get("valid_count", 0),
                    "total": valid_result.get("total_count", 0),
                    "checks": valid_result.get("checks", []),
                },
                "tampering_analysis": {
                    "status": tamp_result.get("status"),
                    "overall_suspicious": tamp_result.get("overall_suspicious"),
                    "suspicion_score": tamp_result.get("suspicion_score"),
                    "checks": [
                        {k: v for k, v in tc.items() if k != "image"}
                        for tc in tamp_result.get("checks", [])
                    ],
                    "message": tamp_result.get("message", ""),
                },
                "consistency": {
                    "status": consistency_result.get("status"),
                    "consistent": consistency_result.get("consistent"),
                    "score": consistency_result.get("consistency_score"),
                    "checks": consistency_result.get("checks", []),
                },
                "ocr": {
                    "status": doc_data["_ocr"].get("status"),
                    "confidence": doc_data["_ocr"].get("confidence"),
                    "engine": doc_data["_ocr"].get("engine", "EasyOCR"),
                },
                "disclaimer": (
                    "This is a heuristic screening report generated by the "
                    "SIH26188 AI Document Screening System. Scores are "
                    "deterministic heuristics, not probabilities of fraud. "
                    "All findings require human review and verification "
                    "through authorized channels."
                ),
            }
            report_json = json.dumps(report, indent=2, default=str)
            doc_slug = (doc_data["_doc_type"] or "document").replace(" ", "_")
            st.download_button(
                label="📥 Download Screening Report (JSON)",
                data=report_json,
                file_name=f"screening_report_{doc_slug}_{doc_data['_fhash'][:8]}.json",
                mime="application/json",
                key=f"dl_{doc_data['_fhash']}",
            )

        # ── Cross-document consistency display ──────────────────────────
        if consistency_result.get("status") == "success":
            st.markdown("---")
            st.markdown("### 🔗 Cross-Document Consistency")
            checks = consistency_result.get("checks", [])
            if checks:
                check_data = []
                for c in checks:
                    icon = "✅" if c.get("consistent") else "⚠️"
                    check_data.append({
                        "Field": c.get("field_label", c.get("field", "")),
                        "Status": f"{icon} {'Consistent' if c.get('consistent') else 'Mismatch'}",
                        "Details": c.get("message", ""),
                    })
                st.table(check_data)
            else:
                st.info("No comparable fields found across documents.")
            st.caption(
                f"Consistency score: {consistency_result.get('consistency_score', 0):.2f} · "
                f"{consistency_result.get('message', '')}"
            )


def _render_supported_docs_summary() -> None:
    """Show a compact card of supported document types."""
    doc_icons = {"aadhaar": "🪪", "pan": "💳", "voter_id": "🗳️"}
    cols = st.columns(len(DOCUMENT_TYPES))
    for col, (key, doc) in zip(cols, DOCUMENT_TYPES.items()):
        with col:
            icon = doc_icons.get(key, "📄")
            n_fields = len(doc["fields"])
            checksum = f"✅ {doc['checksum_algorithm'].title()} checksum" if doc.get("checksum_algorithm") else ""
            st.markdown(
                f"**{icon} {doc['name']}**\n\n"
                f"_{doc['description']}_\n\n"
                f"**{n_fields}** extractable fields"
                + (f"  \n{checksum}" if checksum else "")
            )


def _render_results(
    *,
    prep: dict,
    ocr_result: dict,
    detect_result: dict,
    extract_result: dict,
    valid_result: dict,
    tamp_result: dict,
    risk_result: dict,
    module_statuses: dict,
    doc_type: str | None,
) -> None:
    """Render the full analysis results panel with tabbed layout."""

    st.divider()
    doc_label = doc_type.upper() if doc_type else "UNKNOWN"
    st.markdown(f"## 📊 Screening Report — {doc_label}")

    # ── Headline: Risk score hero + Document info (always visible) ─────────
    score = risk_result.get("score", 0.0)
    score_pct = risk_result.get("score_pct", round(score * 100))
    level = risk_result.get("level", "LOW")
    score_css = f"score-{level.lower()}"

    col_score, col_badge, col_doc = st.columns([1, 1, 2])

    with col_score:
        st.markdown(
            f'<div class="risk-hero">'
            f'<div class="score-value {score_css}">{score_pct}</div>'
            f'<div class="score-label">Heuristic Score / 100</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_badge:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(render_risk_badge(level), unsafe_allow_html=True)
        st.caption("Heuristic screening score — not a probability of fraud")

    with col_doc:
        doc_name = detect_result.get("document_name", "Unknown")
        doc_conf = detect_result.get("confidence", 0.0)
        c1, c2 = st.columns(2)
        c1.metric("Document Type", doc_name)
        c2.metric("Detection Confidence", f"{doc_conf:.0%}")
        if detect_result.get("matched_keywords"):
            st.caption(f"Matched keywords: {', '.join(detect_result['matched_keywords'])}")

    # ── Tabs ───────────────────────────────────────────────────────────────
    tab_assessment, tab_fields, tab_image, tab_details = st.tabs([
        "⚖️ Screening Assessment",
        "📋 Fields & Validation",
        "🔬 Image Analysis",
        "📝 Details",
    ])

    # ── Tab 1: Screening Assessment ────────────────────────────────────────
    with tab_assessment:
        col_ind, col_rec = st.columns([3, 2])

        with col_ind:
            st.markdown("#### Risk Indicators")
            indicators = risk_result.get("indicators", [])
            if indicators:
                for ind in indicators:
                    st.markdown(
                        f'<div class="indicator-suspicious">🚨 {ind}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    '<div class="indicator-normal">✅ No suspicious indicators identified.</div>',
                    unsafe_allow_html=True,
                )

            # Show contributing factors
            factors = risk_result.get("factors", [])
            if factors:
                st.markdown("##### Contributing Factors")
                factor_data = []
                for f in factors:
                    factor_data.append({
                        "Category": f.get("category", "").title(),
                        "Factor": f.get("name", ""),
                        "Weight": f"{f.get('contribution', 0)}%",
                        "Description": f.get("description", ""),
                    })
                st.table(factor_data)

        with col_rec:
            st.markdown("#### Recommendation")
            recommendation = risk_result.get("recommendation", "N/A")
            st.info(f"📋 {recommendation}")

            st.markdown("#### Score Breakdown")
            st.markdown(f"**Heuristic Score:** {score_pct} / 100")
            st.markdown(f"**Risk Level:** {render_risk_badge(level)}", unsafe_allow_html=True)
            st.markdown(f"**Summary:** {risk_result.get('summary', 'N/A')}")

    # ── Tab 2: Fields & Validation ─────────────────────────────────────────
    with tab_fields:
        # Extracted fields
        st.markdown("#### 📋 Extracted Fields")
        fields = extract_result.get("fields", {})
        if fields:
            field_data = []
            for fname, fval in fields.items():
                display_val = fval
                if isinstance(fval, dict):
                    display_val = fval.get("value", str(fval))
                masked = mask_sensitive_field(str(display_val), fname, doc_type or "")
                label = fname
                if doc_type and doc_type in DOCUMENT_TYPES:
                    fconf = DOCUMENT_TYPES[doc_type]["fields"].get(fname, {})
                    label = fconf.get("label", fname)
                field_data.append({"Field": label, "Value": masked})
            st.table(field_data)
        else:
            st.info(
                "No identity fields were extracted. "
                "The document may be unrecognised or OCR text was insufficient."
            )
        st.caption(
            f"Extracted **{extract_result.get('extraction_count', 0)}** / "
            f"**{extract_result.get('total_fields', 0)}** defined fields."
        )

        st.divider()

        # Validation checks
        st.markdown("#### ✅ Validation Checks")
        valid_status = valid_result.get("status", "")
        checks = valid_result.get("checks", [])

        if valid_status == "error" and not checks:
            findings = valid_result.get("findings", [])
            if findings:
                for f in findings:
                    st.warning(f)
            else:
                st.info("No validation checks could be performed for this document type.")
        elif checks:
            check_data = []
            for chk in checks:
                passed = chk.get("passed")
                icon = "✅" if passed else "❌"
                check_data.append({
                    "Check": chk.get("check_name", chk.get("field", "")),
                    "Result": f"{icon} {'Passed' if passed else 'Failed'}",
                    "Details": chk.get("message", ""),
                })
            st.table(check_data)

            findings = valid_result.get("findings", [])
            if findings:
                st.markdown("**Validation Findings:**")
                for f in findings:
                    st.markdown(f"- {f}")
        else:
            st.info("No validation checks were performed.")

        vc = valid_result.get("valid_count", 0)
        tc = valid_result.get("total_count", 0)
        st.caption(f"Passed: {vc}/{tc}")

    # ── Tab 3: Image Analysis ──────────────────────────────────────────────
    with tab_image:
        st.markdown("#### 🔬 Image Anomaly Analysis")
        tamp_status = tamp_result.get("status", "")
        tamp_checks = tamp_result.get("checks", [])

        if tamp_status == "error" and not tamp_checks:
            st.warning(f"⚠️ {tamp_result.get('message', 'Analysis could not be performed.')}")
        elif tamp_checks:
            check_data = []
            for tc_item in tamp_checks:
                suspicious = tc_item.get("suspicious")
                icon = "🚨" if suspicious else "✅"
                check_data.append({
                    "Indicator": tc_item.get("name", ""),
                    "Status": f"{icon} {'Suspicious' if suspicious else 'Normal'}",
                    "Details": tc_item.get("result", tc_item.get("description", "")),
                })
            st.table(check_data)

            if tamp_result.get("ela_image") is not None:
                st.image(
                    np_image_to_pil(tamp_result["ela_image"]),
                    caption="Error Level Analysis (ELA) — brighter regions indicate higher compression difference",
                    use_container_width=True,
                )

            if tamp_result.get("overall_suspicious"):
                st.warning(f"⚠️ {tamp_result.get('message', '')}")
            else:
                st.success(f"✅ {tamp_result.get('message', '')}")
        else:
            st.info("No image anomaly checks were performed.")

        t_score = tamp_result.get("suspicion_score", 0.0)
        method = tamp_result.get("method", "N/A")
        st.caption(
            f"Heuristic anomaly score: {t_score:.2f} · "
            f"Method: {method} · "
            f"Overall suspicious: {'Yes' if tamp_result.get('overall_suspicious') else 'No'}"
        )

    # ── Tab 4: Details ─────────────────────────────────────────────────────
    with tab_details:
        # OCR results
        st.markdown("#### 📝 OCR Results")
        ocr_status = ocr_result.get("status", "unknown")
        ocr_text = ocr_result.get("text", "")

        if ocr_status == "success" and ocr_text:
            st.text_area("Extracted Text", ocr_text, height=150, disabled=True)
            ocr_conf = ocr_result.get("confidence", 0.0)
            n_regions = len(ocr_result.get("details", []))
            st.caption(
                f"Confidence: {ocr_conf:.0%} · "
                f"Regions: {n_regions} · "
                f"Engine: {ocr_result.get('engine', 'N/A')}"
            )
        elif ocr_status == "no_text":
            msg = ocr_result.get("message", "No readable text was detected in this image.")
            st.warning(f"📭 {msg}")
        elif ocr_status == "error":
            msg = ocr_result.get("message", "An error occurred during text extraction.")
            st.error(f"❌ OCR Error: {msg}")
        else:
            st.info(f"OCR returned status: {ocr_status}.")

        st.divider()

        # Preprocessing steps
        st.markdown("#### 🖼️ Preprocessing Steps")
        steps = prep.get("steps", [])
        if steps:
            step_cols = st.columns(min(len(steps), 4))
            for idx, step in enumerate(steps):
                with step_cols[idx % len(step_cols)]:
                    st.caption(f"**{step['name'].title()}**")
                    st.image(
                        np_image_to_pil(step.get("image")),
                        caption=step["description"],
                        use_container_width=True,
                    )
        else:
            st.info("No preprocessing steps recorded.")

        st.divider()

        # Module status
        st.markdown("#### 🔧 Module Status")
        status_html = "".join(render_module_status(k, v) for k, v in module_statuses.items())
        st.markdown(status_html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
def page_history() -> None:
    """Screening history page."""
    st.markdown(
        f'<div class="main-header">'
        f"<h1>📊 Screening History</h1>"
        f"<p>Review past document screenings and their results.</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    db = get_database()
    screenings = db.get_all_screenings()
    count = len(screenings)

    # Count by risk level
    levels = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for s in screenings:
        lv = (s.get("risk_level") or "LOW").upper()
        levels[lv] = levels.get(lv, 0) + 1

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Screenings", count)
    col2.metric("🟢 Low Risk", levels["LOW"])
    col3.metric("🟡 Medium Risk", levels["MEDIUM"])
    col4.metric("🔴 High Risk", levels["HIGH"])

    st.divider()

    if not screenings:
        st.info("No screenings recorded yet. Go to **Document Screening** to analyze documents.")
        return

    # Clear all button
    col_spacer, col_clear = st.columns([4, 1])
    with col_clear:
        if st.button("🗑️ Clear All", type="secondary"):
            st.session_state["confirm_clear_all"] = True
    if st.session_state.get("confirm_clear_all"):
        st.warning("⚠️ This will delete **all** screening records. This cannot be undone.")
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if st.button("✅ Confirm Delete All", type="primary"):
                for s in screenings:
                    db.delete_screening(s.get("id"))
                st.session_state["confirm_clear_all"] = False
                st.success("All screening records deleted.")
                st.rerun()
        with c2:
            if st.button("Cancel"):
                st.session_state["confirm_clear_all"] = False
                st.rerun()

    # Screening records
    for s in screenings:
        sid = s.get("id", "?")
        ts = s.get("timestamp", s.get("created_at", ""))
        doc_name = s.get("document_name", "Unknown")
        risk_lvl = (s.get("risk_level") or "LOW").upper()
        risk_score = s.get("risk_score", 0.0)
        risk_pct = round(risk_score * 100)

        badge = render_risk_badge(risk_lvl)
        header = f"**#{sid}** · {doc_name} · Score: {risk_pct}/100 · {ts}"

        with st.expander(header, expanded=False):
            # Summary row
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Risk Level:** {badge}", unsafe_allow_html=True)
            c2.metric("Heuristic Score", f"{risk_pct} / 100")
            c3.markdown(f"**Recommendation:** {s.get('recommendation', 'N/A')}")

            # Structured findings
            findings = s.get("findings")
            if findings and isinstance(findings, dict):
                with st.expander("📋 Detailed Findings", expanded=False):
                    # Validation
                    val = findings.get("validation", {})
                    if val:
                        st.markdown(f"**Validation:** {val.get('valid', 0)}/{val.get('total', 0)} checks passed")
                    # Tampering
                    tamp = findings.get("tampering", {})
                    if tamp:
                        susp = "⚠️ Yes" if tamp.get("suspicious") else "✅ No"
                        st.markdown(f"**Tampering suspicious:** {susp} (score: {tamp.get('score', 0):.2f})")
                    # Consistency
                    cons = findings.get("consistency", {})
                    if cons:
                        st.markdown(f"**Consistency:** {cons.get('status', 'N/A')}")
                    # Risk factors
                    risk = findings.get("risk", {})
                    if risk and risk.get("factors"):
                        st.markdown("**Risk Factors:**")
                        for f in risk["factors"]:
                            st.markdown(f"- [{f.get('category', '')}] {f.get('name', '')}: {f.get('description', '')}")

                    # Raw JSON fallback
                    with st.expander("🔍 Raw JSON", expanded=False):
                        st.json(findings)

            if st.button(f"🗑️ Delete #{sid}", key=f"del_{sid}"):
                db.delete_screening(sid)
                st.success(f"Screening #{sid} deleted.")
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
def page_about() -> None:
    """About / information page."""
    st.markdown(
        f'<div class="main-header">'
        f"<h1>ℹ️ About</h1>"
        f"<p>System information, supported documents, and privacy details.</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown(f"### {APP_NAME}")
    st.markdown(f"**Version:** {APP_VERSION}")
    st.markdown(APP_DESCRIPTION)

    st.divider()

    # Supported document types
    st.markdown("### 📄 Supported Document Types")
    for key, doc in DOCUMENT_TYPES.items():
        with st.expander(f"{doc['name']} — {doc['description']}", expanded=False):
            st.markdown("**Extractable fields:**")
            for fname, fconf in doc["fields"].items():
                req = "Required" if fconf.get("required") else "Optional"
                sens = " · 🔒 Sensitive" if fconf.get("sensitive") else ""
                st.markdown(f"- **{fconf['label']}** ({fconf.get('format_description', 'N/A')}) — _{req}{sens}_")
            if doc.get("checksum_algorithm"):
                st.caption(f"Checksum: {doc['checksum_algorithm']} on {doc['checksum_field']}")

    st.divider()

    # Technology stack
    st.markdown("### 🛠️ Technology Stack")
    tech_data = [
        {"Component": "UI Framework", "Technology": "Streamlit"},
        {"Component": "Image Processing", "Technology": "OpenCV"},
        {"Component": "OCR Engine", "Technology": "EasyOCR"},
        {"Component": "Database", "Technology": "SQLite"},
        {"Component": "ML/Validation", "Technology": "scikit‑learn, regex, Verhoeff checksum"},
        {"Component": "Language", "Technology": "Python 3.11+"},
    ]
    st.table(tech_data)

    st.divider()

    # Privacy
    st.markdown("### 🔒 Privacy")
    st.markdown(PRIVACY_NOTICE)

    st.divider()

    # Disclaimer
    st.markdown("### ⚠️ Disclaimer")
    st.warning(
        "This is a **screening tool** that identifies potential indicators of concern. "
        "It does **not** make legal determinations about whether a document is authentic "
        "or whether a person's identity is genuine. All findings require human review "
        "and verification through authorized channels. Suspicion scores are heuristic "
        "indicators, not statistically calibrated probabilities."
    )


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main() -> None:
    """Application entry point with sidebar navigation."""

    # Sidebar
    with st.sidebar:
        st.markdown(
            f'<div class="brand-card"><span class="brand-icon">🛡️</span>'
            f'<span class="brand-title">{APP_NAME}</span>'
            f'<div class="brand-sub">v{APP_VERSION} · Local-first screening</div></div>',
            unsafe_allow_html=True,
        )

        st.caption("WORKSPACE")
        page = st.radio(
            "Navigation",
            ["📋 Document Screening", "📊 Screening History", "ℹ️ About"],
            label_visibility="collapsed",
        )

        st.divider()

        db = get_database()
        screenings = db.get_all_screenings()
        total = len(screenings)
        st.markdown("**📈 Screening Overview**")
        st.metric("Total screenings", total)

        if total > 0:
            levels = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
            for s in screenings:
                lv = (s.get("risk_level") or "LOW").upper()
                levels[lv] = levels.get(lv, 0) + 1
            st.caption(f"🟢 {levels['LOW']}  ·  🟡 {levels['MEDIUM']}  ·  🔴 {levels['HIGH']}")

        st.divider()
        st.markdown("**⚙️ Analysis Pipeline**")
        pipeline = [
            "📝 OCR extraction", "🔍 Document detection", "📋 Field validation",
            "🔬 Anomaly analysis", "🔗 Consistency check", "⚖️ Risk scoring",
        ]
        for idx, item in enumerate(pipeline, 1):
            st.caption(f"{idx:02d}  {item}")

        st.divider()
        st.markdown(
            '<div class="privacy-banner">🔒 <strong>Local processing</strong><br>'
            'Documents stay on this machine during screening.</div>',
            unsafe_allow_html=True,
        )

    # Route
    if page == "📋 Document Screening":
        page_screening()
    elif page == "📊 Screening History":
        page_history()
    elif page == "ℹ️ About":
        page_about()


if __name__ == "__main__":
    main()
