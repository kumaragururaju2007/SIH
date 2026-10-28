import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from app.services.normalize import (
    normalize_date,
    normalize_number,
    normalize_name,
    normalize_id,
    devanagari_to_ascii,
)


def test_devanagari_to_ascii_digits():
    """Verify conversion of Devanagari numerals to ASCII digits."""
    assert devanagari_to_ascii("०१२३४५६७८९") == "0123456789"
    assert devanagari_to_ascii("क्षेत्रफल १२,५००") == "क्षेत्रफल 12,500"


def test_normalize_date_formats():
    """Test date normalization across various formats and languages."""
    # Standard formats
    assert normalize_date("22/03/2021") == "2021-03-22"
    assert normalize_date("15-05-2024") == "2024-05-15"
    assert normalize_date("2026-04-15") == "2026-04-15"
    assert normalize_date("12 March 2024") == "2024-03-12"
    assert normalize_date("14 Nov 2016") == "2016-11-14"

    # Hindi / Devanagari date strings
    assert normalize_date("१५ मार्च २०२१") == "2021-03-15"
    assert normalize_date("१४-११-२०१६") == "2016-11-14"
    assert normalize_date("२२/०३/२०२१") == "2021-03-22"

    # Edge cases
    assert normalize_date("") is None
    assert normalize_date(None) is None
    assert normalize_date("invalid date string") is None


def test_normalize_number_and_units():
    """Test numeric normalization with commas, Devanagari digits, and land area units."""
    # Standard square metres
    val1, unit1 = normalize_number("12,500 sq.m")
    assert val1 == 12500.0
    assert unit1 == "sqm"

    val2, unit2 = normalize_number("6500 sqm")
    assert val2 == 6500.0

    # Devanagari number with Hindi unit
    val_hin, unit_hin = normalize_number("१३,००० वर्ग मीटर")
    assert val_hin == 13000.0
    assert unit_hin == "sqm"

    # Acres converted to sqm (1 acre ≈ 4046.86 sqm)
    val_acre, unit_acre = normalize_number("2.5 acres")
    assert unit_acre == "acre"
    assert round(val_acre, 1) == 10117.1

    # Hectares converted to sqm (1 ha = 10,000 sqm)
    val_ha, unit_ha = normalize_number("1.2 hectares")
    assert unit_ha == "hectare"
    assert val_ha == 12000.0


def test_normalize_names_and_honorifics():
    """Test name normalization with honorific stripping, transliteration, and variation handling."""
    # Honorific stripping
    assert normalize_name("Dr. Rajesh Deshmukh") == "rajesh deshmukh"
    assert normalize_name("Smt. Sunita Patil") == "sunita patil"
    assert normalize_name("M/s Apex Educational Foundation") == "apex educational foundation"

    # Benign variation across Shri, Sri, Shree
    n1 = normalize_name("Shri Sai Education Trust")
    n2 = normalize_name("Sri Sai Education Trust")
    n3 = normalize_name("Shree Sai Education Trust")
    assert n1 == n2 == n3 == "sai education trust"

    # Hindi Devanagari transliteration
    hin_name1 = normalize_name("श्री विनायक एजुकेशन ट्रस्ट")
    assert "vinayaka" in hin_name1
    assert "ejukeshana" in hin_name1

    hin_name2 = normalize_name("रमेश्वर प्रसाद शर्मा")
    assert "rameshvara" in hin_name2
    assert "sharma" in hin_name2


def test_normalize_id():
    """Test identifier normalization."""
    assert normalize_id("FS-2024-A01-901") == "FS2024A01901"
    assert normalize_id("LD 2021 / A09 / 441") == "LD2021A09441"
    assert normalize_id("TR_2016-A01.702") == "TR2016A01702"
    assert normalize_id("पंजी-२०२२-०९२४") == "पंजी20220924"
