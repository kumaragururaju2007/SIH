import pytest
from app.services.matching import (
    calculate_name_score,
    compare_ids,
    compare_dates,
    compare_addresses,
    normalize_name_for_matching,
)


def test_honorific_variants_match():
    """Dr. Arvind Sharma vs Arvind Sharma should match with high confidence."""
    score, status, steps = calculate_name_score("Dr. Arvind Sharma", "Arvind Sharma")
    assert status == "match"
    assert score >= 90.0

    score2, status2, _ = calculate_name_score("Shri Ramesh Patel", "Ramesh Patel")
    assert status2 == "match"
    assert score2 >= 90.0


def test_hindi_and_english_transliterated_names_match():
    """Devanagari Hindi name must match transliterated English equivalent."""
    hindi_name = "श्री विनायक एजुकेशन ट्रस्ट"
    english_name = "Vinayak Education Trust"
    score, status, steps = calculate_name_score(hindi_name, english_name)
    assert status == "match"
    assert score >= 85.0


def test_different_people_same_surname_guarded_conflict():
    """
    Ramesh Kumar vs Suresh Kumar should NOT match despite high token overlap.
    Guardrail caps the score below partial_min to guarantee a conflict.
    """
    score, status, steps = calculate_name_score("Ramesh Kumar", "Suresh Kumar", match_min=85.0, partial_min=70.0)
    assert status == "conflict"
    assert score < 70.0
    assert any("guardrail_triggered" in step for step in steps)


def test_typo_in_one_letter_gives_partial_or_match():
    """Single-letter typos (edit distance 1) should be recognized as partial or match."""
    # Apeex vs Apex (edit distance 1)
    score, status, steps = calculate_name_score("Apeex Educational Foundation", "Apex Educational Foundation")
    assert status in ("match", "partial")
    assert score >= 70.0

    # Horizn vs Horizon
    score2, status2, steps2 = calculate_name_score("Horizn Institute of Technology", "Horizon Institute of Technology")
    assert status2 in ("match", "partial")
    assert score2 >= 70.0


def test_completely_different_trusts_conflict():
    """Completely different entities must yield a conflict outcome."""
    score, status, steps = calculate_name_score("Apex Educational Trust", "Universal Global Foundation")
    assert status == "conflict"
    assert score < 70.0


def test_extra_legal_words_ignored():
    """Legal suffixes like (Regd.), Pvt Ltd, Society should be stripped without penalizing score."""
    score, status, steps = calculate_name_score(
        "Horizon Educational Trust (Regd.)",
        "Horizon Educational Trust",
    )
    assert status == "match"
    assert score == 100.0

    score2, status2, steps2 = calculate_name_score(
        "Apex Foundation Pvt Ltd",
        "Apex Foundation",
    )
    assert status2 == "match"
    assert score2 == 100.0


def test_id_comparison():
    """Test normalized exact match and edit distance 1 partial for IDs."""
    score, status = compare_ids("TR/2021/441", "TR-2021-441")
    assert status == "match"
    assert score == 100.0

    # Single-char typo: 441 vs 442
    score2, status2 = compare_ids("TR-2021-441", "TR-2021-442")
    assert status2 == "partial"
    assert score2 == 80.0

    # Disparate IDs
    score3, status3 = compare_ids("TR-2021-441", "FS-2024-901")
    assert status3 == "conflict"
    assert score3 == 0.0


def test_date_chronology_comparison():
    """Test date order: left <= right."""
    # Valid chronological order: trust registered 2016-11-14 before land registered 2021-03-22
    score, status, msg = compare_dates("2016-11-14", "2021-03-22")
    assert status == "match"
    assert score == 100.0

    # Same day is also valid
    score2, status2, _ = compare_dates("2021-03-22", "2021-03-22")
    assert status2 == "match"
    assert score2 == 100.0

    # Inverted chronology: violation
    score3, status3, msg3 = compare_dates("2024-05-10", "2021-03-22")
    assert status3 == "conflict"
    assert score3 == 0.0
