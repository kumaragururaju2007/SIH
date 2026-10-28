from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "configs" / "classification.yaml"

# Cached classification config
_CLASSIFICATION_CONFIG = None


def load_classification_config() -> dict:
    global _CLASSIFICATION_CONFIG
    if _CLASSIFICATION_CONFIG is None:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                _CLASSIFICATION_CONFIG = yaml.safe_load(f)
        else:
            _CLASSIFICATION_CONFIG = {
                "threshold": 0.20,
                "keywords": {
                    "fire_safety_certificate": {"english": ["fire", "safety", "noc"], "hindi": ["अग्नि", "सुरक्षा"]},
                    "land_document": {"english": ["land", "plot", "area"], "hindi": ["भूमि", "खसरा", "भूखंड"]},
                    "trust_registration": {"english": ["trust", "society", "trustee"], "hindi": ["न्यास", "ट्रस्ट"]},
                },
            }
    return _CLASSIFICATION_CONFIG


def classify(
    ocr_text: Optional[str],
    qr_text: Optional[str] = None,
    filename: Optional[str] = None,
    file_name: Optional[str] = None,
) -> Tuple[Optional[str], float, List[str]]:
    """
    Classifies a document into one of the known document types or None if unrecognized.
    Returns: (doc_type or None, confidence_score [0.0 - 1.0], reasons)
    """
    if file_name and not filename:
        filename = file_name
    cfg = load_classification_config()
    threshold = cfg.get("threshold", 0.20)
    keywords_cfg = cfg.get("keywords", {})

    scores: Dict[str, float] = {dtype: 0.0 for dtype in keywords_cfg.keys()}
    reasons_map: Dict[str, List[str]] = {dtype: [] for dtype in keywords_cfg.keys()}

    # 1. Evaluate QR text signals (strong hint if available)
    if qr_text:
        qr_upper = qr_text.upper()
        if "CERT:" in qr_upper or "AUTH:" in qr_upper or "FIRE" in qr_upper:
            scores["fire_safety_certificate"] += 0.35
            reasons_map["fire_safety_certificate"].append(f"QR payload signature matches fire certificate ({qr_text[:30]}...)")
        if "LAND_REG:" in qr_upper or "AREA:" in qr_upper:
            scores["land_document"] += 0.35
            reasons_map["land_document"].append(f"QR payload signature matches land document ({qr_text[:30]}...)")
        if "TRUST_REG:" in qr_upper or "TRUST:" in qr_upper:
            scores["trust_registration"] += 0.35
            reasons_map["trust_registration"].append(f"QR payload signature matches trust registration ({qr_text[:30]}...)")

    # 2. Evaluate OCR text keywords (English and Hindi)
    if ocr_text and ocr_text.strip():
        text_lower = ocr_text.lower()
        for dtype, lang_dict in keywords_cfg.items():
            matched_en = [kw for kw in lang_dict.get("english", []) if kw.lower() in text_lower]
            matched_hi = [kw for kw in lang_dict.get("hindi", []) if kw in ocr_text]

            total_matches = len(matched_en) + len(matched_hi)
            if total_matches > 0:
                # Up to 0.60 contribution from keyword matches
                kw_score = min(total_matches * 0.12, 0.60)
                scores[dtype] += kw_score
                matched_all = matched_en + matched_hi
                reasons_map[dtype].append(f"Matched {len(matched_all)} keywords: {', '.join(matched_all[:4])}")

    # 3. Evaluate Filename as weak hint only (max 0.05, never deciding)
    if filename:
        fname_lower = filename.lower()
        for dtype in keywords_cfg.keys():
            if dtype in fname_lower:
                scores[dtype] += 0.05
                reasons_map[dtype].append("Filename contains document type substring (weak hint)")

    # 4. Determine winning candidate
    best_dtype = None
    best_score = 0.0

    for dtype, score in scores.items():
        if score > best_score:
            best_score = score
            best_dtype = dtype

    # Cap score at 1.0
    best_score = min(round(best_score, 2), 1.0)

    if best_score < threshold or best_dtype is None:
        return None, best_score, ["Confidence score below threshold; document unrecognized"]

    return best_dtype, best_score, reasons_map[best_dtype]
