import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from PIL import Image
import imagehash
from sqlalchemy.orm import Session

from app.models import Document, Application, Institution, ExtractedField
from app.services.pipeline import resolve_file_path

logger = logging.getLogger(__name__)


def are_applications_linked(app_a: Application, app_b: Application) -> bool:
    """Return True if two applications belong to the same institution/resubmission lineage.
    Documents inside the same application, or draft copies and resubmissions linked
    by parent_application_id, must NOT count as duplicates of the original.
    """
    if app_a.id == app_b.id:
        return True

    # Same parent application
    if (
        app_a.parent_application_id is not None
        and app_a.parent_application_id == app_b.parent_application_id
    ):
        return True

    # One is parent of the other
    if app_a.parent_application_id is not None and app_a.parent_application_id == app_b.id:
        return True
    if app_b.parent_application_id is not None and app_b.parent_application_id == app_a.id:
        return True

    return False


def is_earlier_document(
    current_doc: Document,
    current_app: Application,
    other_doc: Document,
    other_app: Application,
) -> bool:
    """A document can only be a duplicate or reuse of an earlier submitted document."""
    if current_app.submission_date and other_app.submission_date:
        if other_app.submission_date < current_app.submission_date:
            return True
        if other_app.submission_date > current_app.submission_date:
            return False
    # If same date or unset, earlier application or earlier document sequence applies
    if other_app.id != current_app.id:
        return other_app.id < current_app.id
    return other_doc.id < current_doc.id


def compute_document_phash(file_path: str) -> Optional[str]:
    """Compute 256-bit body perceptual hash using imagehash.phash."""
    try:
        resolved = resolve_file_path(file_path)
        if not resolved.exists():
            return None
        with Image.open(resolved) as img:
            gray = img.convert("L")
            w, h = gray.size
            # Focus on central body content to distinguish unique documents sharing standard header/footer templates
            body = gray.crop((int(w * 0.1), int(h * 0.25), int(w * 0.9), int(h * 0.75)))
            return str(imagehash.phash(body, hash_size=16))
    except Exception as e:
        logger.warning(f"Failed to compute perceptual hash for {file_path}: {e}")
        return None


def check_duplicates(
    db: Session,
    document: Document,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Check a document for exact duplicates, near duplicates (pHash), and ID reuse across other applications.
    
    Returns a dict with:
        result: 'ok' | 'suspicious'
        signals: List of detected signal names
        evidence: Full dictionary of matches and references
    """
    cfg = config or {}
    phash_threshold = cfg.get("phash_hamming_near_duplicate", 1)

    current_app = db.get(Application, document.application_id)
    if not current_app:
        return {
            "result": "ok",
            "signals": [],
            "evidence": {"details": "Application not found for document"},
        }

    # Ensure document has phash populated with 16x16 (len == 64)
    if not document.phash or len(document.phash) != 64:
        computed_phash = compute_document_phash(document.file_path)
        if computed_phash:
            document.phash = computed_phash
            db.commit()

    signals: List[str] = []
    exact_matches: List[Dict[str, Any]] = []
    near_matches: List[Dict[str, Any]] = []
    id_reuses: List[Dict[str, Any]] = []

    # 1. Exact Duplicate (sha256)
    if document.sha256:
        other_sha_docs = (
            db.query(Document)
            .filter(Document.id != document.id, Document.sha256 == document.sha256)
            .all()
        )
        for other in other_sha_docs:
            other_app = db.get(Application, other.application_id)
            if not other_app or are_applications_linked(current_app, other_app):
                continue
            if not is_earlier_document(document, current_app, other, other_app):
                continue
            other_inst = db.get(Institution, other_app.institution_id)
            exact_matches.append({
                "document_id": other.id,
                "application_id": other_app.id,
                "institution_id": other_app.institution_id,
                "institution_name": other_inst.name if other_inst else "Unknown",
                "sha256": other.sha256,
            })

    if exact_matches:
        signals.append("exact_duplicate")

    # 2. Near Duplicate (pHash Hamming distance)
    if document.phash and document.doc_type:
        try:
            curr_hash = imagehash.hex_to_hash(document.phash)
            other_phash_docs = (
                db.query(Document)
                .filter(
                    Document.id != document.id,
                    Document.doc_type == document.doc_type,
                    Document.phash.isnot(None),
                )
                .all()
            )
            for other in other_phash_docs:
                if not other.phash or len(other.phash) != len(document.phash):
                    continue
                other_app = db.get(Application, other.application_id)
                if not other_app or are_applications_linked(current_app, other_app):
                    continue
                if not is_earlier_document(document, current_app, other, other_app):
                    continue
                other_hash = imagehash.hex_to_hash(other.phash)
                dist = curr_hash - other_hash
                if dist <= phash_threshold:
                    other_inst = db.get(Institution, other_app.institution_id)
                    near_matches.append({
                        "document_id": other.id,
                        "application_id": other_app.id,
                        "institution_id": other_app.institution_id,
                        "institution_name": other_inst.name if other_inst else "Unknown",
                        "hamming_distance": int(dist),
                        "phash": other.phash,
                    })
        except Exception as e:
            logger.warning(f"Perceptual hash comparison failed for document {document.id}: {e}")

    if near_matches:
        signals.append("near_duplicate")

    # 3. Certificate or Registration Number Reuse
    target_fields = [
        f
        for f in document.extracted_fields
        if f.name in ("certificate_number", "registration_number")
        and f.value_normalized
    ]

    for f in target_fields:
        other_fields = (
            db.query(ExtractedField)
            .filter(
                ExtractedField.name == f.name,
                ExtractedField.value_normalized == f.value_normalized,
                ExtractedField.document_id != document.id,
            )
            .all()
        )
        for of in other_fields:
            other_doc = db.get(Document, of.document_id)
            if not other_doc:
                continue
            other_app = db.get(Application, other_doc.application_id)
            if not other_app or are_applications_linked(current_app, other_app):
                continue
            if not is_earlier_document(document, current_app, other_doc, other_app):
                continue
            other_inst = db.get(Institution, other_app.institution_id)
            id_reuses.append({
                "field_name": f.name,
                "reused_value": f.value_normalized,
                "document_id": other_doc.id,
                "application_id": other_app.id,
                "institution_id": other_app.institution_id,
                "institution_name": other_inst.name if other_inst else "Unknown",
            })

    if id_reuses:
        signals.append("id_reuse")

    is_suspicious = len(signals) > 0
    result = "suspicious" if is_suspicious else "ok"

    evidence = {
        "duplicate_found": is_suspicious,
        "signals": signals,
        "exact_matches": exact_matches,
        "near_matches": near_matches,
        "id_reuses": id_reuses,
        "details": (
            f"Detected {len(signals)} duplicate/reuse signal(s): {', '.join(signals)}"
            if is_suspicious
            else "No duplicate documents or reused identifiers found in unlinked applications."
        ),
    }

    return {
        "result": result,
        "probability": None,
        "signals": signals,
        "evidence": evidence,
    }
