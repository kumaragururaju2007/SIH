import os
import sys
import json
import time
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List, Optional

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.services.ocr import run_ocr, OcrResult
from app.services.qr import decode_qr
from app.services.classify import classify
from app.services.extract import get_extractor, ExtractedFieldData
from app.services.normalize import normalize_date, normalize_number, normalize_name, normalize_id


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


def match_field_value(field_name: str, true_val: Any, extracted_field: Optional[ExtractedFieldData]) -> bool:
    if extracted_field is None or extracted_field.value_original is None:
        return False

    norm_val = extracted_field.value_normalized or ""
    orig_val = extracted_field.value_original or ""

    # ID fields
    if any(k in field_name for k in ("number", "deed", "certificate")):
        t_id = normalize_id(str(true_val))
        return t_id == normalize_id(norm_val) or t_id == normalize_id(orig_val)

    # Date fields
    if any(k in field_name for k in ("date", "until")):
        t_date = normalize_date(str(true_val))
        return (t_date is not None and t_date == norm_val) or str(true_val) == norm_val

    # Numeric / Area fields
    if "area" in field_name or isinstance(true_val, (int, float)):
        try:
            t_f = float(true_val)
            e_f = float(norm_val)
            return abs(t_f - e_f) < 1.0 or (t_f > 0 and abs(t_f - e_f) / t_f < 0.02)
        except (ValueError, TypeError):
            pass

    # List fields (Trustees)
    if field_name in ("trustees", "trustee_names") or isinstance(true_val, list):
        try:
            ext_list = json.loads(norm_val) if norm_val.startswith("[") else [norm_val]
            t_list = [normalize_name(x) for x in (true_val if isinstance(true_val, list) else [true_val])]
            matches = sum(1 for t in t_list if any(t in e or e in t for e in ext_list))
            return matches >= max(1, len(t_list) * 0.5)
        except Exception:
            pass

    # Name fields
    if any(k in field_name for k in ("name", "owner", "trust")):
        t_norm = normalize_name(str(true_val))
        e_norm = normalize_name(str(norm_val))
        if t_norm and e_norm:
            if t_norm == e_norm or t_norm in e_norm or e_norm in t_norm:
                return True
            if fuzz and fuzz.ratio(t_norm, e_norm) >= 70:
                return True

    # General text fields (address, locality, issuing authority)
    t_str = str(true_val).strip().lower()
    e_str = str(norm_val if norm_val else orig_val).strip().lower()
    if t_str == e_str or t_str in e_str or e_str in t_str:
        return True
    if fuzz and fuzz.partial_ratio(t_str, e_str) >= 75:
        return True

    return False


