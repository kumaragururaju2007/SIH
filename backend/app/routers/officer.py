import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Application,
    Document,
    Institution,
    InstitutionHistory,
    RuleResult,
    ConsistencyResult,
    AuthResult,
    DeficiencyReport,
    Review,
    AuditLog,
)
from app.schemas import (
    ApplicationResponse,
    InstitutionResponse,
    InstitutionHistoryResponse,
    DocumentWithResultsResponse,
    DocumentDetailResponse,
    CompletenessResponse,
    RuleResultResponse,
    ConsistencyComparison,
    ConsistencyComparisonSide,
    AuthResultResponse,
    DocumentForensicsResponse,
    AuditLogResponse,
    OfficerQueueItem,
    OfficerApplicationDetail,
    OverrideRequest,
    DecisionRequest,
    DeficiencyReportResponse,
    DeficiencyReportUpdateRequest,
)
from app.audit import log_action
from app.services.completeness import check_completeness
from app.services.labels import determine_document_label, determine_application_labels, load_label_config
from app.services.risk import calculate_application_risk
from app.services.auth.forensics import analyze_tampering
from app.services.auth.config import load_auth_config
from app.services.deficiency import (
    generate_deficiency_report,
    scan_for_forbidden_phrases,
    render_report_text,
    render_report_html,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/officer", tags=["officer"])

VALID_LABELS = {"verified", "needs_verification", "inconsistent", "possible_tampering"}
VALID_DECISIONS = {"approve", "reject", "send_deficiency"}


@router.get("/queue", response_model=List[OfficerQueueItem])
def get_officer_queue(
    request: Request,
    state: Optional[str] = Query(None, description="Filter by status / state"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    application_type: Optional[str] = Query(None, description="Filter by application type"),
    label: Optional[str] = Query(None, description="Filter by result label"),
    band: Optional[str] = Query(None, description="Filter by risk band (low, medium, high)"),
    db: Session = Depends(get_db),
):
    """
    Returns applications in status submitted or in_review (or filtered state),
    sorted by risk descending, each with institution, label, score, band, top factors,
    counts of issues, and whether it is a resubmission (parent link).
    """
    query = db.query(Application)

    target_status = state or status_filter
    if target_status:
        query = query.filter(Application.status == target_status)
    else:
        # Default queue view: submitted or in_review
        query = query.filter(Application.status.in_(["submitted", "in_review"]))

    if application_type:
        query = query.filter(Application.application_type == application_type)
    if label:
        query = query.filter(Application.label == label)
    if band:
        query = query.filter(Application.risk_band == band)

    apps = query.all()

    queue_items: List[OfficerQueueItem] = []
    for app in apps:
        inst = app.institution
        inst_name = inst.name if inst else "Unknown Institution"
        inst_state = inst.state if inst else "Unknown"

        # Calculate counts of issues
        failed_rules_count = (
            db.query(RuleResult)
            .filter(RuleResult.application_id == app.id, RuleResult.status == "failed")
            .count()
        )
        conflicts_count = (
            db.query(ConsistencyResult)
            .filter(ConsistencyResult.application_id == app.id, ConsistencyResult.status == "conflict")
            .count()
        )
        doc_ids = [d.id for d in app.documents]
        tampering_count = 0
        if doc_ids:
            tampering_count = (
                db.query(AuthResult)
                .filter(
                    AuthResult.document_id.in_(doc_ids),
                    AuthResult.check_type == "tampering",
                    AuthResult.result.in_(["suspicious", "high_suspicion"]),
                )
                .count()
            )

        missing_docs_count = (
            db.query(RuleResult)
            .filter(
                RuleResult.application_id == app.id,
                RuleResult.rule_id.startswith("REQ-"),
                RuleResult.status == "failed",
            )
            .count()
        )

        issue_counts = {
            "failed_rules": failed_rules_count,
            "consistency_conflicts": conflicts_count,
            "tampering_signals": tampering_count,
            "missing_documents": missing_docs_count,
        }

        # Top factors from stored risk_factors
        top_factors = []
        if app.risk_factors and isinstance(app.risk_factors, dict):
            top_factors = app.risk_factors.get("top_factors", [])

        queue_items.append(
            OfficerQueueItem(
                id=app.id,
                institution_id=app.institution_id,
                institution_name=inst_name,
                institution_state=inst_state,
                application_type=app.application_type,
                status=app.status,
                submission_date=app.submission_date,
                label=app.label,
                risk_score=app.risk_score,
                risk_band=app.risk_band,
                top_factors=top_factors,
                issue_counts=issue_counts,
                is_resubmission=app.parent_application_id is not None,
                parent_application_id=app.parent_application_id,
                created_at=app.created_at,
            )
        )

    # Sort by risk_score descending (None treated as -1)
    queue_items.sort(key=lambda x: (x.risk_score is not None, x.risk_score if x.risk_score is not None else -1), reverse=True)
    return queue_items


@router.get("/applications/{id}", response_model=OfficerApplicationDetail)
def get_officer_application_detail(id: int, db: Session = Depends(get_db)):
    """
    Full detail for an application under officer review:
    - documents with labels, override info, reasons, and extracted fields
    - rule results with clauses and evidence
    - consistency comparisons side by side
    - authentication results with forensic image paths
    - risk breakdown
    - deficiency report if any
    - institution history timeline
    - audit logs
    """
    app = db.get(Application, id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id {id} not found",
        )

    inst = app.institution
    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution associated with application {id} not found",
        )

    # Completeness
    comp_dict = check_completeness(db, id)
    comp_resp = CompletenessResponse(
        application_id=id,
        application_type=app.application_type,
        is_complete=comp_dict["is_complete"],
        required=comp_dict["required"],
        present=comp_dict["present"],
        missing=comp_dict["missing"],
        unrecognized=comp_dict["unrecognized"],
        duplicates_of_type=comp_dict["duplicates_of_type"],
        missing_findings=comp_dict["missing_findings"],
    )

    # Rule results
    sev_order = {"high": 0, "medium": 1, "low": 2}
    all_rrs = db.query(RuleResult).filter(RuleResult.application_id == id).all()
    sorted_all_rrs = sorted(all_rrs, key=lambda r: (sev_order.get(r.severity, 3), r.id))

    rrs_by_doc: Dict[Optional[int], List[RuleResultResponse]] = defaultdict(list)
    for r in sorted_all_rrs:
        rrs_by_doc[r.document_id].append(RuleResultResponse.model_validate(r))

    # Auth results
    doc_ids = [d.id for d in app.documents]
    auth_rows = db.query(AuthResult).filter(AuthResult.document_id.in_(doc_ids)).all() if doc_ids else []
    auth_by_doc: Dict[int, List[AuthResultResponse]] = defaultdict(list)
    auth_summary: Dict[str, int] = defaultdict(int)
    for ar in auth_rows:
        auth_by_doc[ar.document_id].append(AuthResultResponse.model_validate(ar))
        auth_summary[ar.result] += 1

    # Documents with results
    docs_with_results: List[DocumentWithResultsResponse] = []
    forensics_list: List[DocumentForensicsResponse] = []
    auth_cfg = load_auth_config()

    for doc in app.documents:
        doc_detail = DocumentDetailResponse.model_validate(doc)
        doc_rrs = rrs_by_doc.get(doc.id, [])
        doc_auth = auth_by_doc.get(doc.id, [])
        docs_with_results.append(
            DocumentWithResultsResponse(
                **doc_detail.model_dump(),
                rule_results=doc_rrs,
                authentication=doc_auth,
            )
        )

        # Build forensic item
        tamp_res = next((a for a in auth_rows if a.document_id == doc.id and a.check_type == "tampering"), None)
        ev = tamp_res.evidence if tamp_res and tamp_res.evidence else {}
        forensics_list.append(
            DocumentForensicsResponse(
                document_id=doc.id,
                doc_type=doc.doc_type,
                annotated_image_path=ev.get("annotated_path"),
                heatmap_image_path=ev.get("heatmap_path"),
                tampering_score=tamp_res.probability if tamp_res else None,
                status=tamp_res.result if tamp_res else "ok",
                regions=ev.get("regions", []),
                evidence=ev,
            )
        )

    # Consistency comparisons
    cr_rows = db.query(ConsistencyResult).filter(ConsistencyResult.application_id == id).all()
    consistency_comps: List[ConsistencyComparison] = []
    for r in cr_rows:
        l_ev = r.evidence.get("left", {}) if r.evidence else {}
        r_ev = r.evidence.get("right", {}) if r.evidence else {}
        left_side = ConsistencyComparisonSide(
            doc_type=l_ev.get("doc_type"),
            field=l_ev.get("field"),
            document_id=r.doc_a_id,
            original=r.value_a,
            normalized=l_ev.get("normalized"),
        )
        right_side = ConsistencyComparisonSide(
            doc_type=r_ev.get("doc_type"),
            field=r_ev.get("field"),
            document_id=r.doc_b_id,
            original=r.value_b,
            normalized=r_ev.get("normalized"),
        )
        consistency_comps.append(
            ConsistencyComparison(
                rule_id=r.rule_id,
                description=r.evidence.get("description") if r.evidence else None,
                kind=r.evidence.get("kind", "name") if r.evidence else "name",
                relation=r.relation,
                status=r.status,
                severity=r.severity,
                score=r.score,
                message=r.message,
                clause=r.clause,
                left=left_side,
                right=right_side,
                explanation=f"Comparison score: {r.score:.1f}",
                evidence=r.evidence,
            )
        )

    c_summary = {
        "match": sum(1 for c in consistency_comps if c.status == "match"),
        "partial": sum(1 for c in consistency_comps if c.status == "partial"),
        "conflict": sum(1 for c in consistency_comps if c.status == "conflict"),
        "not_evaluable": sum(1 for c in consistency_comps if c.status == "not_evaluable"),
        "total": len(consistency_comps),
    }

    # Deficiency report
    latest_report = (
        db.query(DeficiencyReport)
        .filter(DeficiencyReport.application_id == id)
        .order_by(DeficiencyReport.created_at.desc())
        .first()
    )
    deficiency_report_dict = None
    if latest_report:
        deficiency_report_dict = {
            "id": latest_report.id,
            "status": latest_report.status,
            "content": latest_report.content,
            "approved_by": latest_report.approved_by,
            "created_at": latest_report.created_at.isoformat() if latest_report.created_at else None,
        }

    # Audit logs
    audit_rows = (
        db.query(AuditLog)
        .filter(
            (AuditLog.entity == f"application:{id}")
            | (AuditLog.entity.in_([f"document:{d.id}" for d in app.documents]))
        )
        .order_by(AuditLog.timestamp.desc())
        .all()
    )

    # History timeline
    histories = (
        db.query(InstitutionHistory)
        .filter(InstitutionHistory.institution_id == inst.id)
        .order_by(InstitutionHistory.year.desc())
        .all()
    )

    auth_payload = {
        "application_id": id,
        "summary": dict(auth_summary),
        "total_checks": len(auth_rows),
    }

    return OfficerApplicationDetail(
        application=ApplicationResponse.model_validate(app),
        institution=InstitutionResponse.model_validate(inst),
        history_timeline=[InstitutionHistoryResponse.model_validate(h) for h in histories],
        documents=docs_with_results,
        completeness=comp_resp,
        rule_results=[RuleResultResponse.model_validate(r) for r in sorted_all_rrs],
        consistency=consistency_comps,
        consistency_summary=c_summary,
        authentication=auth_payload,
        forensics=forensics_list,
        risk_breakdown=app.risk_factors if isinstance(app.risk_factors, dict) else {},
        deficiency_report=deficiency_report_dict,
        audit_logs=[AuditLogResponse.model_validate(al) for al in audit_rows],
    )


@router.post("/applications/{id}/override")
def override_document_label(
    id: int,
    payload: OverrideRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Override a document's validation label by an officer.
    - Reason is mandatory (min 10 characters).
    - Preserves original system label and shows both.
    - Writes an audit log entry.
    - Recalculates the composite application label.
    """
    if len(payload.reason.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Override reason must be at least 10 characters long.",
        )

    if payload.new_label not in VALID_LABELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid label '{payload.new_label}'. Must be one of {sorted(VALID_LABELS)}.",
        )

    app = db.get(Application, id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id {id} not found",
        )

    doc = db.get(Document, payload.document_id)
    if not doc or doc.application_id != id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {payload.document_id} not found under application {id}",
        )

    actor = request.headers.get("x-demo-user", "officer")

    # Preserve original system label
    if not doc.system_label:
        doc.system_label = doc.label or "needs_verification"

    orig_system_label = doc.system_label
    old_label = doc.label

    doc.override_label = payload.new_label
    doc.override_reason = payload.reason.strip()
    doc.override_by = actor
    doc.label = payload.new_label
    db.commit()

    # Recompute application composite label
    comp = check_completeness(db, id)
    app_labels = determine_application_labels(db, app, completeness=comp, recompute_documents=False)

    # Write audit log entry
    log_action(
        db=db,
        actor=actor,
        action="override_document_label",
        entity=f"document:{doc.id}",
        details={
            "application_id": id,
            "document_id": doc.id,
            "doc_type": doc.doc_type,
            "system_label": orig_system_label,
            "old_label": old_label,
            "new_label": payload.new_label,
            "reason": payload.reason.strip(),
            "new_application_label": app.label,
        },
    )

    return {
        "status": "success",
        "document_id": doc.id,
        "label": doc.label,
        "system_label": doc.system_label,
        "override_label": doc.override_label,
        "override_reason": doc.override_reason,
        "override_by": doc.override_by,
        "application_label": app.label,
    }


@router.post("/applications/{id}/decision")
def record_officer_decision(
    id: int,
    payload: DecisionRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Record officer final decision: approve | reject | send_deficiency.
    Updates application status and writes an audit log entry.
    """
    if payload.decision not in VALID_DECISIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision '{payload.decision}'. Must be one of {sorted(VALID_DECISIONS)}.",
        )

    app = db.get(Application, id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id {id} not found",
        )

    actor = request.headers.get("x-demo-user", "officer")
    previous_status = app.status

    if payload.decision == "approve":
        app.status = "approved"
    elif payload.decision == "reject":
        app.status = "rejected"
    elif payload.decision == "send_deficiency":
        app.status = "deficiency_sent"

    # Record review entry
    review = Review(
        application_id=app.id,
        officer_name=actor,
        decision=payload.decision,
        comments=payload.comments,
    )
    db.add(review)
    db.commit()
    db.refresh(app)

    # Write audit log
    log_action(
        db=db,
        actor=actor,
        action="officer_decision",
        entity=f"application:{id}",
        details={
            "application_id": id,
            "decision": payload.decision,
            "comments": payload.comments,
            "previous_status": previous_status,
            "new_status": app.status,
        },
    )

    return {
        "status": "success",
        "application_id": id,
        "decision": payload.decision,
        "previous_status": previous_status,
        "new_status": app.status,
        "comments": payload.comments,
    }


# ---------------- Deficiency Report Scrutiny Endpoints ----------------
@router.post("/applications/{id}/deficiency-report/generate", response_model=DeficiencyReportResponse)
def generate_report_endpoint(
    id: int,
    request: Request,
    language: str = Query("en", description="Report language: en or hi"),
    llm_polish: bool = Query(False, description="Optional LLM rephrasing"),
    db: Session = Depends(get_db),
):
    """Generate structured deficiency report from deterministic findings and consistency conflicts."""
    app = db.get(Application, id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id {id} not found",
        )

    actor = request.headers.get("x-demo-user", "officer")
    report = generate_deficiency_report(db, id, lang=language, llm_polish=llm_polish)

    log_action(
        db=db,
        actor=actor,
        action="generate_deficiency_report",
        entity=f"deficiency_report:{report.id}",
        details={
            "application_id": id,
            "report_id": report.id,
            "status": report.status,
            "total_items": report.content.get("total_items"),
            "language": language,
        },
    )
    return report


@router.put("/applications/{id}/deficiency-report", response_model=DeficiencyReportResponse)
def update_deficiency_report(
    id: int,
    payload: DeficiencyReportUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Officer edits deficiency report items, summary, or wording.
    Includes safeguards against prohibited guidance wording.
    """
    app = db.get(Application, id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id {id} not found",
        )

    report = (
        db.query(DeficiencyReport)
        .filter(DeficiencyReport.application_id == id)
        .order_by(DeficiencyReport.created_at.desc())
        .first()
    )
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No deficiency report exists for application {id}",
        )

    actor = request.headers.get("x-demo-user", "officer")
    content = dict(report.content)

    if payload.items is not None:
        for it in payload.items:
            for fld in ("title", "what_failed", "why", "what_to_resubmit"):
                forbidden = scan_for_forbidden_phrases(it.get(fld, ""))
                if forbidden:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Safeguard violation: forbidden phrase(s) {forbidden} found in item field '{fld}'.",
                    )
        content["items"] = payload.items
        content["total_items"] = len(payload.items)
        content["high_severity_count"] = sum(1 for it in payload.items if it.get("severity") == "high")
        content["medium_severity_count"] = sum(1 for it in payload.items if it.get("severity") == "medium")
        content["low_severity_count"] = sum(1 for it in payload.items if it.get("severity") == "low")
        if len(payload.items) == 0:
            content["summary"] = "No deficiencies found. Application is compliant."
        elif len(payload.items) == 1:
            content["summary"] = "1 item needs attention"
        else:
            content["summary"] = f"{len(payload.items)} items need attention"

    if payload.summary is not None:
        forbidden = scan_for_forbidden_phrases(payload.summary)
        if forbidden:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Safeguard violation: forbidden phrase(s) {forbidden} in summary.",
            )
        content["summary"] = payload.summary

    if payload.content is not None:
        content.update(payload.content)

    lang = content.get("language", "en")
    content["rendered_text"] = render_report_text(app, content.get("items", []), content.get("summary", ""), lang=lang)
    content["rendered_html"] = render_report_html(app, content.get("items", []), content.get("summary", ""), lang=lang)

    report.content = content
    db.commit()
    db.refresh(report)

    log_action(
        db=db,
        actor=actor,
        action="update_deficiency_report",
        entity=f"deficiency_report:{report.id}",
        details={"application_id": id, "total_items": content.get("total_items")},
    )
    return report


@router.post("/applications/{id}/deficiency-report/approve", response_model=DeficiencyReportResponse)
def approve_deficiency_report(
    id: int,
    request: Request,
    approved_by: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Approve a deficiency report. Only approved reports may be dispatched."""
    app = db.get(Application, id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id {id} not found",
        )

    report = (
        db.query(DeficiencyReport)
        .filter(DeficiencyReport.application_id == id)
        .order_by(DeficiencyReport.created_at.desc())
        .first()
    )
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No deficiency report found for application {id}",
        )

    actor = approved_by or request.headers.get("x-demo-user", "officer")
    report.status = "approved"
    report.approved_by = actor
    db.commit()
    db.refresh(report)

    log_action(
        db=db,
        actor=actor,
        action="approve_deficiency_report",
        entity=f"deficiency_report:{report.id}",
        details={"application_id": id, "report_id": report.id, "approved_by": actor, "status": "approved"},
    )
    return report


@router.post("/applications/{id}/deficiency-report/send")
def send_deficiency_report(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Send an approved deficiency report to the institution.
    Only reports with status 'approved' can be sent.
    Updates application status to 'deficiency_sent' and writes notification to audit log.
    """
    app = db.get(Application, id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id {id} not found",
        )

    report = (
        db.query(DeficiencyReport)
        .filter(DeficiencyReport.application_id == id)
        .order_by(DeficiencyReport.created_at.desc())
        .first()
    )
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No deficiency report found for application {id}",
        )

    if report.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot send deficiency report in '{report.status}' status. Only approved reports can be sent.",
        )

    actor = request.headers.get("x-demo-user", "officer")
    report.status = "sent"
    app.status = "deficiency_sent"
    db.commit()

    inst_name = app.institution.name if app.institution else "Applicant Institution"
    log_action(
        db=db,
        actor=actor,
        action="send_deficiency_notification",
        entity=f"application:{id}",
        details={
            "application_id": id,
            "report_id": report.id,
            "recipient_institution": inst_name,
            "delivery_channel": "official_email_and_portal",
            "summary": report.content.get("summary"),
            "sent_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {
        "status": "sent",
        "application_id": id,
        "report_id": report.id,
        "application_status": app.status,
        "notification_logged": True,
    }

