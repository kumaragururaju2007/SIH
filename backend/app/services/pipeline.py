import logging
from pathlib import Path
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models import Document, ExtractedField, AuditLog, Application
from app.services.ocr import run_ocr, OcrResult
from app.services.qr import decode_qr
from app.services.classify import classify
from app.services.extract import get_extractor, ExtractedFieldData

logger = logging.getLogger(__name__)


def write_audit(
    db: Session,
    action: str,
    entity: str,
    details: Optional[Dict[str, Any]] = None,
    actor: str = "system",
) -> AuditLog:
    """Helper to record an audit log entry."""
    entry = AuditLog(
        actor=actor,
        action=action,
        entity=entity,
        details=details or {},
    )
    db.add(entry)
    db.commit()
    return entry


def resolve_file_path(file_path: str) -> Path:
    """Resolve document file path against current backend/workspace directories."""
    p = Path(file_path)
    if p.exists():
        return p

    # Try relative to workspace root (SIH/aicte-validator or SIH)
    backend_dir = Path(__file__).resolve().parent.parent.parent
    project_root = backend_dir.parent

    candidates = [
        backend_dir / p,
        project_root / p,
        project_root / "aicte-validator" / p,
        backend_dir.parent.parent / p,
    ]
    for c in candidates:
        if c.exists():
            return c

    # Normalize Windows backslashes
    alt_p = Path(str(file_path).replace("\\", "/"))
    for c in [backend_dir / alt_p, project_root / alt_p]:
        if c.exists():
            return c

    return p


def process_document(db: Session, document_id: int) -> Document:
    """Synchronous idempotent document processing pipeline:
    1. Runs OCR (OpenCV preprocessing, Tesseract / PaddleOCR fallback).
    2. Runs QR code decoding.
    3. Runs document classification.
    4. Runs field extraction (Rules / API LLM / Local LLM) and normalization.
    5. Clears previous ExtractedField records and saves updated state.
    6. Writes an audit log entry per step.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document with ID {document_id} not found.")

    resolved_path = resolve_file_path(doc.file_path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"Document file does not exist at {doc.file_path} (resolved: {resolved_path})")

    file_str = str(resolved_path)

    # 1. OCR Step
    ocr_res = run_ocr(file_str)
    write_audit(
        db=db,
        action="ocr_complete",
        entity=f"Document:{doc.id}",
        details={
            "mean_confidence": ocr_res.mean_confidence,
            "language": ocr_res.language,
            "words_count": len(ocr_res.words),
        },
    )

    # 2. QR Code Decoding Step
    qr_content = decode_qr(file_str)
    write_audit(
        db=db,
        action="qr_decode",
        entity=f"Document:{doc.id}",
        details={"has_qr": qr_content is not None, "length": len(qr_content) if qr_content else 0},
    )

    # 3. Document Classification Step
    doc_type, class_conf, class_reasons = classify(
        ocr_text=ocr_res.text,
        qr_text=qr_content,
        file_name=resolved_path.name,
    )
    write_audit(
        db=db,
        action="document_classification",
        entity=f"Document:{doc.id}",
        details={
            "doc_type": doc_type,
            "confidence": class_conf,
            "reasons": class_reasons,
        },
    )

    # 4. Field Extraction Step
    extracted_fields_dict: Dict[str, ExtractedFieldData] = {}
    if doc_type:
        extractor = get_extractor()
        extracted_fields_dict = extractor.extract(
            ocr_result=ocr_res,
            doc_type=doc_type,
            qr_text=qr_content,
        )
        write_audit(
            db=db,
            action="field_extraction",
            entity=f"Document:{doc.id}",
            details={"doc_type": doc_type, "fields_extracted": list(extracted_fields_dict.keys())},
        )
    else:
        write_audit(
            db=db,
            action="field_extraction_skipped",
            entity=f"Document:{doc.id}",
            details={"reason": "Document unclassified or below confidence threshold."},
        )

    # 5. Idempotent Database Save
    # Clear previous extracted fields for this document
    db.query(ExtractedField).filter(ExtractedField.document_id == doc.id).delete()

    # Update document row
    doc.ocr_text = ocr_res.text
    doc.ocr_confidence = ocr_res.mean_confidence
    doc.language = ocr_res.language
    doc.qr_text = qr_content
    doc.doc_type = doc_type

    # Insert new extracted fields
    for fname, fdata in extracted_fields_dict.items():
        ef = ExtractedField(
            document_id=doc.id,
            name=fdata.name,
            value_original=fdata.value_original,
            value_normalized=fdata.value_normalized,
            confidence=fdata.confidence,
            needs_verification=fdata.needs_verification,
        )
        db.add(ef)

    db.commit()
    db.refresh(doc)
    return doc
