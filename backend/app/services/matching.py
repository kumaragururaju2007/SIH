import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set

import yaml
from rapidfuzz import fuzz, distance

from app.config import settings
from app.services.rules_engine import to_date_obj


from app.services.normalize import normalize_name


def load_name_normalization_config(config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Load configurable synonym groups, legal suffixes, and spelling variants from YAML."""
    if config_dir is None:
        config_dir = Path(settings.CONFIG_DIR)

    norm_file = config_dir / "consistency" / "name_normalization.yaml"
    if not norm_file.exists():
        candidate = Path(__file__).resolve().parent.parent.parent / "configs" / "consistency" / "name_normalization.yaml"
        if candidate.exists():
            norm_file = candidate

    if not norm_file.exists():
        return {
            "synonym_groups": {},
            "legal_suffixes": [],
            "spelling_variants": {},
        }

    with open(norm_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def normalize_name_for_matching(
    raw_text: str,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[str, List[str]]:
    """
    Apply multi-stage normalization pipeline to an entity or person name:
    1. Base transliteration from Devanagari to Latin and honorifics stripping.
    2. Lowercase, strip punctuation and normalize spaces.
    3. Strip legal suffix tokens (e.g. regd, ltd, pvt, public).
    4. Collapse common phonetic variants and romanization prefixes (shri/sri, w/v, doubled vowels).
    5. Canonicalize institutional and organizational synonym stems.

    Returns:
      (normalized_string, list_of_transformation_steps)
    """
    if not raw_text:
        return "", ["empty_input"]

    if config is None:
        config = load_name_normalization_config()

    steps: List[str] = [f"raw: {raw_text}"]

    # 1. Base normalization: honorifics stripping and Devanagari transliteration
    pre_cleaned = str(raw_text).replace("¢", "c")
    base_cleaned = normalize_name(pre_cleaned)
    if base_cleaned != raw_text:
        steps.append(f"base_normalized: {base_cleaned}")

    # Clean punctuation, lowercase, normalize spaces
    # Normalize common OCR symbol misreads (e.g. ¢ -> c)
    cleaned_text = base_cleaned.replace("¢", "c")
    s = re.sub(r"[^\w\s]", " ", cleaned_text.lower())
    s = s.replace("te hnole", "technole")
    s = re.sub(r"\s+", " ", s).strip()
    steps.append(f"cleaned: {s}")

    tokens = s.split()
    if not tokens:
        return "", steps

    # Discard standalone OCR artefact digit tokens (e.g. '00', '5')
    tokens = [t for t in tokens if not t.isdigit()]
    if not tokens:
        return "", steps

    # 2. Remove legal suffixes
    legal_suffixes = set(config.get("legal_suffixes", []))
    filtered_tokens = [t for t in tokens if t not in legal_suffixes]
    if len(filtered_tokens) != len(tokens):
        s = " ".join(filtered_tokens)
        tokens = filtered_tokens
        steps.append(f"legal_suffixes_removed: {s}")

    # 3. Collapse spelling variants (letter substitutions, prefixes, aliases, doubled vowels)
    spelling = config.get("spelling_variants", {})
    prefixes = spelling.get("prefixes", {})
    substitutions = spelling.get("substitutions", {})
    aliases = spelling.get("aliases", {})
    doubled_vowels = spelling.get("doubled_vowels", {})

    collapsed_tokens = []
    for t in tokens:
        w = t
        # Aliases mapping (e.g. vaniyaka -> vinayak)
        if w in aliases:
            w = aliases[w]

        # Prefix replacement (e.g. shri -> sri)
        for pfx, rep in prefixes.items():
            if w == pfx or w.startswith(pfx + "_"):
                w = rep
                break

        # Letter substitutions (e.g. w -> v, ph -> f)
        for old_ch, new_ch in substitutions.items():
            w = w.replace(old_ch, new_ch)

        # Doubled vowels collapse (e.g. ee -> i, oo -> u, aa -> a)
        for dbl, single in doubled_vowels.items():
            w = w.replace(dbl, single)

        collapsed_tokens.append(w)

    tokens = collapsed_tokens
    s = " ".join(tokens)
    steps.append(f"spelling_collapsed: {s}")

    # 4. Canonicalize synonyms (after spelling normalization)
    synonym_map: Dict[str, str] = {}
    for canonical, syn_list in config.get("synonym_groups", {}).items():
        for syn in syn_list:
            synonym_map[syn.lower()] = canonical.lower()

    syn_replaced_tokens = [synonym_map.get(t, t) for t in tokens]
    if syn_replaced_tokens != tokens:
        s = " ".join(syn_replaced_tokens)
        tokens = syn_replaced_tokens
        steps.append(f"synonyms_canonicalized: {s}")

    final_str = " ".join(tokens)
    return final_str, steps


def calculate_name_score(
    name1: str,
    name2: str,
    match_min: float = 85.0,
    partial_min: float = 70.0,
    max_typo_dist: int = 1,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[float, str, List[str]]:
    """
    Calculate deterministic matching score between two names using RapidFuzz.

    Formula:
      token_score = max(fuzz.token_set_ratio(n1, n2), fuzz.token_sort_ratio(n1, n2))
      char_score  = fuzz.ratio(n1.replace(' ', ''), n2.replace(' ', ''))
      base_score  = 0.65 * token_score + 0.35 * char_score

    Guardrail against false matches:
      When two names differ by non-synonym, non-typo tokens (e.g. 'Ramesh Kumar' vs 'Suresh Kumar'),
      token_set_ratio alone could artificially inflate the score. If differing tokens exceed
      max_typo_dist (Levenshtein distance > 1), the final score is capped at (partial_min - 1)
      to strictly guarantee a conflict outcome.

    Returns:
      (score, status, matching_steps) where status is 'match' | 'partial' | 'conflict'
    """
    norm1, steps1 = normalize_name_for_matching(name1, config=config)
    norm2, steps2 = normalize_name_for_matching(name2, config=config)

    steps = [f"left: {norm1}", f"right: {norm2}"]

    if not norm1 or not norm2:
        return 0.0, "conflict", steps

    if norm1 == norm2:
        return 100.0, "match", steps + ["exact_match: 100.0"]

    # Calculate rapidfuzz metrics
    token_set = fuzz.token_set_ratio(norm1, norm2)
    token_sort = fuzz.token_sort_ratio(norm1, norm2)
    token_score = max(token_set, token_sort)

    char_score = fuzz.ratio(norm1.replace(" ", ""), norm2.replace(" ", ""))

    # Documented weighted combination
    base_score = round(0.65 * token_score + 0.35 * char_score, 2)
    steps.append(f"metrics: token_set={token_set:.1f}, token_sort={token_sort:.1f}, char={char_score:.1f} -> base={base_score:.1f}")

    # Guardrail: Check for differing personal name tokens
    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())
    diff1 = tokens1 - tokens2
    diff2 = tokens2 - tokens1

    if diff1 and diff2:
        # Check if every differing token in diff1 has a near-neighbor in diff2 within max_typo_dist
        has_distinct_different_name = False
        for t1 in diff1:
            min_dist = min(distance.Levenshtein.distance(t1, t2) for t2 in diff2)
            if min_dist > max_typo_dist:
                has_distinct_different_name = True
                steps.append(f"guardrail_triggered: differing token '{t1}' dist {min_dist} > {max_typo_dist}")
                break

        if has_distinct_different_name:
            capped_score = min(base_score, partial_min - 1.0)
            steps.append(f"score_capped: {base_score} -> {capped_score}")
            base_score = capped_score

    # Determine status
    if base_score >= match_min:
        status = "match"
    elif base_score >= partial_min:
        status = "partial"
    else:
        status = "conflict"

    return base_score, status, steps


def compare_ids(id_left: str, id_right: str) -> Tuple[float, str]:
    """Compare registration or certificate IDs with strict format tolerance."""
    c1 = re.sub(r"[\s\-_/]", "", str(id_left).strip().upper())
    c2 = re.sub(r"[\s\-_/]", "", str(id_right).strip().upper())

    if not c1 or not c2:
        return 0.0, "conflict"

    if c1 == c2:
        return 100.0, "match"

    dist = distance.Levenshtein.distance(c1, c2)
    if dist == 1:
        return 80.0, "partial"

    return 0.0, "conflict"


def compare_dates(
    date_left_raw: Any,
    date_right_raw: Any,
) -> Tuple[float, str, str]:
    """
    Compare chronological relationship between two ISO dates.
    Validates that date_left <= date_right (e.g. trust incorporated before land acquisition).
    """
    d_left = to_date_obj(date_left_raw)
    d_right = to_date_obj(date_right_raw)

    if d_left is None or d_right is None:
        return 0.0, "not_evaluable", f"Invalid date format: left='{date_left_raw}', right='{date_right_raw}'"

    if d_left <= d_right:
        score = 100.0
        status = "match"
        msg = f"Date order valid: {d_left.isoformat()} <= {d_right.isoformat()}"
    else:
        score = 0.0
        status = "conflict"
        msg = f"Date order violated: {d_left.isoformat()} is after {d_right.isoformat()}"

    return score, status, msg


def compare_addresses(
    addr1: str,
    addr2: str,
    match_min: float = 75.0,
    partial_min: float = 50.0,
) -> Tuple[float, str, List[str]]:
    """Compare physical addresses using token-based normalization."""
    c1 = re.sub(r"[^\w\s]", " ", str(addr1).lower())
    c2 = re.sub(r"[^\w\s]", " ", str(addr2).lower())
    c1 = re.sub(r"\s+", " ", c1).strip()
    c2 = re.sub(r"\s+", " ", c2).strip()

    if not c1 or not c2:
        return 0.0, "conflict", ["empty_address"]

    t_set = fuzz.token_set_ratio(c1, c2)
    t_sort = fuzz.token_sort_ratio(c1, c2)
    score = round(max(t_set, t_sort), 2)

    if score >= match_min:
        status = "match"
    else:
        # Address comparison is informational only (institutions commonly have separate campus vs trust registered office)
        status = "partial"

    steps = [f"addr1: {c1}", f"addr2: {c2}", f"score: {score}"]
    return score, status, steps
