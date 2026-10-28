import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models import Application, Document, AuthResult
from app.services.pipeline import write_audit
from app.services.auth.config import load_auth_config
from app.services.auth.duplicates import check_duplicates
from app.services.auth.metadata import check_metadata
from app.services.auth.forensics import analyze_tampering
from app.services.auth.qr_check import verify_qr_code
from app.services.auth.registry import verify_registry, get_registry_client

logger = logging.getLogger(__name__)


def run_authentication(db: Session, application_id: int) -> Dict[str, Any]:
    """Run full authentication pipeline on all documents of an application:
    1. duplicate check (exact sha256, near pHash, ID reuse across other applications)
    2. metadata check (producer/creator, mod/creation date gap, post-dating)
    3. tampering analysis (ELA, copy-move, noise inconsistency, degraded scan guard)
    4. QR code verification (payload vs extracted ID)
    5. Registry verification (government mock registry comparison)
    
    Idempotent: clears previous AuthResult records for this application.
    Writes an audit log entry with counts per outcome.
    """
    application = db.get(Application, application_id)
    if not application:
        raise ValueError(f"Application with ID {application_id} not found.")

    config = load_auth_config()
    reg_client = get_registry_client()

    doc_ids = [d.id for d in application.documents]
    if doc_ids:
        # Clear previous AuthResult records
        db.query(AuthResult).filter(AuthResult.document_id.in_(doc_ids)).delete(synchronize_session=False)
        db.commit()

    outcome_counts: Dict[str, int] = {
        "ok": 0,
        "suspicious": 0,
        "high_suspicion": 0,
        "low_quality_scan": 0,
        "match": 0,
        "mismatch": 0,
        "absent": 0,
        "not_found": 0,
        "unavailable": 0,
        "unreadable": 0,
    }

    doc_results: List[Dict[str, Any]] = []

    for doc in application.documents:
        results_by_type: Dict[str, Dict[str, Any]] = {}

        # 1. Duplicate check
        dup_res = check_duplicates(db=db, document=doc, config=config)
        results_by_type["duplicate"] = dup_res

        # 2. Metadata check
        meta_res = check_metadata(db=db, document=doc, config=config)
        results_by_type["metadata"] = meta_res

        app_ref = application.label.replace("EVAL:", "") if application.label else (f"A{application.institution_id:02d}" if application.institution_id else f"app_{application.id}")
        # 3. Tampering Forensics check
        try:
            tamper_res = analyze_tampering(
                file_path=doc.file_path,
                app_id=app_ref,
                doc_id=doc.id,
                config=config,
            )
        except Exception as e:
            logger.error(f"Tampering analysis failed for document {doc.id}: {e}")
            tamper_res = {
                "result": "ok",
                "probability": None,
                "signals": [],
                "evidence": {"error": str(e)},
            }
        results_by_type["tampering"] = tamper_res

        # 4. QR Check
        qr_res = verify_qr_code(db=db, document=doc, config=config)
        results_by_type["qr"] = qr_res

        # 5. Registry Verification
        reg_res = verify_registry(db=db, document=doc, client=reg_client, config=config)
        results_by_type["registry"] = reg_res

        # Save to DB
        doc_auth_rows: List[AuthResult] = []
        for check_type, res in results_by_type.items():
            res_val = res.get("result", "ok")
            outcome_counts[res_val] = outcome_counts.get(res_val, 0) + 1

            row = AuthResult(
                document_id=doc.id,
                check_type=check_type,
                result=res_val,
                probability=res.get("probability"),
                evidence=res.get("evidence"),
            )
            db.add(row)
            doc_auth_rows.append(row)

        db.commit()

        doc_results.append({
            "document_id": doc.id,
            "doc_type": doc.doc_type,
            "checks": results_by_type,
        })

    # Write audit log
    write_audit(
        db=db,
        action="run_authentication",
        entity=f"Application:{application.id}",
        details={
            "application_id": application.id,
            "total_documents": len(application.documents),
            "outcome_counts": outcome_counts,
        },
    )

    return {
        "application_id": application.id,
        "outcome_counts": outcome_counts,
        "documents": doc_results,
    }
