from collections import defaultdict
from datetime import datetime, timezone
import os
import hashlib
from pathlib import Path
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Application, Institution, Document, RuleResult, ConsistencyResult, AuthResult, DeficiencyReport
from app.schemas import (
    ApplicationCreate,
    ApplicationResponse,
    InstitutionResponse,
    DocumentResponse,
    DocumentDetailResponse,
    ExtractedFieldResponse,
    CompletenessResponse,
    ValidationResponse,
    ResultsResponse,
    DocumentWithResultsResponse,
    RuleResultResponse,
    ConsistencyComparison,
    ConsistencyComparisonSide,
    ConsistencySectionResponse,
    AuthResultResponse,
    DocumentAuthenticationResponse,
    AuthenticationSectionResponse,
    DocumentForensicsResponse,
    DeficiencyReportResponse,
)
from app.audit import log_action
from app.services.pipeline import process_document, resolve_file_path
from app.services.completeness import check_completeness
from app.services.validation import run_rules
from app.services.consistency import run_consistency
from app.services.auth.run import run_authentication
from app.services.auth.forensics import analyze_tampering
from app.services.auth.config import load_auth_config
from app.services.labels import determine_application_labels
from app.services.risk import calculate_application_risk

router = APIRouter(tags=["applications & documents"])


# ---------------- Applications Endpoints ----------------
@router.post("/applications", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    institution = db.get(Institution, payload.institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution with id {payload.institution_id} not found",
        )

    if payload.parent_application_id is not None:
        parent = db.get(Application, payload.parent_application_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent application with id {payload.parent_application_id} not found",
            )

    application = Application(
        institution_id=payload.institution_id,
        application_type=payload.application_type,
        status="draft",
        parent_application_id=payload.parent_application_id,
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    log_action(
        db=db,
        actor="system",
        action="create_application",
        entity=f"application:{application.id}",
        details={
            "application_id": application.id,
            "institution_id": application.institution_id,
            "application_type": application.application_type,
            "status": application.status,
        },
    )

    return application


@router.get("/institutions", response_model=List[InstitutionResponse])
def list_institutions(db: Session = Depends(get_db)):
    """List all institutions for role switching and institution portal."""
    return db.query(Institution).order_by(Institution.name).all()


@router.get("/applications", response_model=List[ApplicationResponse])
def list_applications(
    institution_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List applications optionally filtered by institution_id or status."""
    query = db.query(Application)
    if institution_id is not None:
        query = query.filter(Application.institution_id == institution_id)
    if status is not None:
        query = query.filter(Application.status == status)
    return query.order_by(Application.id.desc()).all()


@router.get("/applications/{id}", response_model=ApplicationResponse)
def get_application(id: int, db: Session = Depends(get_db)):
    application = db.get(Application, id)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id {id} not found",
        )
    return application


@router.post("/applications/{id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a document for an application:
    Saves file to UPLOAD_DIR/<app_id>/<filename>, computes SHA-256, and creates a Document record.
    """
    application = db.get(Application, id)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id {id} not found",
        )

    # Prepare upload directory
    app_upload_dir = Path(settings.UPLOAD_DIR) / str(application.id)
    app_upload_dir.mkdir(parents=True, exist_ok=True)

    dest_path = app_upload_dir / file.filename

    content = await file.read()
    sha256_hash = hashlib.sha256(content).hexdigest()

    with open(dest_path, "wb") as f:
        f.write(content)

    doc = Document(
        application_id=application.id,
        file_path=str(dest_path),
        sha256=sha256_hash,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    log_action(
        db=db,
        actor="system",
        action="upload_document",
        entity=f"document:{doc.id}",
        details={
            "document_id": doc.id,
            "application_id": application.id,
            "filename": file.filename,
            "sha256": sha256_hash,
        },
    )

    return doc


@router.post("/applications/{id}/process-all", response_model=List[DocumentDetailResponse])
def process_all_application_documents(id: int, db: Session = Depends(get_db)):
    """Process every document belonging to the given application."""
    application = db.get(Application, id)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id {id} not found",
        )

    processed_docs = []
    for doc in application.documents:
        p_doc = process_document(db, doc.id)
        processed_docs.append(p_doc)

    return processed_docs


# ---------------- Documents Endpoints ----------------
@router.post("/documents/{id}/process", response_model=DocumentDetailResponse)
def process_single_document(id: int, db: Session = Depends(get_db)):
    """Run full pipeline (OCR, QR, Classification, Extraction, Normalization) on a single document."""
    doc = db.get(Document, id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {id} not found",
        )

    try:
        updated_doc = process_document(db, id)
        return updated_doc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}",
        )


