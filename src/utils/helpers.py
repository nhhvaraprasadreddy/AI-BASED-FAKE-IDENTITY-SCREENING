from __future__ import annotations

import logging
from datetime import datetime
from src.config import DOCUMENT_TYPES, RISK_THRESHOLDS, RISK_LEVELS

def setup_logging(name: str = "sih26188") -> logging.Logger:
    """Configures and returns a logger with StreamHandler."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

logger = setup_logging(__name__)

def mask_aadhaar(number: str) -> str:
    """Takes a 12-digit Aadhaar number and returns masked format."""
    try:
        clean = ''.join(c for c in str(number) if c.isdigit())
        if len(clean) == 12:
            return f"XXXX XXXX {clean[-4:]}"
        return str(number)
    except Exception as e:
        logger.error(f"Error masking aadhaar: {e}")
        return str(number)

def mask_pan(number: str) -> str:
    """Takes a 10-char PAN and returns masked format."""
    try:
        clean = str(number).replace(" ", "")
        if len(clean) == 10:
            return f"{'X'*8}{clean[-2:]}"
        return str(number)
    except Exception as e:
        logger.error(f"Error masking PAN: {e}")
        return str(number)

def mask_sensitive_field(value: str, field_name: str, document_type: str) -> str:
    """Masks a field if it is marked as sensitive in DOCUMENT_TYPES."""
    try:
        doc_info = DOCUMENT_TYPES.get(document_type)
        if not doc_info:
            return value
        field_info = doc_info.get("fields", {}).get(field_name)
        if not field_info or not field_info.get("sensitive"):
            return value
        
        if document_type == "aadhaar" and field_name == "aadhaar_number":
            return mask_aadhaar(value)
        elif document_type == "pan" and field_name == "pan_number":
            return mask_pan(value)
        return "****"
    except Exception as e:
        logger.error(f"Error masking sensitive field: {e}")
        return value

def format_risk_level(score: float) -> str:
    """Formats risk score to risk level string."""
    try:
        if score <= RISK_THRESHOLDS["low_max"]:
            return "LOW"
        elif score <= RISK_THRESHOLDS["medium_max"]:
            return "MEDIUM"
        else:
            return "HIGH"
    except Exception as e:
        logger.error(f"Error formatting risk level: {e}")
        return "MEDIUM"

def get_risk_color(level: str) -> str:
    """Returns the hex color for a risk level."""
    try:
        return RISK_LEVELS.get(level.upper(), {}).get("color", "#000000")
    except Exception as e:
        logger.error(f"Error getting risk color: {e}")
        return "#000000"

def format_timestamp(dt: datetime = None) -> str:
    """Returns ISO-format timestamp string."""
    try:
        if dt is None:
            dt = datetime.now()
        return dt.isoformat()
    except Exception as e:
        logger.error(f"Error formatting timestamp: {e}")
        return datetime.now().isoformat()
