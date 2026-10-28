from datetime import date
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.audit import log_action
from app.models import Application, Document, RuleResult
from app.schemas import RuleOutcome, CompletenessResponse, ValidationResponse
from app.services.completeness import check_completeness, get_application_type_spec
from app.services.rules_engine import load_rules, evaluate_rule, to_date_obj


def run_rules(
    db: Session,
    application_id: int,
    config_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Run deterministic rules engine across all documents of an application.
    Clears previous RuleResults for the application, making it fully idempotent.
    """
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise ValueError(f"Application with ID {application_id} not found.")

    # 1. Determine submission_date (default to today if unset)
    sub_date = application.submission_date or date.today()
    if isinstance(sub_date, str):
        sub_date = to_date_obj(sub_date) or date.today()

    # 2. Build application parameters
    app_spec = get_application_type_spec(application.application_type, config_dir=config_dir)
    app_params = dict(app_spec.get("parameters", {}))
    app_params["submission_date"] = sub_date
    app_params["application_type"] = application.application_type

    # Ensure min_area_sqm fallback if specified on application type
    if "min_area_sqm" not in app_params and "min_area_sqm" in app_spec:
        app_params["min_area_sqm"] = app_spec["min_area_sqm"]

    # 3. Check completeness
    completeness_data = check_completeness(db, application_id, config_dir=config_dir)
    missing_findings: List[RuleOutcome] = completeness_data["missing_findings"]
    active_docs: Dict[str, Document] = completeness_data["active_documents"]

    # 4. Load all rules
    rules_by_doc = load_rules(config_dir=config_dir)

    all_outcomes: List[RuleOutcome] = []

    # Missing documents produce failed RuleOutcomes
    all_outcomes.extend(missing_findings)

    # 5. Evaluate rules for each active document
    for doc_type, doc in active_docs.items():
        doc_rules = rules_by_doc.get(doc_type, [])
        fields_map = {f.name: f for f in doc.extracted_fields}

        for rule in doc_rules:
            # Check applies_to filter
            if rule.applies_to and application.application_type not in rule.applies_to:
                continue

            outcome = evaluate_rule(
                rule=rule,
                extracted_fields=fields_map,
                app_params=app_params,
                document_id=doc.id,
            )
            all_outcomes.append(outcome)

    # 6. Idempotently replace RuleResult records in database
    db.query(RuleResult).filter(RuleResult.application_id == application_id).delete()

    for outcome in all_outcomes:
        rr = RuleResult(
            application_id=application_id,
            document_id=outcome.document_id,
            rule_id=outcome.rule_id,
            status=outcome.status,
            passed=outcome.passed,
            severity=outcome.severity,
            message=outcome.message,
            clause=outcome.clause,
            evidence=outcome.evidence,
        )
        db.add(rr)

    db.commit()

    # 7. Tally counts
    passed_count = sum(1 for o in all_outcomes if o.status == "passed")
    failed_count = sum(1 for o in all_outcomes if o.status == "failed")
    not_evaluable_count = sum(1 for o in all_outcomes if o.status == "not_evaluable")
    total_count = len(all_outcomes)

    summary = {
        "passed": passed_count,
        "failed": failed_count,
        "not_evaluable": not_evaluable_count,
        "total": total_count,
    }

    # 8. Audit log
    log_action(
        db=db,
        actor="system",
        action="run_rules",
        entity=f"application:{application_id}",
        details=summary,
    )

    is_valid = (failed_count == 0 and not_evaluable_count == 0)

    # Format completeness response
    comp_resp = CompletenessResponse(
        application_id=application_id,
        application_type=application.application_type,
        is_complete=completeness_data["is_complete"],
        required=completeness_data["required"],
        present=completeness_data["present"],
        missing=completeness_data["missing"],
        unrecognized=completeness_data["unrecognized"],
        duplicates_of_type=completeness_data["duplicates_of_type"],
        missing_findings=missing_findings,
    )

    return {
        "application_id": application_id,
        "status": "completed",
        "is_valid": is_valid,
        "completeness": comp_resp,
        "summary": summary,
        "findings": all_outcomes,
    }
