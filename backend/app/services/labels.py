import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Application, Document, RuleResult, ConsistencyResult, AuthResult

logger = logging.getLogger(__name__)


def load_label_config(config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Load label determination configuration from YAML."""
    if config_dir is None:
        config_dir = Path(settings.CONFIG_DIR)

    label_file = config_dir / "labels" / "label_config.yaml"
    if not label_file.exists():
        candidate = Path(__file__).resolve().parent.parent.parent / "configs" / "labels" / "label_config.yaml"
        if candidate.exists():
            label_file = candidate

    if not label_file.exists():
        return {
            "label_hierarchy": {
                "precedence": ["possible_tampering", "inconsistent", "needs_verification", "verified"]
            }
        }

    with open(label_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


LABEL_RANKS: Dict[str, int] = {
    "possible_tampering": 4,
    "inconsistent": 3,
    "needs_verification": 2,
    "verified": 1,
}


def determine_document_label(
    db: Session,
    document: Document,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Determine the deterministic label and reasons list for a single document.
    
    Precedence: possible_tampering > inconsistent > needs_verification > verified
    """
    cfg = config or load_label_config()

    # Gather results for this document
    auth_rows = db.query(AuthResult).filter(AuthResult.document_id == document.id).all()
    auth_map: Dict[str, AuthResult] = {r.check_type: r for r in auth_rows}

    rule_rows = db.query(RuleResult).filter(RuleResult.document_id == document.id).all()
    
    consistency_rows = (
        db.query(ConsistencyResult)
        .filter(
            (ConsistencyResult.doc_a_id == document.id) | (ConsistencyResult.doc_b_id == document.id)
        )
        .all()
    )

    tamp_row = auth_map.get("tampering")
    dup_row = auth_map.get("duplicate")
    meta_row = auth_map.get("metadata")
    qr_row = auth_map.get("qr")
    reg_row = auth_map.get("registry")

    tampering_reasons: List[Dict[str, Any]] = []
    inconsistent_reasons: List[Dict[str, Any]] = []
    verification_reasons: List[Dict[str, Any]] = []
    verified_confirmations: List[Dict[str, Any]] = []

    # 1. Check possible_tampering
    # Condition 1a: tampering status is high_suspicion
    if tamp_row and tamp_row.result == "high_suspicion":
        tampering_reasons.append({
            "type": "high_tampering_score",
            "ref_id": tamp_row.id,
            "category": "authentication",
            "summary": f"Classical forensics signaled high tampering probability (score: {tamp_row.probability})",
        })

    # Condition 1b: tampering status is suspicious with a supporting signal
    # Supporting signals: registry mismatch, QR mismatch, or suspicious metadata
    has_supporting_signal = False
    supporting_details: List[str] = []
    if reg_row and reg_row.result == "mismatch":
        has_supporting_signal = True
        supporting_details.append("registry field mismatch")
    if qr_row and qr_row.result == "mismatch":
        has_supporting_signal = True
        supporting_details.append("QR payload identifier mismatch")
    if meta_row and meta_row.result == "suspicious":
        has_supporting_signal = True
        supporting_details.append("suspicious editor metadata signature")

    if tamp_row and tamp_row.result == "suspicious" and has_supporting_signal:
        tampering_reasons.append({
            "type": "corroborated_tampering",
            "ref_id": tamp_row.id,
            "category": "authentication",
            "summary": f"Forensic tampering signal (score: {tamp_row.probability}) corroborated by {', '.join(supporting_details)}",
        })

    # Condition 1c: exact or near duplicate, or certificate number reuse across applications
    if dup_row and dup_row.evidence and dup_row.evidence.get("duplicate_found"):
        dup_sigs = dup_row.evidence.get("signals", [])
        tampering_reasons.append({
            "type": "duplicate_reuse",
            "ref_id": dup_row.id,
            "category": "authentication",
            "summary": f"Duplicate document or identifier reuse detected across applications: {', '.join(dup_sigs)}",
        })

    # 2. Check inconsistent
    # Condition 2a: failed rule (any severity)
    for r in rule_rows:
        if not r.passed or r.status == "failed":
            inconsistent_reasons.append({
                "type": "rule_failed",
                "ref_id": r.id,
                "category": "rule",
                "summary": f"Failed approval rule {r.rule_id}: {r.message}",
            })

    # Condition 2b: consistency conflict
    for c in consistency_rows:
        if c.status == "conflict":
            inconsistent_reasons.append({
                "type": "consistency_conflict",
                "ref_id": c.id,
                "category": "consistency",
                "summary": f"Cross-document consistency conflict on {c.rule_id}: {c.message}",
            })

    # Condition 2c: registry mismatch without tampering signal
    if reg_row and reg_row.result == "mismatch" and not tampering_reasons:
        diffs = reg_row.evidence.get("differing_fields", []) if reg_row.evidence else []
        diff_str = ", ".join(f"{d.get('field')} ({d.get('registry_value')} vs {d.get('extracted_value')})" for d in diffs)
        inconsistent_reasons.append({
            "type": "registry_mismatch",
            "ref_id": reg_row.id,
            "category": "authentication",
            "summary": f"Government registry record discrepancy: {diff_str if diff_str else 'Field mismatch'}",
        })

    # 3. Check needs_verification
    # Condition 3a: not_evaluable rule
    for r in rule_rows:
        if r.status == "not_evaluable":
            verification_reasons.append({
                "type": "rule_not_evaluable",
                "ref_id": r.id,
                "category": "rule",
                "summary": f"Rule {r.rule_id} could not be evaluated deterministically: {r.message}",
            })

    # Condition 3b: partial consistency match
    for c in consistency_rows:
        if c.status == "partial":
            verification_reasons.append({
                "type": "consistency_partial",
                "ref_id": c.id,
                "category": "consistency",
                "summary": f"Partial cross-document match on {c.rule_id}: {c.message}",
            })

    # Condition 3c: QR absent or unreadable
    if qr_row and qr_row.result in ("absent", "unreadable"):
        verification_reasons.append({
            "type": "qr_absent_unreadable",
            "ref_id": qr_row.id,
            "category": "authentication",
            "summary": f"Document QR code is {qr_row.result} (requires manual visual review)",
        })

    # Condition 3d: registry unavailable or not_found
    if reg_row and reg_row.result in ("unavailable", "not_found"):
        verification_reasons.append({
            "type": "registry_unverified",
            "ref_id": reg_row.id,
            "category": "authentication",
            "summary": f"Registry verification {reg_row.result}: official record not confirmed online",
        })

    # Condition 3e: low OCR confidence
    if document.ocr_confidence is not None and document.ocr_confidence < 0.60:
        verification_reasons.append({
            "type": "low_ocr_confidence",
            "ref_id": document.id,
            "category": "ocr",
            "summary": f"OCR mean confidence ({round(document.ocr_confidence * 100, 1)}%) is below verification threshold",
        })

    # Condition 3f: unrecognized document type
    if not document.doc_type or document.doc_type in ("unknown", "unclassified"):
        verification_reasons.append({
            "type": "unrecognized_doc_type",
            "ref_id": document.id,
            "category": "classification",
            "summary": "Document could not be classified into any approved document type",
        })

    # Condition 3g: low_quality_scan
    if tamp_row and tamp_row.result == "low_quality_scan":
        verification_reasons.append({
            "type": "low_quality_scan",
            "ref_id": tamp_row.id,
            "category": "forensics",
            "summary": "Document is flagged as a degraded or poor-quality scan (blur or low resolution)",
        })

    # 4. Check verified (positive confirmations)
    if reg_row and reg_row.result == "match":
        verified_confirmations.append({
            "type": "registry_confirmed",
            "ref_id": reg_row.id,
            "category": "authentication",
            "summary": "Official government registry record verified and matches document fields",
        })
    if qr_row and qr_row.result == "match":
        verified_confirmations.append({
            "type": "qr_confirmed",
            "ref_id": qr_row.id,
            "category": "authentication",
            "summary": "Security QR code decoded successfully and matches document extracted identifier",
        })
    if rule_rows and all(r.passed for r in rule_rows):
        verified_confirmations.append({
            "type": "rules_passed",
            "ref_id": document.id,
            "category": "rule",
            "summary": f"All {len(rule_rows)} approval norms and document criteria evaluated and passed",
        })

    # Select final label by strict precedence
    if tampering_reasons:
        system_label = "possible_tampering"
        active_reasons = tampering_reasons
    elif inconsistent_reasons:
        system_label = "inconsistent"
        active_reasons = inconsistent_reasons
    elif verification_reasons:
        system_label = "needs_verification"
        active_reasons = verification_reasons
    elif verified_confirmations:
        system_label = "verified"
        active_reasons = verified_confirmations
    else:
        # Default fallback if unverified
        system_label = "needs_verification"
        active_reasons = [{
            "type": "insufficient_confirmation",
            "ref_id": document.id,
            "category": "system",
            "summary": "Document has no positive confirmation from registry, QR, or verified rules",
        }]

    # Apply officer override if active
    final_label = document.override_label if document.override_label else system_label

    # Save to database
    document.system_label = system_label
    document.label = final_label
    document.reasons = active_reasons
    db.commit()

    return {
        "document_id": document.id,
        "doc_type": document.doc_type,
        "label": final_label,
        "system_label": system_label,
        "is_overridden": document.override_label is not None,
        "override_reason": document.override_reason,
        "override_by": document.override_by,
        "reasons": active_reasons,
    }


def determine_application_labels(
    db: Session,
    application: Application,
    completeness: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
    recompute_documents: bool = True,
) -> Dict[str, Any]:
    """Determine labels for all documents and composite label for the application.
    
    Application label = worst document label (precedence: possible_tampering > inconsistent > needs_verification > verified).
    A missing required document makes the application at least inconsistent (finding MISSING).
    """
    cfg = config or load_label_config()

    doc_results: List[Dict[str, Any]] = []
    worst_rank = 0
    worst_label = "verified"

    for doc in application.documents:
        if recompute_documents:
            d_res = determine_document_label(db=db, document=doc, config=cfg)
        else:
            d_res = {
                "document_id": doc.id,
                "doc_type": doc.doc_type,
                "label": doc.label or doc.system_label or "needs_verification",
                "system_label": doc.system_label or "needs_verification",
                "is_overridden": doc.override_label is not None,
                "override_reason": doc.override_reason,
                "override_by": doc.override_by,
                "reasons": doc.reasons or [],
            }
        doc_results.append(d_res)
        rank = LABEL_RANKS.get(d_res["label"], 1)
        if rank > worst_rank:
            worst_rank = rank
            worst_label = d_res["label"]

    app_reasons: List[Dict[str, Any]] = []

    # Check for missing required documents
    missing_docs: List[str] = []
    if completeness:
        if isinstance(completeness, dict):
            missing_docs = completeness.get("missing_documents") or completeness.get("missing", [])
        elif hasattr(completeness, "missing"):
            missing_docs = list(completeness.missing)
        elif hasattr(completeness, "missing_documents"):
            missing_docs = list(completeness.missing_documents)
    elif application.rule_results:
        for r in application.rule_results:
            if r.rule_id.startswith("REQ-") and not r.passed:
                missing_docs.append(r.rule_id.replace("REQ-", ""))

    if missing_docs:
        # A missing required document makes the application at least inconsistent
        missing_min_rank = LABEL_RANKS["inconsistent"]
        if worst_rank < missing_min_rank:
            worst_rank = missing_min_rank
            worst_label = "inconsistent"

        app_reasons.append({
            "type": "missing_required_document",
            "ref_id": application.id,
            "category": "completeness",
            "summary": f"Application is missing required mandatory document(s): {', '.join(missing_docs)}",
        })

    # Collect top reasons from contributing documents
    for d in doc_results:
        for r in d.get("reasons", []):
            item = dict(r)
            item["document_id"] = d["document_id"]
            item["doc_type"] = d["doc_type"]
            app_reasons.append(item)

    # Save to Application
    application.label = worst_label
    application.reasons = app_reasons
    db.commit()

    return {
        "application_id": application.id,
        "label": worst_label,
        "reasons": app_reasons,
        "documents": doc_results,
    }
