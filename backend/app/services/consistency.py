import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

import yaml
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Application, Document, Institution, ConsistencyResult
from app.audit import log_action
from app.schemas import ConsistencyComparison, ConsistencyComparisonSide
from app.services.completeness import check_completeness
from app.services.rules_engine import ConfigValidationError, to_date_obj
from app.services.matching import (
    calculate_name_score,
    compare_ids,
    compare_dates,
    compare_addresses,
    load_name_normalization_config,
)


class ConsistencyRuleDefinition(BaseModel):
    id: str
    description: str
    kind: str = Field(pattern="^(name|id|date_order|address)$")
    left: str
    right: Union[str, List[str]]
    relation: str = Field(pattern="^(equals|any_of|date_before_or_equal)$")
    thresholds: Dict[str, float] = Field(default_factory=lambda: {"match_min": 85.0, "partial_min": 70.0})
    severity_on_conflict: str = "high"
    severity_on_partial: str = "medium"
    message_templates: Dict[str, str]
    clause: str = "Handbook clause: <to be mapped to the current handbook edition>"
    version: str = "1.0.0"


def load_consistency_rules(config_dir: Optional[Path] = None) -> List[ConsistencyRuleDefinition]:
    """Load cross-document consistency rules from YAML."""
    if config_dir is None:
        config_dir = Path(settings.CONFIG_DIR)

    rules_file = config_dir / "consistency" / "consistency_rules.yaml"
    if not rules_file.exists():
        candidate = Path(__file__).resolve().parent.parent.parent / "configs" / "consistency" / "consistency_rules.yaml"
        if candidate.exists():
            rules_file = candidate

    if not rules_file.exists():
        return []

    with open(rules_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    rule_entries = data.get("consistency_rules", [])
    results: List[ConsistencyRuleDefinition] = []
    for entry in rule_entries:
        results.append(ConsistencyRuleDefinition(**entry))
    return results


def _resolve_target(
    target_spec: str,
    application: Application,
    active_docs: Dict[str, Document],
) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str], Optional[str], bool, float]:
    """
    Resolve target string like 'land_document.owner_name' or 'application.institution_name'.
    Returns:
      (raw_val, norm_val, doc_id, doc_type, field_name, needs_verification, confidence)
    """
    parts = target_spec.split(".", 1)
    if len(parts) != 2:
        return None, None, None, None, None, False, 1.0

    target_type, field_name = parts[0].strip(), parts[1].strip()

    # Application-level field
    if target_type == "application":
        if field_name == "institution_name":
            inst_name = application.institution.name if application.institution else ""
            return inst_name, inst_name.lower(), None, "application", "institution_name", False, 1.0
        return None, None, None, "application", field_name, False, 1.0

    # Document-level field
    doc = active_docs.get(target_type)
    if not doc:
        return None, None, None, target_type, field_name, False, 0.0

    # Locate extracted field (supporting common aliases)
    field_obj = None
    alias_map = {
        "registered_date": "registration_date",
        "registration_date": "registered_date",
        "trustee_names": "trustees",
        "trustees": "trustee_names",
    }

    for ef in doc.extracted_fields:
        if ef.name == field_name or ef.name == alias_map.get(field_name):
            field_obj = ef
            break

    if not field_obj:
        return None, None, doc.id, target_type, field_name, False, 0.0

    return (
        field_obj.value_original,
        field_obj.value_normalized,
        doc.id,
        target_type,
        field_name,
        field_obj.needs_verification,
        field_obj.confidence,
    )


