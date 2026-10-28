import re
import json
import logging
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.models import Document, ExtractedField
from app.services.normalize import normalize_id

logger = logging.getLogger(__name__)


def parse_qr_payload(qr_text: Optional[str]) -> Optional[Dict[str, str]]:
    """Parse QR code payload string into a structured dictionary.
    
    Supported formats:
    - Pipe-delimited key:value pairs (e.g. CERT:FS-2024-A01-901|AUTH:...|EXP:...)
    - JSON payloads (e.g. {"certificate_number": "..."})
    - Key-value pairs separated by semicolon or newline
    """
    if not qr_text or not qr_text.strip():
        return None

    raw = qr_text.strip()

    # Try JSON first
    if raw.startswith("{") and raw.endswith("}"):
        try:
            data = json.loads(raw)
            return {str(k).upper(): str(v) for k, v in data.items()}
        except Exception:
            pass

    # Pipe or semicolon delimited
    parts = re.split(r"[|\n;]", raw)
    parsed: Dict[str, str] = {}
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            k, v = part.split(":", 1)
            parsed[k.strip().upper()] = v.strip()
        elif "=" in part:
            k, v = part.split("=", 1)
            parsed[k.strip().upper()] = v.strip()

    return parsed if parsed else None


def extract_id_from_qr_payload(payload: Dict[str, str]) -> Optional[str]:
    """Extract standard document identifier from parsed QR dictionary."""
    for key in ("CERT", "CERTIFICATE_NUMBER", "CERT_NO", "LAND_REG", "TRUST_REG", "REGISTRATION_NUMBER", "REG_NO", "ID"):
        if key in payload and payload[key]:
            return payload[key]
    return None


def verify_qr_code(
    db: Session,
    document: Document,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Verify stored QR text on document against extracted document fields.
    
    Outcomes:
    - 'match': QR payload ID matches extracted normalized ID
    - 'mismatch': QR says one number, extracted document text says another
    - 'absent': No QR on document (reported as 'unavailable', not failure)
    - 'unreadable': QR detected/present but cannot be parsed
    """
    qr_text = document.qr_text

    # 1. QR Absent check
    if not qr_text or not qr_text.strip():
        return {
            "result": "absent",
            "probability": None,
            "signals": [],
            "evidence": {
                "status": "unavailable",
                "outcome": "absent",
                "details": "Document does not have an embedded QR code.",
                "qr_payload_raw": None,
            },
        }

    # 2. Parse payload
    payload = parse_qr_payload(qr_text)
    if not payload:
        return {
            "result": "unreadable",
            "probability": None,
            "signals": ["unreadable_qr"],
            "evidence": {
                "status": "unreadable",
                "outcome": "unreadable",
                "details": "QR code is present but could not be parsed into a structured payload.",
                "qr_payload_raw": qr_text,
            },
        }

    qr_id_raw = extract_id_from_qr_payload(payload)
    if not qr_id_raw:
        return {
            "result": "unreadable",
            "probability": None,
            "signals": ["unreadable_qr"],
            "evidence": {
                "status": "unreadable",
                "outcome": "unreadable",
                "details": "QR payload does not contain an identifiable document number or ID.",
                "parsed_payload": payload,
                "qr_payload_raw": qr_text,
            },
        }

    # 3. Find extracted identifier on document
    extracted_id: Optional[str] = None
    target_field_name: Optional[str] = None

    for ef in document.extracted_fields:
        if ef.name in ("certificate_number", "registration_number") and ef.value_normalized:
            extracted_id = ef.value_normalized
            target_field_name = ef.name
            break

    if not extracted_id:
        return {
            "result": "unavailable",
            "probability": None,
            "signals": [],
            "evidence": {
                "status": "unavailable",
                "details": "Document does not have an extracted certificate or registration number to compare.",
                "qr_id_raw": qr_id_raw,
                "parsed_payload": payload,
            },
        }

    norm_qr_id = normalize_id(qr_id_raw)
    norm_doc_id = normalize_id(extracted_id)

    # 4. Compare
    if norm_qr_id == norm_doc_id:
        return {
            "result": "match",
            "probability": None,
            "signals": [],
            "evidence": {
                "status": "match",
                "outcome": "match",
                "compared_field": target_field_name,
                "qr_id_normalized": norm_qr_id,
                "document_id_normalized": norm_doc_id,
                "parsed_payload": payload,
                "qr_payload_raw": qr_text,
            },
        }
    else:
        return {
            "result": "mismatch",
            "probability": None,
            "signals": ["qr_id_mismatch"],
            "evidence": {
                "status": "mismatch",
                "outcome": "mismatch",
                "compared_field": target_field_name,
                "qr_id_normalized": norm_qr_id,
                "document_id_normalized": norm_doc_id,
                "details": f"QR payload ({norm_qr_id}) does not match extracted document text ({norm_doc_id}).",
                "parsed_payload": payload,
                "qr_payload_raw": qr_text,
            },
        }
