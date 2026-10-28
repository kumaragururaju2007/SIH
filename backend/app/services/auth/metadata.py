import re
import logging
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ExifTags
from sqlalchemy.orm import Session

from app.models import Document, Application, ExtractedField
from app.services.pipeline import resolve_file_path

logger = logging.getLogger(__name__)


def parse_pdf_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse PDF date format (e.g. D:20240416100000Z or 20240416) into UTC datetime."""
    if not date_str:
        return None
    s = str(date_str).strip()
    if s.startswith("D:"):
        s = s[2:]
    s = s.replace("'", "")

    # Clean regex extraction
    m = re.match(r"^(\d{4})(\d{2})(\d{2})(?:(\d{2})(\d{2})(\d{2}))?", s)
    if m:
        year, month, day, hour, minute, second = m.groups()
        try:
            return datetime(
                int(year),
                int(month),
                int(day),
                int(hour or 0),
                int(minute or 0),
                int(second or 0),
                tzinfo=timezone.utc,
            )
        except Exception:
            pass

    # Try ISO formats
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue

    return None


def extract_raw_metadata(resolved_path: Path) -> Dict[str, Any]:
    """Extract metadata from PDF via PyMuPDF (or pikepdf) or image EXIF via Pillow."""
    raw_meta: Dict[str, Any] = {}

    # Check for corresponding PDF file if current file is PNG
    pdf_path: Optional[Path] = None
    if resolved_path.suffix.lower() == ".pdf" and resolved_path.exists():
        pdf_path = resolved_path
    else:
        candidate_pdf = resolved_path.with_suffix(".pdf")
        if candidate_pdf.exists():
            pdf_path = candidate_pdf

    # 1. Try PyMuPDF on PDF file
    if pdf_path and pdf_path.exists():
        try:
            import fitz
            doc = fitz.open(pdf_path)
            meta = doc.metadata or {}
            doc.close()
            if meta:
                raw_meta = {
                    "source": "pdf",
                    "producer": meta.get("producer") or "",
                    "creator": meta.get("creator") or "",
                    "creationDate": meta.get("creationDate") or "",
                    "modDate": meta.get("modDate") or "",
                    "title": meta.get("title") or "",
                    "author": meta.get("author") or "",
                }
                return raw_meta
        except Exception as e:
            logger.debug(f"PyMuPDF metadata extraction failed: {e}")

        # Fallback to pikepdf if installed
        try:
            import pikepdf
            with pikepdf.Pdf.open(pdf_path) as pdoc:
                pdoc_meta = pdoc.docinfo
                raw_meta = {
                    "source": "pikepdf",
                    "producer": str(pdoc_meta.get("/Producer", "")),
                    "creator": str(pdoc_meta.get("/Creator", "")),
                    "creationDate": str(pdoc_meta.get("/CreationDate", "")),
                    "modDate": str(pdoc_meta.get("/ModDate", "")),
                }
                return raw_meta
        except Exception:
            pass

    # 2. Try Pillow EXIF on image file
    if resolved_path.exists() and resolved_path.suffix.lower() in (".png", ".jpg", ".jpeg", ".tiff"):
        try:
            with Image.open(resolved_path) as img:
                exif = img.getexif()
                if exif:
                    exif_data = {
                        ExifTags.TAGS.get(k, str(k)): str(v)
                        for k, v in exif.items()
                        if k in ExifTags.TAGS
                    }
                    raw_meta = {
                        "source": "image_exif",
                        "producer": exif_data.get("Software", ""),
                        "creator": exif_data.get("Artist", ""),
                        "creationDate": exif_data.get("DateTimeOriginal", exif_data.get("DateTime", "")),
                        "modDate": exif_data.get("DateTime", ""),
                    }
                    return raw_meta
        except Exception as e:
            logger.debug(f"Pillow EXIF extraction failed: {e}")

    return raw_meta


def check_metadata(
    db: Session,
    document: Document,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Verify document metadata against configured forensic rules and application context.
    
    Signals:
    - ModDate later than CreationDate by more than metadata_max_gap_days
    - Producer or Creator matching suspicious editor list
    - CreationDate after document's own issued/registered date by more than gap, or after submission date
    - Missing metadata -> returns status 'unavailable'
    
    Returns dict:
        status: 'ok' | 'suspicious' | 'unavailable'
        signals: List[str]
        evidence: Dict containing signals, raw values, and details
    """
    cfg = config or {}
    max_gap_days = cfg.get("metadata_max_gap_days", 1)
    suspicious_producers = [
        s.lower()
        for s in cfg.get(
            "suspicious_producers",
            ["photoshop", "gimp", "canva", "paint", "image editor", "illustrator"],
        )
    ]

    resolved_path = resolve_file_path(document.file_path)
    raw_meta = extract_raw_metadata(resolved_path)

    # Check if metadata is absent
    has_values = any(
        raw_meta.get(k)
        for k in ("producer", "creator", "creationDate", "modDate")
    )
    if not has_values:
        return {
            "result": "unavailable",
            "probability": None,
            "signals": [],
            "evidence": {
                "status": "unavailable",
                "reason": "Document metadata is missing or unavailable.",
                "raw_metadata": raw_meta,
            },
        }

    signals: List[str] = []
    signal_details: List[str] = []

    creation_str = raw_meta.get("creationDate")
    mod_str = raw_meta.get("modDate")
    producer_str = (raw_meta.get("producer") or "").lower()
    creator_str = (raw_meta.get("creator") or "").lower()

    creation_dt = parse_pdf_date(creation_str)
    mod_dt = parse_pdf_date(mod_str)

    # 1. Producer / Creator check for suspicious image editors
    matched_editor: Optional[str] = None
    for editor in suspicious_producers:
        if editor in producer_str or editor in creator_str:
            matched_editor = editor
            break

    if matched_editor:
        signals.append("suspicious_producer")
        signal_details.append(
            f"Software / Producer contains suspicious editor string: '{matched_editor}'"
        )

    # 2. ModDate vs CreationDate gap check
    if creation_dt and mod_dt:
        gap_days = (mod_dt.date() - creation_dt.date()).days
        if gap_days > max_gap_days:
            signals.append("mod_date_gap_exceeded")
            signal_details.append(
                f"ModDate ({mod_dt.strftime('%Y-%m-%d')}) is {gap_days} days later than "
                f"CreationDate ({creation_dt.strftime('%Y-%m-%d')}), exceeding max allowed gap of {max_gap_days} day(s)."
            )

    # 3. CreationDate vs document issued/registered date and submission date
    app = db.get(Application, document.application_id)
    doc_date: Optional[date] = None

    for ef in document.extracted_fields:
        if ef.name in ("issued_date", "registered_date", "registration_date") and ef.value_normalized:
            try:
                doc_date = datetime.strptime(ef.value_normalized, "%Y-%m-%d").date()
                break
            except Exception:
                pass

    if creation_dt:
        c_date = creation_dt.date()
        if doc_date:
            date_gap = (c_date - doc_date).days
            if date_gap > max_gap_days + 15:  # Tolerance beyond issuance
                signals.append("creation_date_post_dated")
                signal_details.append(
                    f"CreationDate ({c_date}) is {date_gap} days after document issuance date ({doc_date})."
                )

        if app and app.submission_date and c_date > app.submission_date:
            signals.append("creation_date_after_submission")
            signal_details.append(
                f"CreationDate ({c_date}) is after application submission date ({app.submission_date})."
            )

    status = "suspicious" if signals else "ok"

    return {
        "result": status,
        "probability": None,
        "signals": signals,
        "evidence": {
            "status": status,
            "signals": signals,
            "signal_details": signal_details,
            "raw_metadata": raw_meta,
            "parsed_creation_date": creation_dt.isoformat() if creation_dt else None,
            "parsed_mod_date": mod_dt.isoformat() if mod_dt else None,
        },
    }