def run_consistency(
    db: Session,
    application_id: int,
    config_dir: Optional[Path] = None,
) -> List[ConsistencyComparison]:
    """
    Run all configured cross-document consistency checks for an application.
    Idempotent: clears previous ConsistencyResult entries for this application.
    """
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise ValueError(f"Application with ID {application_id} not found.")

    comp_info = check_completeness(db, application_id, config_dir=config_dir)
    active_docs: Dict[str, Document] = comp_info["active_documents"]

    rules = load_consistency_rules(config_dir=config_dir)
    norm_config = load_name_normalization_config(config_dir=config_dir)

    comparisons: List[ConsistencyComparison] = []

    for rule in rules:
        # 1. Resolve Left side
        l_raw, l_norm, l_doc_id, l_dtype, l_field, l_unverif, l_conf = _resolve_target(
            rule.left, application, active_docs
        )

        left_side = ConsistencyComparisonSide(
            doc_type=l_dtype,
            field=l_field,
            document_id=l_doc_id,
            original=l_raw,
            normalized=l_norm,
        )

        # Check for unresolvable left side
        if l_doc_id is None and l_dtype != "application":
            comp = ConsistencyComparison(
                rule_id=rule.id,
                description=rule.description,
                kind=rule.kind,
                relation=rule.relation,
                status="not_evaluable",
                severity="medium",
                score=0.0,
                message=f"Document '{l_dtype}' required for rule {rule.id} is missing from application.",
                clause=rule.clause,
                left=left_side,
                right=ConsistencyComparisonSide(),
                explanation="Source document missing on left side.",
                evidence={"reason": "missing_document", "side": "left", "target": rule.left},
            )
            comparisons.append(comp)
            continue

        if not l_raw and not l_norm:
            comp = ConsistencyComparison(
                rule_id=rule.id,
                description=rule.description,
                kind=rule.kind,
                relation=rule.relation,
                status="not_evaluable",
                severity="medium",
                score=0.0,
                message=f"Field '{l_field}' on document '{l_dtype}' has null or empty value.",
                clause=rule.clause,
                left=left_side,
                right=ConsistencyComparisonSide(),
                explanation="Null or empty field on left side.",
                evidence={"reason": "null_field", "side": "left", "target": rule.left},
            )
            comparisons.append(comp)
            continue

        if l_unverif:
            comp = ConsistencyComparison(
                rule_id=rule.id,
                description=rule.description,
                kind=rule.kind,
                relation=rule.relation,
                status="not_evaluable",
                severity="medium",
                score=0.0,
                message=f"Field '{l_field}' on '{l_dtype}' is unverified (confidence {l_conf:.2f}); cannot evaluate consistency safely.",
                clause=rule.clause,
                left=left_side,
                right=ConsistencyComparisonSide(),
                explanation="Left field flagged needs_verification.",
                evidence={"reason": "needs_verification", "side": "left", "confidence": l_conf},
            )
            comparisons.append(comp)
            continue

        # 2. Resolve Right targets (list or single)
        right_targets = [rule.right] if isinstance(rule.right, str) else rule.right

        candidate_outcomes = []

        for r_target in right_targets:
            r_raw, r_norm, r_doc_id, r_dtype, r_field, r_unverif, r_conf = _resolve_target(
                r_target, application, active_docs
            )

            right_side = ConsistencyComparisonSide(
                doc_type=r_dtype,
                field=r_field,
                document_id=r_doc_id,
                original=r_raw,
                normalized=r_norm,
            )

            # Check right side availability
            if r_doc_id is None and r_dtype != "application":
                candidate_outcomes.append({
                    "status": "not_evaluable",
                    "score": 0.0,
                    "right_side": right_side,
                    "explanation": f"Right document '{r_dtype}' missing",
                    "steps": [],
                })
                continue

            if not r_raw and not r_norm:
                candidate_outcomes.append({
                    "status": "not_evaluable",
                    "score": 0.0,
                    "right_side": right_side,
                    "explanation": f"Right field '{r_field}' null or empty",
                    "steps": [],
                })
                continue

            if r_unverif:
                candidate_outcomes.append({
                    "status": "not_evaluable",
                    "score": 0.0,
                    "right_side": right_side,
                    "explanation": f"Right field '{r_field}' unverified (confidence {r_conf:.2f})",
                    "steps": [],
                })
                continue

            # Candidate values could be a single string or JSON list (e.g. trustees)
            candidates_to_eval = []
            if (r_norm and r_norm.startswith("[")) or (r_raw and r_raw.startswith("[")):
                try:
                    parsed_list = json.loads(r_norm if r_norm.startswith("[") else r_raw)
                    if isinstance(parsed_list, list):
                        candidates_to_eval.extend([str(item) for item in parsed_list])
                except Exception:
                    candidates_to_eval.append(r_norm or r_raw)
            elif "," in (r_raw or "") and r_field in ("trustees", "trustee_names"):
                candidates_to_eval.extend([c.strip() for c in (r_raw or "").split(",") if c.strip()])
            else:
                candidates_to_eval.append(r_norm or r_raw)

            match_min = rule.thresholds.get("match_min", 85.0)
            partial_min = rule.thresholds.get("partial_min", 70.0)

            best_c_score = 0.0
            best_c_status = "conflict"
            best_c_val = candidates_to_eval[0] if candidates_to_eval else (r_norm or r_raw)
            best_steps = []

            for c_val in candidates_to_eval:
                if rule.kind == "name":
                    c_score, c_stat, c_steps = calculate_name_score(
                        name1=l_norm or l_raw,
                        name2=c_val,
                        match_min=match_min,
                        partial_min=partial_min,
                        config=norm_config,
                    )
                elif rule.kind == "id":
                    c_score, c_stat = compare_ids(l_norm or l_raw, c_val)
                    c_steps = [f"id_match: {c_score}"]
                elif rule.kind == "date_order":
                    c_score, c_stat, date_msg = compare_dates(l_norm or l_raw, c_val)
                    c_steps = [date_msg]
                elif rule.kind == "address":
                    c_score, c_stat, c_steps = compare_addresses(
                        l_norm or l_raw, c_val, match_min=match_min, partial_min=partial_min
                    )
                else:
                    c_score, c_stat, c_steps = 0.0, "conflict", ["unknown_kind"]

                # Rank: match > partial > conflict, then by numerical score
                stat_rank = {"match": 3, "partial": 2, "conflict": 1, "not_evaluable": 0}
                if (stat_rank[c_stat], c_score) > (stat_rank[best_c_status], best_c_score):
                    best_c_score = c_score
                    best_c_status = c_stat
                    best_c_val = c_val
                    best_steps = c_steps

            candidate_outcomes.append({
                "status": best_c_status,
                "score": best_c_score,
                "right_side": right_side,
                "best_val": best_c_val,
                "explanation": f"Compared with '{best_c_val}'",
                "steps": best_steps,
            })

        # Select overall best outcome across all right candidates
        stat_rank = {"match": 3, "partial": 2, "conflict": 1, "not_evaluable": 0}
        candidate_outcomes.sort(key=lambda o: (stat_rank.get(o["status"], 0), o["score"]), reverse=True)

        chosen = candidate_outcomes[0]
        final_status = chosen["status"]
        final_score = chosen["score"]
        final_right = chosen["right_side"]
        final_steps = chosen["steps"]

        # Determine severity
        if final_status == "conflict":
            severity = rule.severity_on_conflict
        elif final_status == "partial":
            severity = rule.severity_on_partial
        elif final_status == "match":
            severity = "low"
        else:
            severity = "medium"

        # Format message template
        template = rule.message_templates.get(final_status, "Comparison complete.")
        try:
            rendered_msg = template.format(
                left_value=l_raw or l_norm or "N/A",
                right_value=final_right.original or final_right.normalized or "N/A",
                score=final_score,
            )
        except Exception:
            rendered_msg = template

        explanation = chosen.get("explanation", "")
        evidence = {
            "rule_id": rule.id,
            "left": left_side.model_dump(),
            "right": final_right.model_dump(),
            "score": final_score,
            "thresholds": rule.thresholds,
            "matching_steps": final_steps,
        }

        comparison = ConsistencyComparison(
            rule_id=rule.id,
            description=rule.description,
            kind=rule.kind,
            relation=rule.relation,
            status=final_status,
            severity=severity,
            score=final_score,
            message=rendered_msg,
            clause=rule.clause,
            left=left_side,
            right=final_right,
            explanation=explanation,
            evidence=evidence,
        )
        comparisons.append(comparison)

    # 3. Idempotently persist ConsistencyResult rows in database
    db.query(ConsistencyResult).filter(ConsistencyResult.application_id == application_id).delete()

    for comp in comparisons:
        cr = ConsistencyResult(
            application_id=application_id,
            rule_id=comp.rule_id,
            field=f"{comp.left.field}->{comp.right.field}",
            doc_a_id=comp.left.document_id,
            doc_b_id=comp.right.document_id,
            value_a=comp.left.original or comp.left.normalized,
            value_b=comp.right.original or comp.right.normalized,
            score=comp.score,
            outcome=comp.status,
            status=comp.status,
            severity=comp.severity,
            relation=comp.relation,
            message=comp.message,
            clause=comp.clause,
            evidence=comp.evidence,
        )
        db.add(cr)

    db.commit()

    # 4. Audit Log
    summary_counts = {
        "match": sum(1 for c in comparisons if c.status == "match"),
        "partial": sum(1 for c in comparisons if c.status == "partial"),
        "conflict": sum(1 for c in comparisons if c.status == "conflict"),
        "not_evaluable": sum(1 for c in comparisons if c.status == "not_evaluable"),
        "total": len(comparisons),
    }

    log_action(
        db=db,
        actor="system",
        action="run_consistency",
        entity=f"application:{application_id}",
        details=summary_counts,
    )

    return comparisons