@router.get("/documents/{id}", response_model=DocumentDetailResponse)
def get_document(id: int, db: Session = Depends(get_db)):
    """Return document details, OCR text, confidence, and extracted fields."""
    doc = db.get(Document, id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {id} not found",
        )
    return doc


@router.get("/documents/{id}/file")
def get_document_file(id: int, db: Session = Depends(get_db)):
    """Return actual document file for viewing in the UI."""
    doc = db.get(Document, id)
    if not doc or not doc.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {id} not found",
        )
    resolved = resolve_file_path(doc.file_path)
    if not resolved.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File on disk not found for document {id}",
        )
    ext = resolved.suffix.lower()
    media_type = "application/pdf" if ext == ".pdf" else "image/png"
    return FileResponse(str(resolved), media_type=media_type)


# ---------------- Validation & Completeness Endpoints ----------------
@router.get("/applications/{id}/completeness", response_model=CompletenessResponse)
def get_application_completeness(id: int, db: Session = Depends(get_db)):
    """Pre-submission document completeness self-check for an institution."""
    app = db.get(Application, id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id {id} not found",
        )

    try:
        comp = check_completeness(db, id)
        return CompletenessResponse(
            application_id=id,
            application_type=app.application_type,
            is_complete=comp["is_complete"],
            required=comp["required"],
            present=comp["present"],
            missing=comp["missing"],
            unrecognized=comp["unrecognized"],
            duplicates_of_type=comp["duplicates_of_type"],
            missing_findings=comp["missing_findings"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Completeness check failed: {str(e)}",
        )


@router.post("/applications/{id}/validate", response_model=ValidationResponse)
def validate_application(id: int, db: Session = Depends(get_db)):
    """
    Process any pending documents, evaluate completeness, execute deterministic per-document rules,
    and perform cross-document consistency checks.
    """
    app = db.get(Application, id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id {id} not found",
        )

    try:
        # 1. Run OCR/extraction pipeline on any unprocessed uploaded documents
        for doc in app.documents:
            if doc.ocr_text is None:
                process_document(db, doc.id)

        # 2. Run rules engine and completeness check
        rules_result = run_rules(db, id)

        # 3. Run cross-document consistency check
        consistency_comparisons = run_consistency(db, id)

        c_summary = {
            "match": sum(1 for c in consistency_comparisons if c.status == "match"),
            "partial": sum(1 for c in consistency_comparisons if c.status == "partial"),
            "conflict": sum(1 for c in consistency_comparisons if c.status == "conflict"),
            "not_evaluable": sum(1 for c in consistency_comparisons if c.status == "not_evaluable"),
            "total": len(consistency_comparisons),
        }

        # Valid only if no rule failures, no not_evaluables, and zero consistency conflicts
        is_valid = rules_result["is_valid"] and (c_summary["conflict"] == 0)

        # 4. Run document authentication checks (Core Feature 2)
        auth_results = run_authentication(db, id)

        # 5. Determine labels (dry run: update document/app labels for inspection)
        comp_dict = rules_result["completeness"]
        labels_res = determine_application_labels(db, app, completeness=comp_dict)

        # 6. Calculate explainable risk score & band (dry run)
        risk_res = calculate_application_risk(db, id, completeness=comp_dict)

        return ValidationResponse(
            application_id=id,
            status="completed",
            is_valid=is_valid,
            completeness=rules_result["completeness"],
            summary=rules_result["summary"],
            findings=rules_result["findings"],
            consistency=consistency_comparisons,
            consistency_summary=c_summary,
            authentication=auth_results,
            label=labels_res["label"],
            risk_score=risk_res["risk_score"],
            risk_band=risk_res["risk_band"],
            risk_breakdown=risk_res,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Application validation failed: {str(e)}",
        )


@router.post("/applications/{id}/submit", response_model=ApplicationResponse)
def submit_application(id: int, request: Request, db: Session = Depends(get_db)):
    """
    Runs the full end-to-end pipeline:
    1. Process any pending documents (OCR, QR, classification, field extraction)
    2. Deterministic rule evaluations & completeness check
    3. Cross-document consistency checks
    4. Document authentication checks (forensics, metadata, duplicate, QR, registry)
    5. Result labels determination (verified, needs_verification, inconsistent, possible_tampering)
    6. Explainable risk scoring (0-100, bands, top factors)
    7. Updates application status to 'submitted' and logs audit entry.
    """
    app = db.get(Application, id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id {id} not found",
        )

    try:
        # 1. Process all pending documents
        for doc in app.documents:
            if doc.ocr_text is None:
                process_document(db, doc.id)

        # 2. Run rules engine & completeness check
        rules_result = run_rules(db, id)

        # 3. Run cross-document consistency check
        consistency_comps = run_consistency(db, id)

        # 4. Run document authentication checks
        auth_results = run_authentication(db, id)

        # 5. Determine labels for all documents & application
        comp_dict = rules_result["completeness"]
        labels_res = determine_application_labels(db, app, completeness=comp_dict)

        # 6. Calculate explainable risk score & band
        risk_res = calculate_application_risk(db, id, completeness=comp_dict)

        # 7. Update status to submitted & set submission date
        app.status = "submitted"
        if not app.submission_date:
            app.submission_date = datetime.now(timezone.utc).date()

        db.commit()
        db.refresh(app)

        actor = request.headers.get("x-demo-user", "institution")
        log_action(
            db=db,
            actor=actor,
            action="submit_application",
            entity=f"application:{id}",
            details={
                "application_id": id,
                "status": app.status,
                "label": app.label,
                "risk_score": app.risk_score,
                "risk_band": app.risk_band,
            },
        )

        return app
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Application submission failed: {str(e)}",
        )