def run_evaluation():
    manifest_path = resolve_file("data/synthetic/manifest.json")
    if not manifest_path.exists():
        manifest_path = BACKEND_DIR / "data" / "synthetic" / "manifest.json"
    if not manifest_path.exists():
        manifest_path = BACKEND_DIR.parent / "data" / "synthetic" / "manifest.json"

    if not manifest_path.exists():
        print(f"Error: manifest.json not found at {manifest_path}")
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    extractor = get_extractor()
    engine_name = "Tesseract (via tesserocr)" if "tesserocr" in sys.modules else "PaddleOCR"
    print(f"============================================================")
    print(f" AICTE Document Validation System - Extraction Evaluation")
    print(f" OCR Engine: {engine_name} | Extractor Provider: {settings.EXTRACTOR}")
    print(f" Manifest: {manifest_path}")
    print(f"============================================================\n")

    applications = manifest.get("applications", [])
    total_docs = 0

    # Metrics collectors
    doc_type_stats = defaultdict(lambda: {"total": 0, "class_correct": 0, "conf_sum": 0.0, "fields": defaultdict(lambda: {"total": 0, "correct": 0})})
    language_stats = defaultdict(lambda: {"total_fields": 0, "correct_fields": 0, "docs": 0, "class_correct": 0})
    poor_scan_stats = {"total_fields": 0, "correct_fields": 0, "docs": 0, "class_correct": 0}

    field_global_stats = defaultdict(lambda: {"total": 0, "correct": 0, "doc_type": ""})
    a09_hindi_fields: Dict[str, Any] = {}

    start_time = time.time()

    for app in applications:
        app_id = app.get("app_id", "")
        scenario = app.get("scenario", "")
        is_poor_scan = any(term in scenario.lower() for term in ("poor scan", "low contrast", "blur", "noise"))

        for doc_entry in app.get("documents", []):
            total_docs += 1
            true_doc_type = doc_entry.get("doc_type")
            true_fields = doc_entry.get("fields", {})
            doc_lang = doc_entry.get("language", "en")
            file_rel = doc_entry.get("file_path_png")

            file_path = resolve_file(file_rel)
            if not file_path.exists():
                print(f"Warning: File not found: {file_path}")
                continue

            file_str = str(file_path)

            # 1. OCR
            ocr_res = run_ocr(file_str)

            # 2. QR Decode
            qr_text = decode_qr(file_str)

            # 3. Classify
            pred_type, class_conf, reasons = classify(
                ocr_text=ocr_res.text,
                qr_text=qr_text,
                filename=file_path.name,
            )

            is_class_correct = (pred_type == true_doc_type)

            # 4. Extract
            extracted_fields = {}
            if pred_type:
                extracted_fields = extractor.extract(ocr_res, pred_type, qr_text=qr_text)

            # Record stats
            stats = doc_type_stats[true_doc_type]
            stats["total"] += 1
            if is_class_correct:
                stats["class_correct"] += 1
            stats["conf_sum"] += ocr_res.mean_confidence

            lang_stat = language_stats[doc_lang]
            lang_stat["docs"] += 1
            if is_class_correct:
                lang_stat["class_correct"] += 1

            if is_poor_scan:
                poor_scan_stats["docs"] += 1
                if is_class_correct:
                    poor_scan_stats["class_correct"] += 1

            # Save A09 land document fields for final report
            if app_id == "A09" and true_doc_type == "land_document":
                a09_hindi_fields = {
                    fname: {
                        "orig": ef.value_original,
                        "norm": ef.value_normalized,
                        "conf": ef.confidence,
                        "needs_verification": ef.needs_verification,
                    }
                    for fname, ef in extracted_fields.items()
                }

            # Field-level evaluation
            for fname, true_val in true_fields.items():
                if fname.endswith("_displayed"):
                    continue

                eval_true_val = true_val
                if fname == "valid_until" and "valid_until_displayed" in true_fields:
                    eval_true_val = true_fields["valid_until_displayed"]
                elif fname == "area_sqm" and "area_sqm_displayed" in true_fields:
                    eval_true_val = true_fields["area_sqm_displayed"]

                ext_field = extracted_fields.get(fname)
                if not ext_field:
                    if fname == "registered_date":
                        ext_field = extracted_fields.get("registration_date")
                    elif fname == "trustee_names":
                        ext_field = extracted_fields.get("trustees")

                is_correct = match_field_value(fname, eval_true_val, ext_field)

                stats["fields"][fname]["total"] += 1
                field_global_stats[f"{true_doc_type}.{fname}"]["total"] += 1
                field_global_stats[f"{true_doc_type}.{fname}"]["doc_type"] = true_doc_type

                lang_stat["total_fields"] += 1
                if is_poor_scan:
                    poor_scan_stats["total_fields"] += 1

                if is_correct:
                    stats["fields"][fname]["correct"] += 1
                    field_global_stats[f"{true_doc_type}.{fname}"]["correct"] += 1
                    lang_stat["correct_fields"] += 1
                    if is_poor_scan:
                        poor_scan_stats["correct_fields"] += 1

    elapsed = round(time.time() - start_time, 2)

    # Generate Markdown Report
    lines = []
    lines.append("# AICTE Document Extraction Evaluation Report")
    lines.append(f"\n- **Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"- **OCR Engine:** {engine_name}")
    lines.append(f"- **Extractor Provider:** `{settings.EXTRACTOR}`")
    lines.append(f"- **Total Documents Processed:** {total_docs}")
    lines.append(f"- **Total Time:** {elapsed}s (avg {elapsed/max(1, total_docs):.2f}s/doc)\n")

    lines.append("## 1. Document Type Summary\n")
    lines.append("| Document Type | Documents | Classification Accuracy | Mean OCR Confidence | Field Accuracy |")
    lines.append("| :--- | :---: | :---: | :---: | :---: |")

    for dtype, s in doc_type_stats.items():
        n = s["total"]
        c_acc = (s["class_correct"] / n) * 100 if n else 0
        mean_conf = (s["conf_sum"] / n) * 100 if n else 0
        tot_f = sum(f["total"] for f in s["fields"].values())
        cor_f = sum(f["correct"] for f in s["fields"].values())
        f_acc = (cor_f / tot_f) * 100 if tot_f else 0
        lines.append(f"| `{dtype}` | {n} | {c_acc:.1f}% | {mean_conf:.1f}% | **{f_acc:.1f}%** |")

    lines.append("\n## 2. Accuracy by Document Category\n")
    lines.append("| Category | Documents | Classification Accuracy | Field Accuracy |")
    lines.append("| :--- | :---: | :---: | :---: |")

    for lang, ls in language_stats.items():
        doc_cnt = ls["docs"]
        c_acc = (ls["class_correct"] / doc_cnt) * 100 if doc_cnt else 0
        f_acc = (ls["correct_fields"] / ls["total_fields"]) * 100 if ls["total_fields"] else 0
        lang_title = "English Documents" if lang == "en" else "Hindi Documents"
        lines.append(f"| {lang_title} (`{lang}`) | {doc_cnt} | {c_acc:.1f}% | **{f_acc:.1f}%** |")

    ps_docs = poor_scan_stats["docs"]
    ps_c_acc = (poor_scan_stats["class_correct"] / ps_docs) * 100 if ps_docs else 0
    ps_f_acc = (poor_scan_stats["correct_fields"] / poor_scan_stats["total_fields"]) * 100 if poor_scan_stats["total_fields"] else 0
    lines.append(f"| Poor-Scan / Degraded Documents | {ps_docs} | {ps_c_acc:.1f}% | **{ps_f_acc:.1f}%** |")

    # 10 Worst Fields
    lines.append("\n## 3. Ten Lowest Performing Fields\n")
    lines.append("| Rank | Field Name | Document Type | Total Checked | Correct | Accuracy |")
    lines.append("| :---: | :--- | :--- | :---: | :---: | :---: |")

    sorted_fields = []
    for full_name, f_data in field_global_stats.items():
        tot = f_data["total"]
        cor = f_data["correct"]
        acc = (cor / tot) * 100 if tot else 0
        fname = full_name.split(".", 1)[-1]
        sorted_fields.append((acc, fname, f_data["doc_type"], tot, cor))

    sorted_fields.sort(key=lambda x: (x[0], x[3]))
    for rank, (acc, fname, dtype, tot, cor) in enumerate(sorted_fields[:10], 1):
        lines.append(f"| {rank} | `{fname}` | `{dtype}` | {tot} | {cor} | {acc:.1f}% |")

    # A09 Land Document Extraction Details
    lines.append("\n## 4. Hindi Document Verification (A09 Land Document)\n")
    lines.append("| Field Name | Extracted Original | Normalized Value | Confidence | Needs Verification |")
    lines.append("| :--- | :--- | :--- | :---: | :---: |")
    for fname, data in a09_hindi_fields.items():
        orig_disp = str(data["orig"]).replace("\n", " ") if data["orig"] else "None"
        norm_disp = str(data["norm"]).replace("\n", " ") if data["norm"] else "None"
        lines.append(f"| `{fname}` | {orig_disp} | {norm_disp} | {data['conf']} | `{data['needs_verification']}` |")

    report_content = "\n".join(lines)

    # Save to data/synthetic/extraction_report.md
    out_dir = BACKEND_DIR.parent / "data" / "synthetic"
    if not out_dir.exists():
        out_dir = BACKEND_DIR / "data" / "synthetic"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / "extraction_report.md"

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    try:
        print(report_content)
    except UnicodeEncodeError:
        print(report_content.encode("ascii", errors="replace").decode("ascii"))
    print(f"\n[OK] Evaluation report saved to: {report_file}")


if __name__ == "__main__":
    run_evaluation()
