import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import (
    Application,
    Document,
    ExtractedField,
    RuleResult,
    ConsistencyResult,
    AuthResult,
)
from app.schemas import (
    ApplicationResponse,
    DocumentResponse,
    DocumentDetailResponse,
    ValidationResponse,
    ComparisonItem,
    DraftComparisonResponse,
)
from app.audit import log_action
from app.services.pipeline import process_document, resolve_file_path
from app.services.completeness import check_completeness
from app.services.validation import run_rules
from app.services.consistency import run_consistency
from app.services.auth.run import run_authentication
from app.services.labels import determine_application_labels
from app.services.risk import calculate_application_risk

logger = logging.getLogger(__name__)

router = APIRouter(tags=["drafts & resubmissions"])


@router.post("/applications/{id}/drafts", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_draft_copy(id: int, request: Request, db: Session = Depends(get_db)):
    """
    Creates an independent DRAFT COPY of an application:
    - Sets parent_application_id to the source application ID.
    - Copies Document records and their ExtractedFields.
    - The original application and all its results remain completely untouched.
    """
    parent = db.get(Application, id)
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent application with id {id} not found",
        )

    actor = request.headers.get("x-demo-user", "institution")

    # Create new draft application
    draft = Application(
        institution_id=parent.institution_id,
        application_type=parent.application_type,
        status="draft",
        parent_application_id=parent.id,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    # Deep copy documents and extracted fields
    for doc in parent.documents:
        new_doc = Document(
            application_id=draft.id,
            doc_type=doc.doc_type,
            file_path=doc.file_path,
            sha256=doc.sha256,
            phash=doc.phash,
            language=doc.language,
            ocr_text=doc.ocr_text,
            ocr_confidence=doc.ocr_confidence,
            qr_text=doc.qr_text,
            label=doc.label,
            system_label=doc.system_label,
            reasons=doc.reasons,
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

        for ef in doc.extracted_fields:
            new_ef = ExtractedField(
                document_id=new_doc.id,
                name=ef.name,
                value_original=ef.value_original,
                value_normalized=ef.value_normalized,
                confidence=ef.confidence,
                needs_verification=ef.needs_verification,
            )
            db.add(new_ef)

    db.commit()
    db.refresh(draft)

    log_action(
        db=db,
        actor=actor,
        action="create_draft_copy",
        entity=f"application:{draft.id}",
        details={
            "draft_id": draft.id,
            "parent_id": parent.id,
            "documents_copied": len(parent.documents),
        },
    )

    return draft


@router.post("/drafts/{id}/documents", response_model=DocumentDetailResponse, status_code=status.HTTP_201_CREATED)
async def upload_draft_document(
    id: int,
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Upload a replacement or missing document into a draft copy.
    A replacement of the same doc_type supersedes the copied one in the draft only.
    """
    draft = db.get(Application, id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Draft application with id {id} not found",
        )

    # Save uploaded file
    draft_upload_dir = Path(settings.UPLOAD_DIR) / f"draft_{draft.id}"
    draft_upload_dir.mkdir(parents=True, exist_ok=True)
    dest_path = draft_upload_dir / file.filename

    content = await file.read()
    sha256_hash = hashlib.sha256(content).hexdigest()

    with open(dest_path, "wb") as f:
        f.write(content)

    new_doc = Document(
        application_id=draft.id,
        file_path=str(dest_path),
        sha256=sha256_hash,
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    # Run processing pipeline on new document to detect doc_type and extract fields
    processed_doc = process_document(db, new_doc.id)

    # Check for existing document of the same doc_type in this draft only (superseding)
    if processed_doc.doc_type:
        superseded_docs = (
            db.query(Document)
            .filter(
                Document.application_id == draft.id,
                Document.doc_type == processed_doc.doc_type,
                Document.id != processed_doc.id,
            )
            .all()
        )
        for old_doc in superseded_docs:
            db.delete(old_doc)
        db.commit()

    actor = request.headers.get("x-demo-user", "institution") if request else "institution"
    log_action(
        db=db,
        actor=actor,
        action="upload_draft_replacement",
        entity=f"document:{processed_doc.id}",
        details={
            "draft_id": draft.id,
            "document_id": processed_doc.id,
            "doc_type": processed_doc.doc_type,
            "filename": file.filename,
        },
    )

    return processed_doc


@router.post("/drafts/{id}/recheck", response_model=ValidationResponse)
def recheck_draft(id: int, request: Request, db: Session = Depends(get_db)):
    """
    Runs the full validation and scrutiny pipeline on the draft application.
    Reuses existing pipeline code paths.
    Duplicate checks ignore parent applications and unlinked drafts.
    """
    draft = db.get(Application, id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Draft application with id {id} not found",
        )

    # 1. Process any pending documents
    for doc in draft.documents:
        if doc.ocr_text is None:
            resolved = resolve_file_path(doc.file_path)
            if resolved.exists():
                process_document(db, doc.id)

    # 2. Run deterministic per-document rules
    rules_result = run_rules(db, id)

    # 3. Run cross-document consistency checks
    consistency_comps = run_consistency(db, id)

    # 4. Run document authentication checks (ignores parent application in duplicate check)
    auth_results = run_authentication(db, id)

    # 5. Determine document and application labels
    comp = rules_result["completeness"]
    labels_res = determine_application_labels(db, draft, completeness=comp)

    # 6. Calculate risk score and top factors
    risk_res = calculate_application_risk(db, id, completeness=comp)

    c_summary = {
        "match": sum(1 for c in consistency_comps if c.status == "match"),
        "partial": sum(1 for c in consistency_comps if c.status == "partial"),
        "conflict": sum(1 for c in consistency_comps if c.status == "conflict"),
        "not_evaluable": sum(1 for c in consistency_comps if c.status == "not_evaluable"),
        "total": len(consistency_comps),
    }

    actor = request.headers.get("x-demo-user", "institution")
    log_action(
        db=db,
        actor=actor,
        action="recheck_draft",
        entity=f"application:{draft.id}",
        details={
            "draft_id": draft.id,
            "label": draft.label,
            "risk_score": draft.risk_score,
            "risk_band": draft.risk_band,
        },
    )

    return ValidationResponse(
        application_id=draft.id,
        status="completed",
        is_valid=rules_result["is_valid"] and (c_summary["conflict"] == 0),
        completeness=rules_result["completeness"],
        summary=rules_result["summary"],
        findings=rules_result["findings"],
        consistency=consistency_comps,
        consistency_summary=c_summary,
        authentication=auth_results,
        label=labels_res["label"],
        risk_score=risk_res["risk_score"],
        risk_band=risk_res["risk_band"],
        risk_breakdown=risk_res,
    )


def extract_application_issue_dict(db: Session, app_id: int) -> Dict[str, Dict[str, Any]]:
    """Helper to extract normalized map of all regulatory/compliance issues for an application."""
    issues: Dict[str, Dict[str, Any]] = {}

    # 1. Missing documents
    comp = check_completeness(db, app_id)
    for m in comp.get("missing", []):
        key = f"MISSING:{m}"
        issues[key] = {
            "key": key,
            "category": "missing_document",
            "title": f"Missing Mandatory Document: {m.replace('_', ' ').title()}",
            "clause": "Handbook Chapter 1 Mandatory Documents",
            "doc_type": m,
            "message": f"Mandatory document '{m}' is missing",
            "severity": "high",
        }

    # 2. Failed rules
    rrs = db.query(RuleResult).filter(RuleResult.application_id == app_id).all()
    for r in rrs:
        if not r.passed or r.status == "failed":
            doc = db.get(Document, r.document_id) if r.document_id else None
            doc_type = doc.doc_type if doc else "document"
            key = f"RULE:{r.rule_id}:{doc_type}"
            issues[key] = {
                "key": key,
                "category": "rule_failure",
                "title": f"Rule Failure: {r.rule_id}",
                "clause": r.clause or "Handbook Approval Norms",
                "doc_type": doc_type,
                "message": r.message,
                "severity": r.severity or "high",
            }

    # 3. Consistency conflicts & partials
    crs = db.query(ConsistencyResult).filter(ConsistencyResult.application_id == app_id).all()
    for c in crs:
        if c.status in ("conflict", "partial"):
            key = f"CONSISTENCY:{c.rule_id}"
            issues[key] = {
                "key": key,
                "category": "consistency",
                "title": f"Consistency Issue: {c.rule_id}",
                "clause": c.clause or "Handbook Title Continuity",
                "doc_type": None,
                "message": c.message,
                "severity": c.severity or "high",
            }

    # 4. Authentication issues (registry, tampering, duplicate)
    app = db.get(Application, app_id)
    if app:
        doc_ids = [d.id for d in app.documents]
        ars = db.query(AuthResult).filter(AuthResult.document_id.in_(doc_ids)).all() if doc_ids else []
        for ar in ars:
            doc = db.get(Document, ar.document_id)
            doc_type = doc.doc_type if doc else "document"
            if ar.check_type == "tampering" and ar.result in ("suspicious", "high_suspicion"):
                key = f"AUTH:tampering:{doc_type}"
                issues[key] = {
                    "key": key,
                    "category": "authentication",
                    "title": f"Authenticity Signal: {doc_type.replace('_', ' ').title()}",
                    "clause": "Handbook Authenticity Standards",
                    "doc_type": doc_type,
                    "message": f"Tampering score: {round((ar.probability or 0.0)*100, 1)}%",
                    "severity": "high",
                }
            elif ar.check_type == "registry" and ar.result == "mismatch":
                key = f"AUTH:registry:{doc_type}"
                issues[key] = {
                    "key": key,
                    "category": "authentication",
                    "title": f"Registry Discrepancy: {doc_type.replace('_', ' ').title()}",
                    "clause": "Handbook Registry Verification",
                    "doc_type": doc_type,
                    "message": "Mismatch with government registry record",
                    "severity": "high",
                }

    return issues


@router.get("/drafts/{id}/comparison", response_model=DraftComparisonResponse)
def get_draft_comparison(id: int, db: Session = Depends(get_db)):
    """
    Before (Parent) vs After (Draft) Comparison:
    - Resolved issues (present before, fixed now)
    - Remaining issues (present before and still present)
    - New issues (not present before, introduced in draft)
    - Summary metrics and sentence ("X failures before, Y remaining")
    - Label and risk score changes
    """
    draft = db.get(Application, id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Draft application with id {id} not found",
        )

    if not draft.parent_application_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application is not a draft copy linked to a parent application.",
        )

    parent = db.get(Application, draft.parent_application_id)
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent application with id {draft.parent_application_id} not found",
        )

    parent_issues = extract_application_issue_dict(db, parent.id)
    draft_issues = extract_application_issue_dict(db, draft.id)

    p_keys = set(parent_issues.keys())
    d_keys = set(draft_issues.keys())

    resolved_keys = p_keys - d_keys
    remaining_keys = p_keys & d_keys
    new_keys = d_keys - p_keys

    resolved_items: List[ComparisonItem] = []
    for k in sorted(resolved_keys):
        item = parent_issues[k]
        resolved_items.append(
            ComparisonItem(
                id=item["key"],
                category=item["category"],
                title=item["title"],
                status="resolved",
                before_message=item["message"],
                after_message="Resolved in resubmission",
                clause=item["clause"],
                doc_type=item["doc_type"],
                severity=item["severity"],
            )
        )

    remaining_items: List[ComparisonItem] = []
    for k in sorted(remaining_keys):
        p_item = parent_issues[k]
        d_item = draft_issues[k]
        remaining_items.append(
            ComparisonItem(
                id=p_item["key"],
                category=p_item["category"],
                title=p_item["title"],
                status="remaining",
                before_message=p_item["message"],
                after_message=d_item["message"],
                clause=p_item["clause"],
                doc_type=p_item["doc_type"],
                severity=p_item["severity"],
            )
        )

    new_items: List[ComparisonItem] = []
    for k in sorted(new_keys):
        item = draft_issues[k]
        new_items.append(
            ComparisonItem(
                id=item["key"],
                category=item["category"],
                title=item["title"],
                status="new",
                before_message=None,
                after_message=item["message"],
                clause=item["clause"],
                doc_type=item["doc_type"],
                severity=item["severity"],
            )
        )

    before_count = len(parent_issues)
    remaining_count = len(remaining_items)
    summary_sentence = f"{before_count} failures before, {remaining_count} remaining"

    overall = {
        "before_label": parent.label,
        "after_label": draft.label,
        "before_risk_score": parent.risk_score,
        "after_risk_score": draft.risk_score,
        "before_risk_band": parent.risk_band,
        "after_risk_band": draft.risk_band,
    }

    return DraftComparisonResponse(
        draft_id=draft.id,
        parent_id=parent.id,
        summary_sentence=summary_sentence,
        before_failures_count=before_count,
        remaining_failures_count=remaining_count,
        resolved_count=len(resolved_items),
        new_count=len(new_items),
        resolved_issues=resolved_items,
        remaining_issues=remaining_items,
        new_issues=new_items,
        overall=overall,
    )


@router.post("/drafts/{id}/submit-resubmission")
def submit_resubmission(id: int, request: Request, db: Session = Depends(get_db)):
    """
    Submits a draft copy as an official resubmission:
    - Status becomes 'submitted'.
    - Still linked to parent_application_id.
    - Appears in officer review queue marked as 'resubmission of #<parent_id>'.
    - Parent application status updated to 'superseded' (documented architectural choice).
    - Writes audit log.
    """
    draft = db.get(Application, id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Draft application with id {id} not found",
        )

    if not draft.parent_application_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application is not a draft copy linked to a parent application.",
        )

    parent = db.get(Application, draft.parent_application_id)
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent application with id {draft.parent_application_id} not found",
        )

    actor = request.headers.get("x-demo-user", "institution")

    # Update draft to submitted
    draft.status = "submitted"
    draft.submission_date = datetime.now(timezone.utc).date()

    # Documented architectural choice: update parent status to 'superseded'
    parent.status = "superseded"
    db.commit()

    log_action(
        db=db,
        actor=actor,
        action="submit_resubmission",
        entity=f"application:{draft.id}",
        details={
            "application_id": draft.id,
            "parent_application_id": parent.id,
            "parent_status": parent.status,
            "status": draft.status,
        },
    )

    return {
        "status": "submitted",
        "application_id": draft.id,
        "parent_application_id": parent.id,
        "is_resubmission": True,
        "message": f"Resubmission of #{parent.id} submitted successfully.",
    }
