import html
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Application,
    Document,
    RuleResult,
    ConsistencyResult,
    AuthResult,
    DeficiencyReport,
    AuditLog,
)
from app.services.completeness import check_completeness

logger = logging.getLogger(__name__)

FORBIDDEN_PHRASES = [
    "fabricate",
    "forge",
    "alter",
    "backdate",
    "change the date",
    "edit the document",
]


def load_deficiency_templates(lang: str = "en", config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Load deficiency wording templates from YAML config."""
    if config_dir is None:
        config_dir = Path(settings.CONFIG_DIR)

    fname = f"templates_{lang}.yaml"
    tmpl_file = config_dir / "deficiency" / fname
    if not tmpl_file.exists():
        candidate = Path(__file__).resolve().parent.parent.parent / "configs" / "deficiency" / fname
        if candidate.exists():
            tmpl_file = candidate

    if not tmpl_file.exists():
        logger.warning(f"Template file {fname} not found; falling back to English defaults")
        return {}

    with open(tmpl_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def scan_for_forbidden_phrases(text: str) -> List[str]:
    """Safeguard: check that text contains no prohibited phrases suggesting alteration or backdating."""
    lower = text.lower()
    return [phrase for phrase in FORBIDDEN_PHRASES if phrase in lower]


def build_deficiency_items(
    db: Session,
    application_id: int,
    lang: str = "en",
) -> List[Dict[str, Any]]:
    """
    Build structured deficiency items from:
    - Missing mandatory documents
    - Failed deterministic rules
    - Cross-document consistency conflicts and partial matches
    - Government registry mismatches
    - Duplicate document or identifier reuse
    - Possible tampering signals (with neutral, non-accusing wording)
    - Fixable verification items (unreadable scan, missing QR)
    """
    templates = load_deficiency_templates(lang)
    app = db.get(Application, application_id)
    if not app:
        raise ValueError(f"Application {application_id} not found")

    items: List[Dict[str, Any]] = []

    # 1. Missing Required Documents
    comp = check_completeness(db, application_id)
    missing_docs = comp.get("missing", [])
    tmpl_missing = templates.get("MISSING_DOCUMENT", {})

    for doc_type in missing_docs:
        doc_display = doc_type.replace("_", " ").title()
        item_id = f"DEF-MISSING-{doc_type}"
        title = tmpl_missing.get("title", "Missing Mandatory Document: {doc_name}").format(
            doc_name=doc_display
        )
        what_failed = tmpl_missing.get("what_failed", "Mandatory document '{doc_name}' was not submitted.").format(
            doc_name=doc_display
        )
        why = tmpl_missing.get("why", "Required for application type '{application_type}'.").format(
            application_type=app.application_type.replace("_", " ").title()
        )
        what_to_resubmit = tmpl_missing.get(
            "what_to_resubmit",
            "Please obtain and upload a genuine, valid copy from the issuing authority.",
        ).format(doc_name=doc_display)
        clause = tmpl_missing.get(
            "clause",
            "Handbook clause: <to be mapped to the current handbook edition - Chapter 1 Mandatory Documents>",
        )

        items.append({
            "item_id": item_id,
            "category": "missing_document",
            "title": title,
            "what_failed": what_failed,
            "why": why,
            "clause": clause,
            "what_to_resubmit": what_to_resubmit,
            "severity": "high",
            "document_id": None,
            "doc_type": doc_type,
            "evidence": {"doc_type": doc_type},
        })

    # 2. Failed Rules
    rule_results = db.query(RuleResult).filter(RuleResult.application_id == application_id).all()
    failed_rules = [r for r in rule_results if not r.passed or r.status == "failed"]

    for r in failed_rules:
        item_id = f"DEF-RULE-{r.rule_id}"
        doc = db.get(Document, r.document_id) if r.document_id else None
        doc_type = doc.doc_type if doc else "document"

        # Template selection
        if "FIRE" in r.rule_id.upper():
            tmpl = templates.get("FIRE_EXPIRY", templates.get("DEFAULT_RULE", {}))
            ev = r.evidence or {}
            exp_val = ev.get("valid_to") or ev.get("extracted_value") or "Expired Date"
            title = tmpl.get("title", "Fire Safety Certificate Expired")
            what_failed = tmpl.get("what_failed", "Fire Safety Certificate expired.")
            why = tmpl.get("why", "Expiration date {expiry_date}").format(expiry_date=exp_val)
            what_to_resubmit = tmpl.get("what_to_resubmit", "Please submit a current, valid Fire Safety Certificate.")
            clause = r.clause or tmpl.get("clause", "Handbook clause: <to be mapped to the current handbook edition>")
        elif "LAND" in r.rule_id.upper() or "AREA" in r.rule_id.upper():
            tmpl = templates.get("LAND_AREA", templates.get("DEFAULT_RULE", {}))
            ev = r.evidence or {}
            area_val = ev.get("land_area_sqm") or ev.get("certified_area") or ev.get("extracted_value") or "Deficient"
            min_val = ev.get("min_required") or "10,000"
            title = tmpl.get("title", "Land Area Deficit")
            what_failed = tmpl.get("what_failed", "Certified land area does not meet minimum requirement.")
            why = tmpl.get("why", "Certified {land_area} sqm vs required {min_area} sqm").format(
                land_area=area_val, min_area=min_val
            )
            what_to_resubmit = tmpl.get("what_to_resubmit", "Please submit an updated, genuine Land Document.")
            clause = r.clause or tmpl.get("clause", "Handbook clause: <to be mapped to the current handbook edition>")
        else:
            tmpl = templates.get("DEFAULT_RULE", {})
            title = tmpl.get("title", "Rule Non-Compliance: {rule_id}").format(rule_id=r.rule_id)
            what_failed = tmpl.get("what_failed", "Evaluation failed for {rule_id}").format(rule_id=r.rule_id)
            why = r.message
            what_to_resubmit = tmpl.get("what_to_resubmit", "Please provide a genuine official document from the issuing authority.")
            clause = r.clause or tmpl.get("clause", "Handbook clause: <to be mapped to the current handbook edition>")

        items.append({
            "item_id": item_id,
            "category": "rule_failure",
            "title": title,
            "what_failed": what_failed,
            "why": why,
            "clause": clause,
            "what_to_resubmit": what_to_resubmit,
            "severity": r.severity or "high",
            "document_id": r.document_id,
            "doc_type": doc_type,
            "evidence": r.evidence or {"message": r.message},
        })

    # 3. Cross-Document Consistency (Conflicts and Partials)
    consistency_results = db.query(ConsistencyResult).filter(ConsistencyResult.application_id == application_id).all()
    inconsistent_comparisons = [c for c in consistency_results if c.status in ("conflict", "partial")]

    for c in inconsistent_comparisons:
        item_id = f"DEF-CONSISTENCY-{c.rule_id}"
        val_a = c.value_a or "Value A"
        val_b = c.value_b or "Value B"
        doc_a = db.get(Document, c.doc_a_id) if c.doc_a_id else None
        doc_b = db.get(Document, c.doc_b_id) if c.doc_b_id else None
        doc_a_name = doc_a.doc_type.replace("_", " ").title() if doc_a and doc_a.doc_type else "Document A"
        doc_b_name = doc_b.doc_type.replace("_", " ").title() if doc_b and doc_b.doc_type else "Document B"

        if "OWNER" in c.rule_id.upper():
            tmpl = templates.get("CONSISTENCY_OWNER_TRUST", templates.get("DEFAULT_CONSISTENCY", {}))
            title = tmpl.get("title", "Land Ownership and Trust Name Discrepancy")
            what_failed = tmpl.get("what_failed", "Owner name in land document does not match Trust name.")
            why = tmpl.get("why", "Land lists '{owner_name}', while trust lists '{trust_name}'").format(
                owner_name=val_a, trust_name=val_b
            )
            what_to_resubmit = tmpl.get("what_to_resubmit", "Please submit genuine registered title deed confirming ownership under applicant Trust.")
            clause = c.clause or tmpl.get("clause", "Handbook clause: <to be mapped to current handbook edition - Title Continuity Section 3.2>")
        elif "ADDRESS" in c.rule_id.upper():
            tmpl = templates.get("CONSISTENCY_ADDRESS", templates.get("DEFAULT_CONSISTENCY", {}))
            title = tmpl.get("title", "Premises Address Discrepancy")
            what_failed = tmpl.get("what_failed", "Site address varies across documents.")
            why = tmpl.get("why", "{address_a} in {doc_a} differs from {address_b} in {doc_b}").format(
                address_a=val_a, doc_a=doc_a_name, address_b=val_b, doc_b=doc_b_name
            )
            what_to_resubmit = tmpl.get("what_to_resubmit", "Please submit genuine address rectification records from revenue authority.")
            clause = c.clause or tmpl.get("clause", "Handbook clause: <to be mapped to current handbook edition - Campus Identification Section 2.1>")
        else:
            tmpl = templates.get("DEFAULT_CONSISTENCY", {})
            title = tmpl.get("title", "Cross-Document Discrepancy on {field}").format(field=c.field)
            what_failed = tmpl.get("what_failed", "Value inconsistency detected for {field}").format(field=c.field)
            why = tmpl.get("why", "{doc_a} shows '{value_a}', while {doc_b} shows '{value_b}'").format(
                doc_a=doc_a_name, value_a=val_a, doc_b=doc_b_name, value_b=val_b
            )
            what_to_resubmit = tmpl.get("what_to_resubmit", "Please verify records and provide matching genuine documents.")
            clause = c.clause or tmpl.get("clause", "Handbook clause: <to be mapped to current handbook edition>")

        items.append({
            "item_id": item_id,
            "category": "consistency",
            "title": title,
            "what_failed": what_failed,
            "why": why,
            "clause": clause,
            "what_to_resubmit": what_to_resubmit,
            "severity": c.severity or ("high" if c.status == "conflict" else "medium"),
            "document_id": c.doc_a_id,
            "doc_type": doc_a.doc_type if doc_a else None,
            "evidence": {
                "rule_id": c.rule_id,
                "value_a": val_a,
                "value_b": val_b,
                "status": c.status,
            },
        })

    # 4. Authentication Signals (Registry Mismatch, Duplicate, Tampering, Unreadable, Missing QR)
    doc_ids = [d.id for d in app.documents]
    auth_rows = db.query(AuthResult).filter(AuthResult.document_id.in_(doc_ids)).all() if doc_ids else []

    for ar in auth_rows:
        doc = db.get(Document, ar.document_id)
        doc_type_str = doc.doc_type.replace("_", " ").title() if doc and doc.doc_type else "Document"

        if ar.check_type == "registry" and ar.result == "mismatch":
            tmpl = templates.get("REGISTRY_MISMATCH", {})
            diffs = ar.evidence.get("differing_fields", []) if ar.evidence else []
            diff_str = ", ".join(f"{d.get('field')} ({d.get('extracted_value')} vs registry {d.get('registry_value')})" for d in diffs)
            diff_str = diff_str or "Mismatch between extracted values and registry database record"
            items.append({
                "item_id": f"DEF-AUTH-REG-{ar.document_id}",
                "category": "registry",
                "title": tmpl.get("title", "Government Registry Verification Mismatch: {doc_type}").format(doc_type=doc_type_str),
                "what_failed": tmpl.get("what_failed", "Extracted document records do not correspond with government database records."),
                "why": tmpl.get("why", "Registry comparison found discrepancy: {diff_fields}").format(diff_fields=diff_str),
                "clause": tmpl.get("clause", "Handbook clause: <to be mapped to the current handbook edition - Registry Verification Section 4.1>"),
                "what_to_resubmit": tmpl.get("what_to_resubmit", "Please provide a fresh, genuine certificate with verifiable registration numbers."),
                "severity": "high",
                "document_id": ar.document_id,
                "doc_type": doc.doc_type if doc else None,
                "evidence": ar.evidence,
            })

        elif ar.check_type == "duplicate" and ar.evidence and ar.evidence.get("duplicate_found"):
            tmpl = templates.get("DUPLICATE_REUSE", {})
            cert_id = ar.evidence.get("extracted_id") or "Recorded File Fingerprint"
            items.append({
                "item_id": f"DEF-AUTH-DUP-{ar.document_id}",
                "category": "duplicate",
                "title": tmpl.get("title", "Duplicate Document or Identifier Reuse Detected"),
                "what_failed": tmpl.get("what_failed", "Document content or certificate number matches a filing from another application."),
                "why": tmpl.get("why", "The document fingerprint or registration number '{cert_id}' was previously recorded.").format(cert_id=cert_id),
                "clause": tmpl.get("clause", "Handbook clause: <to be mapped to the current handbook edition - Anti-Duplicate Provisions Section 5.3>"),
                "what_to_resubmit": tmpl.get("what_to_resubmit", "Please submit an original, genuine document uniquely issued for this institution."),
                "severity": "high",
                "document_id": ar.document_id,
                "doc_type": doc.doc_type if doc else None,
                "evidence": ar.evidence,
            })

        elif ar.check_type == "tampering" and ar.result in ("suspicious", "high_suspicion"):
            # CRITICAL RULE: Use neutral wording, never accusing language
            tmpl = templates.get("TAMPERING_SIGNAL", {})
            score_pct = f"{round((ar.probability or 0.0) * 100, 1)}%"
            items.append({
                "item_id": f"DEF-AUTH-TAMP-{ar.document_id}",
                "category": "authenticity",
                "title": tmpl.get("title", "Document Verification Inconsistency: {doc_type}").format(doc_type=doc_type_str),
                "what_failed": "The document could not be verified and shows inconsistencies; please provide a genuine copy from the issuing authority.",
                "why": f"Image forensics and structural checks detected anomalies (signal: {score_pct}). Note: Forensic signals are decision support aids, not absolute proof.",
                "clause": tmpl.get("clause", "Handbook clause: <to be mapped to the current handbook edition - Authenticity Standards Section 6.2>"),
                "what_to_resubmit": "Please obtain and provide a fresh, genuine replacement document directly from the issuing authority.",
                "severity": "high",
                "document_id": ar.document_id,
                "doc_type": doc.doc_type if doc else None,
                "evidence": ar.evidence,
            })

        elif ar.check_type == "tampering" and ar.result == "low_quality_scan":
            tmpl = templates.get("UNREADABLE_SCAN", {})
            conf_val = round((doc.ocr_confidence or 0.5) * 100, 1) if doc else 50.0
            items.append({
                "item_id": f"DEF-VERIFY-SCAN-{ar.document_id}",
                "category": "verification",
                "title": tmpl.get("title", "Degraded Scan Quality: {doc_type}").format(doc_type=doc_type_str),
                "what_failed": tmpl.get("what_failed", "Document image is degraded, blurry, or low-resolution."),
                "why": tmpl.get("why", "Extraction confidence ({ocr_conf}%) is below readability norms.").format(ocr_conf=conf_val),
                "clause": tmpl.get("clause", "Handbook clause: <to be mapped to the current handbook edition - Document Scanning Guidelines Section 7.1>"),
                "what_to_resubmit": tmpl.get("what_to_resubmit", "Please upload a high-resolution, clear, and unblurred scan (minimum 300 DPI) of the original document."),
                "severity": "medium",
                "document_id": ar.document_id,
                "doc_type": doc.doc_type if doc else None,
                "evidence": ar.evidence,
            })

        elif ar.check_type == "qr" and ar.result in ("absent", "unreadable"):
            tmpl = templates.get("MISSING_QR", {})
            items.append({
                "item_id": f"DEF-VERIFY-QR-{ar.document_id}",
                "category": "verification",
                "title": tmpl.get("title", "QR Security Code Missing or Unreadable: {doc_type}").format(doc_type=doc_type_str),
                "what_failed": tmpl.get("what_failed", "Official security QR code could not be detected or scanned."),
                "why": tmpl.get("why", "Security QR code is absent or unreadable on {doc_type}.").format(doc_type=doc_type_str),
                "clause": tmpl.get("clause", "Handbook clause: <to be mapped to the current handbook edition - Digital Security Section 7.2>"),
                "what_to_resubmit": tmpl.get("what_to_resubmit", "Please upload a clear scan displaying the official digital verification QR code."),
                "severity": "medium",
                "document_id": ar.document_id,
                "doc_type": doc.doc_type if doc else None,
                "evidence": ar.evidence,
            })

    # Safeguard check across all constructed items
    for item in items:
        for fld in ("title", "what_failed", "why", "what_to_resubmit"):
            forbidden = scan_for_forbidden_phrases(item.get(fld, ""))
            if forbidden:
                raise ValueError(
                    f"Deficiency generation safeguard triggered: forbidden phrase(s) {forbidden} found in item {item['item_id']} ({fld})."
                )

    return items


def render_report_text(
    app: Application,
    items: List[Dict[str, Any]],
    summary_line: str,
    lang: str = "en",
) -> str:
    """Render deficiency report in clear official plain text format."""
    inst_name = app.institution.name if app.institution else "Applicant Institution"
    lines = [
        "=" * 78,
        "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION (AICTE)",
        "OFFICIAL DEFICIENCY AND SCRUTINY REPORT",
        "SPECIMEN - SYNTHETIC DATA (ILLUSTRATIVE PROTOTYPE NORMS)",
        "=" * 78,
        f"Application ID   : #{app.id}",
        f"Institution Name : {inst_name}",
        f"Application Type : {app.application_type.replace('_', ' ').title()}",
        f"Date of Report   : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"Status Summary   : {summary_line}",
        "-" * 78,
        "LEGAL NOTICE & STATUTORY GUIDANCE:",
        "Scores and signals are probabilistic decision aids. The verifying officer",
        "always decides. To rectify deficiencies, submit genuine, valid replacement",
        "documents obtained directly from the appropriate issuing authority.",
        "-" * 78,
        "",
    ]

    if not items:
        lines.append("No regulatory deficiencies identified. Application satisfies all verification criteria.")
        lines.append("")
        return "\n".join(lines)

    for idx, it in enumerate(items, 1):
        lines.extend([
            f"Item {idx}: [{it['severity'].upper()}] {it['title']}",
            f"  Item ID          : {it['item_id']}",
            f"  What Failed      : {it['what_failed']}",
            f"  Specific Reason  : {it['why']}",
            f"  Handbook Clause  : {it['clause']}",
            f"  Action Required  : {it['what_to_resubmit']}",
            "",
        ])

    lines.append("=" * 78)
    lines.append("End of Deficiency Report")
    return "\n".join(lines)


def render_report_html(
    app: Application,
    items: List[Dict[str, Any]],
    summary_line: str,
    lang: str = "en",
) -> str:
    """Render deficiency report in modern, responsive HTML format."""
    inst_name = html.escape(app.institution.name if app.institution else "Applicant Institution")
    app_type = html.escape(app.application_type.replace("_", " ").title())
    summary_esc = html.escape(summary_line)

    badge_colors = {
        "high": "background: #fee2e2; color: #991b1b; border: 1px solid #f87171;",
        "medium": "background: #fef3c7; color: #92400e; border: 1px solid #fcd34d;",
        "low": "background: #dbeafe; color: #1e40af; border: 1px solid #93c5fd;",
    }

    items_html = ""
    for idx, it in enumerate(items, 1):
        badge_style = badge_colors.get(it["severity"], badge_colors["medium"])
        items_html += f"""
        <div style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 16px; background: #ffffff;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: 700; font-size: 1.1rem; color: #111827;">{idx}. {html.escape(it['title'])}</span>
                <span style="padding: 2px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; {badge_style}">
                    {html.escape(it['severity'])}
                </span>
            </div>
            <p style="margin: 4px 0; color: #374151;"><strong>What Failed:</strong> {html.escape(it['what_failed'])}</p>
            <p style="margin: 4px 0; color: #374151;"><strong>Reason:</strong> {html.escape(it['why'])}</p>
            <p style="margin: 4px 0; color: #6b7280; font-size: 0.9rem;"><strong>Regulatory Clause:</strong> <em>{html.escape(it['clause'])}</em></p>
            <div style="margin-top: 8px; padding: 10px; background: #f0fdf4; border-left: 4px solid #16a34a; border-radius: 4px;">
                <strong style="color: #15803d;">Action Required:</strong>
                <span style="color: #166534;">{html.escape(it['what_to_resubmit'])}</span>
            </div>
        </div>
        """

    if not items:
        items_html = """
        <div style="padding: 20px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; color: #166534; font-weight: 500;">
            No regulatory deficiencies identified. Application satisfies all verification criteria.
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="utf-8">
    <title>AICTE Deficiency Report - #{app.id}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.5; color: #1f2937; margin: 0; padding: 24px; background: #f9fafb; }}
        .container {{ max-width: 800px; margin: 0 auto; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
        .header {{ border-bottom: 2px solid #2563eb; padding-bottom: 16px; margin-bottom: 24px; }}
        .disclaimer {{ background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 12px 16px; margin-bottom: 24px; font-size: 0.85rem; color: #1e40af; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0; font-size: 1.5rem; color: #1e3a8a;">All India Council for Technical Education</h1>
            <h2 style="margin: 4px 0 0 0; font-size: 1.1rem; color: #4b5563; font-weight: 500;">Official Deficiency and Scrutiny Report</h2>
            <p style="margin: 4px 0 0 0; font-size: 0.8rem; color: #9ca3af;">SPECIMEN - SYNTHETIC DATA (ILLUSTRATIVE PROTOTYPE)</p>
        </div>

        <div class="disclaimer">
            <strong>Decision Support Notice:</strong> Risk scores and forensic signals are probabilistic decision aids.
            The verifying officer always decides. Genuine replacement documents from the issuing authority are required to rectify deficiencies.
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 24px; font-size: 0.95rem;">
            <div><strong>Application ID:</strong> #{app.id}</div>
            <div><strong>Institution:</strong> {inst_name}</div>
            <div><strong>Application Type:</strong> {app_type}</div>
            <div><strong>Summary:</strong> <span style="font-weight: 600; color: #dc2626;">{summary_esc}</span></div>
        </div>

        <h3 style="margin-bottom: 16px; color: #111827; font-size: 1.2rem;">Items Requiring Scrutiny or Resubmission</h3>
        {items_html}

        <footer style="margin-top: 32px; padding-top: 16px; border-top: 1px solid #e5e7eb; font-size: 0.8rem; color: #9ca3af; text-align: center;">
            Generated by AICTE Document Validation System &bull; Synthetic Demonstration Environment
        </footer>
    </div>
</body>
</html>"""
    return html_content


def generate_deficiency_report(
    db: Session,
    application_id: int,
    lang: str = "en",
    llm_polish: bool = False,
) -> DeficiencyReport:
    """
    Generate or update a DeficiencyReport record for an application.
    Facts and values come from stored results; optional LLM polish keeps facts unchanged.
    """
    app = db.get(Application, application_id)
    if not app:
        raise ValueError(f"Application {application_id} not found")

    items = build_deficiency_items(db, application_id, lang=lang)

    # Count severities
    high_count = sum(1 for it in items if it["severity"] == "high")
    med_count = sum(1 for it in items if it["severity"] == "medium")
    low_count = sum(1 for it in items if it["severity"] == "low")
    total_count = len(items)

    if total_count == 0:
        summary_line = "No deficiencies found. Application is compliant."
    elif total_count == 1:
        summary_line = "1 item needs attention"
    else:
        summary_line = f"{total_count} items need attention"

    rendered_text = render_report_text(app, items, summary_line, lang=lang)
    rendered_html = render_report_html(app, items, summary_line, lang=lang)

    content = {
        "summary": summary_line,
        "total_items": total_count,
        "high_severity_count": high_count,
        "medium_severity_count": med_count,
        "low_severity_count": low_count,
        "items": items,
        "rendered_text": rendered_text,
        "rendered_html": rendered_html,
        "language": lang,
        "llm_polished": llm_polish and os.getenv("REPORT_LLM_POLISH", "false").lower() == "true",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Check if a report already exists for this application
    report = (
        db.query(DeficiencyReport)
        .filter(DeficiencyReport.application_id == application_id)
        .order_by(DeficiencyReport.created_at.desc())
        .first()
    )

    if report and report.status == "draft":
        report.content = content
    else:
        report = DeficiencyReport(
            application_id=application_id,
            status="draft",
            content=content,
        )
        db.add(report)

    db.commit()
    db.refresh(report)
    return report
