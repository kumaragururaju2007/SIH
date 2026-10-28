import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Application,
    Document,
    Institution,
    InstitutionHistory,
    RuleResult,
    ConsistencyResult,
    AuthResult,
)

logger = logging.getLogger(__name__)


def load_risk_config(config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Load risk scoring weights and bands from YAML."""
    if config_dir is None:
        config_dir = Path(settings.CONFIG_DIR)

    risk_file = config_dir / "risk" / "risk_config.yaml"
    if not risk_file.exists():
        candidate = Path(__file__).resolve().parent.parent.parent / "configs" / "risk" / "risk_config.yaml"
        if candidate.exists():
            risk_file = candidate

    if not risk_file.exists():
        return {
            "disclaimer": "Illustrative score. Supports the officer's decision; does not replace it.",
            "weights": {
                "tampering": 0.28,
                "duplicate_reuse": 0.22,
                "failed_rules": 0.15,
                "consistency_conflicts": 0.15,
                "missing_documents": 0.10,
                "unverified_ratio": 0.05,
                "history_factor": 0.05,
            },
            "history": {
                "neutral_score": 0.15,
                "rejection_weight": 0.40,
                "flag_weight": 0.05,
                "deficiency_weight": 0.02,
                "recency_decay_per_year": 0.85,
            },
        }

    with open(risk_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def compute_history_factor(
    db: Session,
    institution_id: int,
    history_cfg: Dict[str, Any],
) -> Tuple[float, str]:
    """Calculate institutional history risk factor (0.0 to 1.0) with recency weighting.
    
    If no history records exist, returns the configured neutral baseline score (not zero).
    """
    histories = (
        db.query(InstitutionHistory)
        .filter(InstitutionHistory.institution_id == institution_id)
        .order_by(InstitutionHistory.year.desc())
        .all()
    )

    if not histories:
        neutral = float(history_cfg.get("neutral_score", 0.15))
        return neutral, "New institution without historical AICTE regulatory record (neutral baseline)"

    rej_wt = float(history_cfg.get("rejection_weight", 0.40))
    flag_wt = float(history_cfg.get("flag_weight", 0.05))
    def_wt = float(history_cfg.get("deficiency_weight", 0.02))
    decay_rate = float(history_cfg.get("recency_decay_per_year", 0.85))

    current_year = 2026
    weighted_scores: List[float] = []
    total_flags = 0
    total_rejections = 0
    total_deficiencies = 0

    for h in histories:
        years_ago = max(0, current_year - h.year)
        decay = decay_rate ** years_ago

        is_rejection = 1.0 if "reject" in h.outcome.lower() else 0.0
        if is_rejection:
            total_rejections += 1
        total_flags += h.flags_count
        total_deficiencies += h.deficiency_count

        rec_val = (is_rejection * rej_wt) + (h.flags_count * flag_wt) + (h.deficiency_count * def_wt)
        weighted_scores.append(rec_val * decay)

    raw_sum = sum(weighted_scores)
    final_score = min(1.0, max(0.0, raw_sum))

    desc_parts = []
    if total_rejections:
        desc_parts.append(f"{total_rejections} prior rejection(s)")
    if total_flags:
        desc_parts.append(f"{total_flags} regulatory flag(s)")
    if total_deficiencies:
        desc_parts.append(f"{total_deficiencies} deficiency finding(s)")

    summary_str = f"Historical performance: {', '.join(desc_parts)}" if desc_parts else "Prior compliance history clean"
    return final_score, summary_str


def calculate_application_risk(
    db: Session,
    application_id: int,
    completeness: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Calculate the explainable risk score (0-100), band, and contributing factor breakdown."""
    cfg = config or load_risk_config()
    weights = cfg.get("weights", {})
    disclaimer = cfg.get(
        "disclaimer",
        "Illustrative score. Supports the officer's decision; does not replace it.",
    )

    application = db.get(Application, application_id)
    if not application:
        raise ValueError(f"Application with ID {application_id} not found.")

    doc_ids = [d.id for d in application.documents]

    # 1. Tampering Factor
    auth_rows = db.query(AuthResult).filter(AuthResult.document_id.in_(doc_ids)).all() if doc_ids else []
    tamp_rows = [r for r in auth_rows if r.check_type == "tampering"]
    max_tamp_score = 0.0
    tampering_doc_name = "None"
    for r in tamp_rows:
        score = r.probability or 0.0
        if score > max_tamp_score:
            max_tamp_score = score
            doc = db.get(Document, r.document_id)
            if doc:
                tampering_doc_name = doc.doc_type or f"Document {doc.id}"

    tamp_weight = float(weights.get("tampering", 0.28))
    tamp_points = tamp_weight * max_tamp_score * 100.0

    # 2. Duplicate / Reuse Factor
    dup_rows = [r for r in auth_rows if r.check_type == "duplicate" and r.evidence and r.evidence.get("duplicate_found")]
    has_duplicate = len(dup_rows) > 0
    dup_weight = float(weights.get("duplicate_reuse", 0.22))
    dup_points = dup_weight * (1.0 if has_duplicate else 0.0) * 100.0

    # 3. Failed Rules Factor
    rule_rows = db.query(RuleResult).filter(RuleResult.application_id == application.id).all()
    failed_rules = [r for r in rule_rows if not r.passed or r.status == "failed"]
    
    sev_mults = cfg.get("severity_multipliers", {"high": 1.0, "medium": 0.6, "low": 0.3})
    weighted_failed = sum(sev_mults.get(r.severity, 0.5) for r in failed_rules)
    normalized_failed = min(1.0, weighted_failed / 2.5)
    rules_weight = float(weights.get("failed_rules", 0.15))
    failed_rules_points = rules_weight * normalized_failed * 100.0

    # 4. Consistency Conflicts Factor
    consistency_rows = db.query(ConsistencyResult).filter(ConsistencyResult.application_id == application.id).all()
    conflicts_count = sum(1 for c in consistency_rows if c.status == "conflict")
    partials_count = sum(1 for c in consistency_rows if c.status == "partial")

    c_mults = cfg.get("consistency_multipliers", {"conflict": 1.0, "partial": 0.4})
    weighted_consistency = (conflicts_count * c_mults.get("conflict", 1.0)) + (partials_count * c_mults.get("partial", 0.4))
    normalized_consistency = min(1.0, weighted_consistency / 2.0)
    consistency_weight = float(weights.get("consistency_conflicts", 0.15))
    consistency_points = consistency_weight * normalized_consistency * 100.0

    # 5. Missing Required Documents Factor
    missing_docs: List[str] = []
    if completeness:
        if isinstance(completeness, dict):
            missing_docs = completeness.get("missing_documents") or completeness.get("missing", [])
        elif hasattr(completeness, "missing"):
            missing_docs = list(completeness.missing)
        elif hasattr(completeness, "missing_documents"):
            missing_docs = list(completeness.missing_documents)
    else:
        for r in rule_rows:
            if r.rule_id.startswith("REQ-") and not r.passed:
                missing_docs.append(r.rule_id.replace("REQ-", ""))

    missing_normalized = min(1.0, len(missing_docs) / 2.0)
    missing_weight = float(weights.get("missing_documents", 0.10))
    missing_points = missing_weight * missing_normalized * 100.0

    # 6. Unverified Ratio Factor
    not_eval_rules = sum(1 for r in rule_rows if r.status == "not_evaluable")
    not_eval_consistency = sum(1 for c in consistency_rows if c.status == "not_evaluable")
    total_evaluable = max(1, len(rule_rows) + len(consistency_rows))
    unverified_ratio = min(1.0, (not_eval_rules + not_eval_consistency) / total_evaluable)
    unverified_weight = float(weights.get("unverified_ratio", 0.05))
    unverified_points = unverified_weight * unverified_ratio * 100.0

    # 7. Institution History Factor
    history_cfg = cfg.get("history", {})
    history_score, history_desc = compute_history_factor(db, application.institution_id, history_cfg)
    history_weight = float(weights.get("history_factor", 0.05))
    history_points = history_weight * history_score * 100.0

    # Total Risk Calculation
    all_factors: List[Dict[str, Any]] = [
        {
            "factor": "Image Forensics & Tampering",
            "key": "tampering",
            "points": round(tamp_points, 1),
            "max_possible": round(tamp_weight * 100.0, 1),
            "description": f"Highest tampering probability signal is {round(max_tamp_score * 100.0, 1)}% ({tampering_doc_name})",
        },
        {
            "factor": "Duplicate Document / ID Reuse",
            "key": "duplicate_reuse",
            "points": round(dup_points, 1),
            "max_possible": round(dup_weight * 100.0, 1),
            "description": (
                "Identical file hash or normalized registration ID detected across unlinked applications"
                if has_duplicate
                else "No duplicate files or reused certificates detected"
            ),
        },
        {
            "factor": "Regulatory Rule Non-Compliance",
            "key": "failed_rules",
            "points": round(failed_rules_points, 1),
            "max_possible": round(rules_weight * 100.0, 1),
            "description": f"{len(failed_rules)} non-compliant approval norm(s) identified",
        },
        {
            "factor": "Cross-Document Inconsistency",
            "key": "consistency_conflicts",
            "points": round(consistency_points, 1),
            "max_possible": round(consistency_weight * 100.0, 1),
            "description": f"{conflicts_count} direct conflict(s) and {partials_count} partial discrepancy token(s)",
        },
        {
            "factor": "Missing Mandatory Documentation",
            "key": "missing_documents",
            "points": round(missing_points, 1),
            "max_possible": round(missing_weight * 100.0, 1),
            "description": f"Missing {len(missing_docs)} required document(s): {', '.join(missing_docs) if missing_docs else 'None'}",
        },
        {
            "factor": "Unverified Verification Ratio",
            "key": "unverified_ratio",
            "points": round(unverified_points, 1),
            "max_possible": round(unverified_weight * 100.0, 1),
            "description": f"{round(unverified_ratio * 100.0, 1)}% of criteria could not be verified automatically",
        },
        {
            "factor": "Institutional Regulatory Track Record",
            "key": "history_factor",
            "points": round(history_points, 1),
            "max_possible": round(history_weight * 100.0, 1),
            "description": history_desc,
        },
    ]

    total_score = sum(f["points"] for f in all_factors)
    clamped_score = round(min(100.0, max(0.0, total_score)), 1)

    # Determine risk band
    bands_cfg = cfg.get("bands", {})
    if clamped_score < bands_cfg.get("low", {}).get("max", 35.0):
        band = "low"
    elif clamped_score < bands_cfg.get("medium", {}).get("max", 65.0):
        band = "medium"
    else:
        band = "high"

    # Top 5 contributing factors
    sorted_factors = sorted(all_factors, key=lambda f: f["points"], reverse=True)
    top_5 = sorted_factors[:5]

    # Save to Application
    application.risk_score = clamped_score
    application.risk_band = band
    application.risk_factors = {
        "score": clamped_score,
        "band": band,
        "top_factors": top_5,
        "all_factors": all_factors,
        "disclaimer": disclaimer,
    }
    db.commit()

    return {
        "application_id": application.id,
        "risk_score": clamped_score,
        "risk_band": band,
        "disclaimer": disclaimer,
        "top_factors": top_5,
        "all_factors": all_factors,
    }