@router.get("/applications/{id}/consistency", response_model=ConsistencySectionResponse)
def get_application_consistency(id: int, db: Session = Depends(get_db)):
    """Return only cross-document consistency comparison results in a side-by-side friendly structure."""
    app = db.get(Application, id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id {id} not found",
        )

    try:
        cr_rows = db.query(ConsistencyResult).filter(ConsistencyResult.application_id == id).all()
        if not cr_rows:
            comparisons = run_consistency(db, id)
        else:
            comparisons = []
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
                comparisons.append(
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

        summary = {
            "match": sum(1 for c in comparisons if c.status == "match"),
            "partial": sum(1 for c in comparisons if c.status == "partial"),
            "conflict": sum(1 for c in comparisons if c.status == "conflict"),
            "not_evaluable": sum(1 for c in comparisons if c.status == "not_evaluable"),
            "total": len(comparisons),
        }

        return ConsistencySectionResponse(
            application_id=id,
            summary=summary,
            comparisons=comparisons,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch consistency results: {str(e)}",
        )


@router.get("/applications/{id}/results", response_model=ResultsResponse)
def get_application_results(id: int, db: Session = Depends(get_db)):
    """
    Return all documents with extracted fields, completeness report, per-document rules,
    and cross-document consistency comparisons.
    """
    app = db.get(Application, id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id {id} not found",
        )

    try:
        comp = check_completeness(db, id)
        comp_resp = CompletenessResponse(
            application_id=id,
            application_type=app.application_type,
            is_complete=comp["is_complete"],
            required=comp["required"],
            present=comp["present"],
            missing=comp["missing"],
            unrecognized=comp["unrecognized"],
            duplicates_of_type=comp["duplicates_of_type"],
            missing_findings=comp["missing_findings"],
        )

        sev_order = {"high": 0, "medium": 1, "low": 2}
        all_rrs = db.query(RuleResult).filter(RuleResult.application_id == id).all()
        sorted_all_rrs = sorted(all_rrs, key=lambda r: (sev_order.get(r.severity, 3), r.id))

        rrs_by_doc: Dict[Optional[int], List[RuleResultResponse]] = defaultdict(list)
        for r in sorted_all_rrs:
            rrs_by_doc[r.document_id].append(RuleResultResponse.model_validate(r))

        # Fetch or run authentication checks
        auth_rows = db.query(AuthResult).filter(AuthResult.document_id.in_([d.id for d in app.documents])).all()
        if not auth_rows:
            run_authentication(db, id)
            auth_rows = db.query(AuthResult).filter(AuthResult.document_id.in_([d.id for d in app.documents])).all()

        auth_by_doc: Dict[int, List[AuthResultResponse]] = defaultdict(list)
        for ar in auth_rows:
            auth_by_doc[ar.document_id].append(AuthResultResponse.model_validate(ar))

        docs_with_results = []
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

        summary = {
            "passed": sum(1 for r in all_rrs if r.status == "passed"),
            "failed": sum(1 for r in all_rrs if r.status == "failed"),
            "not_evaluable": sum(1 for r in all_rrs if r.status == "not_evaluable"),
            "total": len(all_rrs),
        }

        # Fetch or run consistency comparisons
        cr_rows = db.query(ConsistencyResult).filter(ConsistencyResult.application_id == id).all()
        if not cr_rows:
            consistency_comps = run_consistency(db, id)
        else:
            consistency_comps = []
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

        return ResultsResponse(
            application_id=id,
            application_type=app.application_type,
            completeness=comp_resp,
            documents=docs_with_results,
            all_rule_results=[RuleResultResponse.model_validate(r) for r in sorted_all_rrs],
            summary=summary,
            consistency=consistency_comps,
            consistency_summary=c_summary,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch application results: {str(e)}",
        )


@router.get("/applications/{id}/authentication", response_model=AuthenticationSectionResponse)
def get_application_authentication(id: int, db: Session = Depends(get_db)):
    """Return only the authentication section (duplicate, metadata, tampering, QR, registry) for an application."""
    app = db.get(Application, id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id {id} not found",
        )

    try:
        doc_ids = [d.id for d in app.documents]
        auth_rows = db.query(AuthResult).filter(AuthResult.document_id.in_(doc_ids)).all() if doc_ids else []
        if not auth_rows and doc_ids:
            run_authentication(db, id)
            auth_rows = db.query(AuthResult).filter(AuthResult.document_id.in_(doc_ids)).all()

        auth_by_doc: Dict[int, List[AuthResultResponse]] = defaultdict(list)
        summary: Dict[str, int] = defaultdict(int)
        for ar in auth_rows:
            auth_by_doc[ar.document_id].append(AuthResultResponse.model_validate(ar))
            summary[ar.result] += 1

        doc_list = []
        for doc in app.documents:
            doc_list.append(
                DocumentAuthenticationResponse(
                    document_id=doc.id,
                    doc_type=doc.doc_type,
                    checks=auth_by_doc.get(doc.id, []),
                )
            )

        return AuthenticationSectionResponse(
            application_id=id,
            summary=dict(summary),
            documents=doc_list,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch application authentication: {str(e)}",
        )


@router.get("/documents/{id}/forensics", response_model=DocumentForensicsResponse)
def get_document_forensics(id: int, db: Session = Depends(get_db)):
    """Return forensic annotated image path, heatmap, regions, and tampering diagnostics for a document."""
    doc = db.get(Document, id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {id} not found",
        )

    try:
        auth_res = (
            db.query(AuthResult)
            .filter(AuthResult.document_id == id, AuthResult.check_type == "tampering")
            .first()
        )

        if not auth_res:
            app = db.get(Application, doc.application_id)
            app_code = f"A{app.institution_id:02d}" if app and app.institution_id else f"app_{doc.application_id}"
            cfg = load_auth_config()
            tamper_dict = analyze_tampering(doc.file_path, app_code, doc.id, cfg)
            auth_res = AuthResult(
                document_id=doc.id,
                check_type="tampering",
                result=tamper_dict.get("result", "ok"),
                probability=tamper_dict.get("probability"),
                evidence=tamper_dict.get("evidence"),
            )
            db.add(auth_res)
            db.commit()
            db.refresh(auth_res)

        evidence = auth_res.evidence or {}
        return DocumentForensicsResponse(
            document_id=doc.id,
            doc_type=doc.doc_type,
            annotated_image_path=evidence.get("annotated_path"),
            heatmap_image_path=evidence.get("heatmap_path"),
            tampering_score=auth_res.probability,
            status=auth_res.result,
            regions=evidence.get("regions", []),
            evidence=evidence,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch document forensics: {str(e)}",
        )


@router.get("/applications/{id}/deficiency-report", response_model=DeficiencyReportResponse)
def get_application_deficiency_report(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Get deficiency report for an application.
    Institution sees it ONLY when status is approved or sent.
    Officer can see drafts.
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

    user = request.headers.get("x-demo-user", "")
    role = request.headers.get("x-demo-role", "")
    is_officer = role == "officer" or "officer" in user.lower()

    if not is_officer and report.status not in ("approved", "sent"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Deficiency report is currently in officer review and has not yet been approved or issued.",
        )

    return report



