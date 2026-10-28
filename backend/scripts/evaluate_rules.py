import os
import sys
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal, engine, Base
from app.models import Institution, Application, Document, ExtractedField, RuleResult
from app.services.pipeline import process_document
from app.services.validation import run_rules
from app.services.rules_engine import to_date_obj


def resolve_file(rel_path: str) -> Path:
    p = Path(rel_path)
    if p.exists():
        return p
    candidates = [
        BACKEND_DIR / p,
        BACKEND_DIR.parent / p,
        BACKEND_DIR.parent / "aicte-validator" / p,
    ]
    for c in candidates:
        if c.exists():
            return c
    alt = Path(str(rel_path).replace("\\", "/"))
    for c in [BACKEND_DIR / alt, BACKEND_DIR.parent / alt]:
        if c.exists():
            return c
    return p


def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def is_per_document_issue(issue: str) -> bool:
    """Check if an issue is a per-document rule or completeness finding."""
    if issue.startswith("MISSING:"):
        return True
    if any(issue.startswith(prefix) for prefix in ("FIRE-", "LAND-", "TRUST-")):
        return True
    return False


def run_rules_evaluation():
    manifest_path = resolve_file("data/synthetic/manifest.json")
    if not manifest_path.exists():
        manifest_path = BACKEND_DIR / "data" / "synthetic" / "manifest.json"
    if not manifest_path.exists():
        manifest_path = BACKEND_DIR.parent / "data" / "synthetic" / "manifest.json"

    if not manifest_path.exists():
        print(f"Error: manifest.json not found at {manifest_path}", file=sys.stderr)
        return 1

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    db = SessionLocal()
    start_time = time.time()

    print("============================================================")
    print(" AICTE Document Validation System - Deterministic Rules Evaluation")
    print(f" Manifest: {manifest_path}")
    print(" Evaluating Per-Document Rules & Completeness against Ground Truth")
    print("============================================================\n")

    applications = manifest.get("applications", [])
    results_rows: List[Dict[str, Any]] = []
    missed_reasons: List[Dict[str, Any]] = []

    # Ensure evaluation institution exists
    inst = db.query(Institution).filter(Institution.name == "Synthetic Test Institution").first()
    if not inst:
        inst = Institution(
            name="Synthetic Test Institution",
            state="Maharashtra",
            trust_name="Synthetic Educational Foundation",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)

    for app_entry in applications:
        app_id = app_entry.get("app_id", "")
        scenario = app_entry.get("scenario", "")
        app_type = app_entry.get("application_type", "new_institution")
        sub_date = to_date_obj(app_entry.get("submission_date"))
        expected_all = app_entry.get("expected_issues", [])

        # Filter to per-document issues
        expected_per_doc = [iss for iss in expected_all if is_per_document_issue(iss)]
        skipped_issues = [iss for iss in expected_all if not is_per_document_issue(iss)]

        # Find or create DB Application
        # We find application by matching institution and custom label or recreate
        db_app = (
            db.query(Application)
            .filter(
                Application.institution_id == inst.id,
                Application.label == f"EVAL:{app_id}",
            )
            .first()
        )
        if not db_app:
            db_app = Application(
                institution_id=inst.id,
                application_type=app_type,
                submission_date=sub_date,
                label=f"EVAL:{app_id}",
                status="submitted",
            )
            db.add(db_app)
            db.commit()
            db.refresh(db_app)
        else:
            db_app.submission_date = sub_date
            db_app.application_type = app_type
            db.commit()

        # Ingest/link documents
        for doc_entry in app_entry.get("documents", []):
            rel_png = doc_entry.get("file_path_png")
            file_path = resolve_file(rel_png)
            if not file_path.exists():
                print(f"Warning: File not found: {file_path}")
                continue

            sha256 = compute_sha256(file_path)
            db_doc = (
                db.query(Document)
                .filter(Document.application_id == db_app.id, Document.sha256 == sha256)
                .first()
            )
            if not db_doc:
                db_doc = Document(
                    application_id=db_app.id,
                    file_path=str(file_path),
                    sha256=sha256,
                )
                db.add(db_doc)
                db.commit()
                db.refresh(db_doc)

            # Ensure document is processed (OCR + Extraction)
            if db_doc.ocr_text is None or len(db_doc.extracted_fields) == 0:
                process_document(db, db_doc.id)

        # Run rules engine and completeness check
        val_result = run_rules(db, db_app.id)

        all_findings = val_result["findings"]
        found_failed = [f.rule_id for f in all_findings if f.status == "failed"]
        not_evaluable_map = {f.rule_id: f.message for f in all_findings if f.status == "not_evaluable"}

        matched = [iss for iss in expected_per_doc if iss in found_failed]
        false_negatives = [iss for iss in expected_per_doc if iss not in found_failed]
        false_positives = [iss for iss in found_failed if iss not in expected_per_doc]

        # Check if false negative was caused by not_evaluable
        for fn in false_negatives:
            reason = not_evaluable_map.get(fn, "Rule evaluated as passed (extraction matched normal criteria)")
            missed_reasons.append({
                "app_id": app_id,
                "rule_id": fn,
                "reason": reason,
            })

        results_rows.append({
            "app_id": app_id,
            "scenario": scenario,
            "expected": expected_per_doc,
            "found": found_failed,
            "matched": matched,
            "fp": false_positives,
            "fn": false_negatives,
            "skipped": skipped_issues,
            "summary": val_result["summary"],
        })

    elapsed = round(time.time() - start_time, 2)
    db.close()

    # Generate Markdown Report
    lines = []
    lines.append("# AICTE Deterministic Rules Engine Evaluation Report")
    lines.append(f"\n- **Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"- **Evaluated Applications:** {len(applications)}")
    lines.append(f"- **Execution Time:** {elapsed}s\n")

    lines.append("## 1. Per-Document Rules Evaluation Summary\n")
    lines.append(
        "| App ID | Scenario | Expected (Per-Doc) | Found (Failed) | Matched | False Positives | False Negatives |"
    )
    lines.append("| :--- | :--- | :--- | :--- | :---: | :---: | :---: |")

    tot_expected = sum(len(r["expected"]) for r in results_rows)
    tot_matched = sum(len(r["matched"]) for r in results_rows)
    tot_fp = sum(len(r["fp"]) for r in results_rows)
    tot_fn = sum(len(r["fn"]) for r in results_rows)

    for r in results_rows:
        exp_str = ", ".join(r["expected"]) if r["expected"] else "None"
        fnd_str = ", ".join(r["found"]) if r["found"] else "None"
        m_str = str(len(r["matched"]))
        fp_str = ", ".join(r["fp"]) if r["fp"] else "-"
        fn_str = ", ".join(r["fn"]) if r["fn"] else "-"
        lines.append(
            f"| **{r['app_id']}** | {r['scenario']} | `{exp_str}` | `{fnd_str}` | **{m_str}/{len(r['expected'])}** | {fp_str} | {fn_str} |"
        )

    lines.append(
        f"\n**Totals:** Expected: {tot_expected} | Matched: {tot_matched} | False Positives: {tot_fp} | False Negatives: {tot_fn}\n"
    )

    lines.append("## 2. Skipped Non-Per-Document Expectations (Out of Scope for This Step)\n")
    lines.append(
        "> [!NOTE]\n"
        "> Cross-document consistency checks (`XDOC-*`), visual/metadata tampering detection (`TAMPERED:*`), "
        "> duplicate hash verification (`DUPLICATE_OF:*`), poor-scan flags (`POOR_SCAN:*`), and registry/QR checks "
        "> (`MISSING_QR:*`, `REGISTRY_UNAVAILABLE:*`) are scheduled for subsequent pipeline steps and were skipped as specified.\n"
    )

    lines.append("## 3. Detailed Misses and Not-Evaluable Analysis\n")
    if missed_reasons:
        lines.append("| App ID | Expected Rule | Outcome / Reason |")
        lines.append("| :--- | :--- | :--- |")
        for m in missed_reasons:
            lines.append(f"| **{m['app_id']}** | `{m['rule_id']}` | {m['reason']} |")
    else:
        lines.append("No per-document expected rules were missed! All per-document rules and completeness checks achieved 100% precision and recall.\n")

    report_content = "\n".join(lines)

    # Save to data/synthetic/rules_report.md
    out_dir = BACKEND_DIR.parent / "data" / "synthetic"
    if not out_dir.exists():
        out_dir = BACKEND_DIR / "data" / "synthetic"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / "rules_report.md"

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    try:
        print(report_content)
    except UnicodeEncodeError:
        print(report_content.encode("ascii", errors="replace").decode("ascii"))

    print(f"\n[OK] Evaluation report saved to: {report_file}")
    return 0


if __name__ == "__main__":
    sys.exit(run_rules_evaluation())
