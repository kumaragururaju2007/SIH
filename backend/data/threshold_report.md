# AICTE Cross-Document Consistency Threshold Tuning Report

- **Timestamp:** 2026-10-27 19:12:16 UTC
- **Dataset:** `name_pairs.csv` (43 hand-labelled pairs across 8 diversity categories)
- **Evaluation Type:** Deterministic grid parameter sweep (NOT machine learning training)

> [!IMPORTANT]
> **Methodology Note:** This tuning is strictly an empirical calibration sweep over a curated 43-pair 
> heuristic benchmark. It tests that token normalization, Devanagari transliteration, and typo edit-distance 
> guards properly separate genuine institutional matches from distinct entities.

## 1. Threshold Parameter Sweep

| `match_min` | `partial_min` | Match Prec. | Match Recall | Conflict Prec. | Conflict Recall | Match FP |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 80.0 | 65.0 | 100.0% | 100.0% | 100.0% | 100.0% | 0 **(Recommended)** |
| 80.0 | 70.0 | 100.0% | 100.0% | 100.0% | 100.0% | 0 |
| 80.0 | 75.0 | 100.0% | 100.0% | 100.0% | 100.0% | 0 |
| 85.0 | 65.0 | 100.0% | 88.0% | 100.0% | 100.0% | 0 |
| 85.0 | 70.0 | 100.0% | 88.0% | 100.0% | 100.0% | 0 |
| 85.0 | 75.0 | 100.0% | 88.0% | 100.0% | 100.0% | 0 |
| 85.0 | 80.0 | 100.0% | 88.0% | 100.0% | 100.0% | 0 |
| 90.0 | 65.0 | 100.0% | 88.0% | 100.0% | 100.0% | 0 |
| 90.0 | 70.0 | 100.0% | 88.0% | 100.0% | 100.0% | 0 |
| 90.0 | 75.0 | 100.0% | 88.0% | 100.0% | 100.0% | 0 |
| 90.0 | 80.0 | 100.0% | 88.0% | 100.0% | 100.0% | 0 |
| 95.0 | 65.0 | 100.0% | 84.0% | 100.0% | 100.0% | 0 |
| 95.0 | 70.0 | 100.0% | 84.0% | 100.0% | 100.0% | 0 |
| 95.0 | 75.0 | 100.0% | 84.0% | 100.0% | 100.0% | 0 |
| 95.0 | 80.0 | 100.0% | 84.0% | 100.0% | 100.0% | 0 |

## 2. Recommended Threshold Settings

- **Recommended `match_min`:** `80.0`
- **Recommended `partial_min`:** `65.0`
- **Rationale:** Achieves 100.0% match precision and 100.0% conflict recall with **zero false matches** (`fp_match = 0`).
- **Guardrail Protection:** Personal names with distinct tokens (e.g. `Ramesh Kumar` vs `Suresh Kumar`) are capped below `partial_min`, preventing fatal false approvals.

## 3. Errors / Edge Cases at Recommended Thresholds

Zero misclassifications on the 43-pair benchmark at recommended thresholds! All pairs evaluated correctly.
