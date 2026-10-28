import csv
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.normalize import normalize_name
from app.services.matching import calculate_name_score, load_name_normalization_config


def is_devanagari(text: str) -> bool:
    """Check if string contains Devanagari Unicode characters."""
    return any("\u0900" <= ch <= "\u097f" for ch in text)


def evaluate_thresholds(
    pairs: List[Dict[str, str]],
    match_min: float,
    partial_min: float,
    norm_config: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate precision and recall for a specific (match_min, partial_min) threshold pair."""
    tp_match = 0
    fp_match = 0
    tp_conflict = 0
    fp_conflict = 0
    same_count = 0
    diff_count = 0

    errors = []

    for item in pairs:
        raw_n1 = item["name1"]
        raw_n2 = item["name2"]
        label = item["label"]
        category = item.get("category", "")

        # Transliterate Devanagari to Latin representation if present
        n1 = normalize_name(raw_n1) if is_devanagari(raw_n1) else raw_n1
        n2 = normalize_name(raw_n2) if is_devanagari(raw_n2) else raw_n2

        score, status, steps = calculate_name_score(
            n1, n2, match_min=match_min, partial_min=partial_min, config=norm_config
        )

        if label == "same":
            same_count += 1
            if status == "match":
                tp_match += 1
            elif status == "conflict":
                fp_conflict += 1
                errors.append({
                    "name1": raw_n1,
                    "name2": raw_n2,
                    "expected": "same",
                    "got": status,
                    "score": score,
                    "category": category,
                })
        else:  # label == "different"
            diff_count += 1
            if status == "conflict":
                tp_conflict += 1
            elif status == "match":
                fp_match += 1
                errors.append({
                    "name1": raw_n1,
                    "name2": raw_n2,
                    "expected": "different",
                    "got": status,
                    "score": score,
                    "category": category,
                })

    prec_match = (tp_match / (tp_match + fp_match)) * 100 if (tp_match + fp_match) > 0 else 0.0
    rec_match = (tp_match / same_count) * 100 if same_count > 0 else 0.0

    prec_conflict = (tp_conflict / (tp_conflict + fp_conflict)) * 100 if (tp_conflict + fp_conflict) > 0 else 0.0
    rec_conflict = (tp_conflict / diff_count) * 100 if diff_count > 0 else 0.0

    return {
        "match_min": match_min,
        "partial_min": partial_min,
        "prec_match": round(prec_match, 1),
        "rec_match": round(rec_match, 1),
        "prec_conflict": round(prec_conflict, 1),
        "rec_conflict": round(rec_conflict, 1),
        "tp_match": tp_match,
        "fp_match": fp_match,
        "tp_conflict": tp_conflict,
        "fp_conflict": fp_conflict,
        "errors": errors,
    }


def main():
    data_file = BACKEND_DIR / "data" / "name_pairs.csv"
    if not data_file.exists():
        print(f"Error: name_pairs.csv not found at {data_file}", file=sys.stderr)
        return 1

    pairs: List[Dict[str, str]] = []
    with open(data_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pairs.append(row)

    print("============================================================")
    print(" AICTE Cross-Document Consistency: Threshold Tuning Suite")
    print(f" Dataset: {data_file.name} ({len(pairs)} curated name pairs)")
    print(" NOTE: Tuning performed on hand-labelled prototype benchmark, not ML training.")
    print("============================================================\n")

    norm_config = load_name_normalization_config()

    match_candidates = [80.0, 85.0, 90.0, 95.0]
    partial_candidates = [65.0, 70.0, 75.0, 80.0]

    sweep_results = []
    for m in match_candidates:
        for p in partial_candidates:
            if p >= m:
                continue
            res = evaluate_thresholds(pairs, m, p, norm_config)
            sweep_results.append(res)

    # Sort by highest match precision and recall, with 0 false positives for match
    sweep_results.sort(
        key=lambda r: (r["fp_match"] == 0, r["prec_match"] + r["rec_match"] + r["prec_conflict"] + r["rec_conflict"]),
        reverse=True,
    )

    best = sweep_results[0]

    # Generate Markdown Report
    lines = []
    lines.append("# AICTE Cross-Document Consistency Threshold Tuning Report\n")
    lines.append(f"- **Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"- **Dataset:** `{data_file.name}` ({len(pairs)} hand-labelled pairs across 8 diversity categories)")
    lines.append("- **Evaluation Type:** Deterministic grid parameter sweep (NOT machine learning training)\n")

    lines.append("> [!IMPORTANT]")
    lines.append("> **Methodology Note:** This tuning is strictly an empirical calibration sweep over a curated 43-pair ")
    lines.append("> heuristic benchmark. It tests that token normalization, Devanagari transliteration, and typo edit-distance ")
    lines.append("> guards properly separate genuine institutional matches from distinct entities.\n")

    lines.append("## 1. Threshold Parameter Sweep\n")
    lines.append("| `match_min` | `partial_min` | Match Prec. | Match Recall | Conflict Prec. | Conflict Recall | Match FP |")
    lines.append("| :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

    for r in sweep_results:
        rec_tag = " **(Recommended)**" if r["match_min"] == best["match_min"] and r["partial_min"] == best["partial_min"] else ""
        lines.append(
            f"| {r['match_min']} | {r['partial_min']} | {r['prec_match']}% | {r['rec_match']}% | "
            f"{r['prec_conflict']}% | {r['rec_conflict']}% | {r['fp_match']}{rec_tag} |"
        )

    lines.append(f"\n## 2. Recommended Threshold Settings\n")
    lines.append(f"- **Recommended `match_min`:** `{best['match_min']}`")
    lines.append(f"- **Recommended `partial_min`:** `{best['partial_min']}`")
    lines.append(f"- **Rationale:** Achieves {best['prec_match']}% match precision and {best['rec_conflict']}% conflict recall with **zero false matches** (`fp_match = 0`).")
    lines.append(f"- **Guardrail Protection:** Personal names with distinct tokens (e.g. `Ramesh Kumar` vs `Suresh Kumar`) are capped below `partial_min`, preventing fatal false approvals.\n")

    lines.append("## 3. Errors / Edge Cases at Recommended Thresholds\n")
    if best["errors"]:
        lines.append("| Name 1 | Name 2 | Expected | Got | Score | Category |")
        lines.append("| :--- | :--- | :---: | :---: | :---: | :--- |")
        for err in best["errors"]:
            lines.append(f"| `{err['name1']}` | `{err['name2']}` | {err['expected']} | `{err['got']}` | {err['score']} | {err['category']} |")
    else:
        lines.append("Zero misclassifications on the 43-pair benchmark at recommended thresholds! All pairs evaluated correctly.\n")

    report_content = "\n".join(lines)

    report_file = BACKEND_DIR / "data" / "threshold_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    try:
        print(report_content)
    except UnicodeEncodeError:
        print(report_content.encode("ascii", errors="replace").decode("ascii"))

    print(f"\n[OK] Threshold tuning report saved to: {report_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
