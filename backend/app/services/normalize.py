import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, Union
from dateutil import parser as date_parser
from indic_transliteration import sanscript

# Devanagari to ASCII digits mapping
DEVANAGARI_DIGITS_TABLE = str.maketrans("०१२३४५६७८९", "0123456789")

# Hindi Month Mapping
HINDI_MONTHS = {
    "जनवरी": "January",
    "फरवरी": "February",
    "फ़रवरी": "February",
    "मार्च": "March",
    "अप्रैल": "April",
    "मई": "May",
    "जून": "June",
    "जुलाई": "July",
    "अगस्त": "August",
    "सितंबर": "September",
    "सितम्बर": "September",
    "अक्टूबर": "October",
    "नवंबर": "November",
    "नवम्बर": "November",
    "दिसंबर": "December",
    "दिसम्बर": "December",
}

# Honorifics to strip in English and Hindi
HONORIFICS_PATTERN = re.compile(
    r"\b(shri|sri|shree|smt|shrimati|mr|mrs|ms|dr|prof|m/s|messrs)\b|\b(श्री|श्रीमती|डॉ|प्रो)\b",
    re.IGNORECASE,
)


def devanagari_to_ascii(text: str) -> str:
    """Converts Devanagari numerals to standard ASCII numerals."""
    if not text:
        return ""
    return str(text).translate(DEVANAGARI_DIGITS_TABLE)


def normalize_date(date_str: Any) -> Optional[str]:
    """
    Parses DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, '12 March 2024',
    Hindi month names and Devanagari digits into standard ISO YYYY-MM-DD string.
    """
    if not date_str:
        return None

    cleaned = str(date_str).strip()
    # Convert Devanagari numerals to ASCII digits
    cleaned = devanagari_to_ascii(cleaned)

    # Replace Hindi month names with English equivalents
    for hin, eng in HINDI_MONTHS.items():
        if hin in cleaned:
            cleaned = cleaned.replace(hin, eng)

    # Clean punctuation and extra spaces
    cleaned = re.sub(r"[\.,]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Try ISO YYYY-MM-DD direct match
    iso_match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", cleaned)
    if iso_match:
        y, m, d = iso_match.groups()
        try:
            return datetime(int(y), int(m), int(d)).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Try DD/MM/YYYY or DD-MM-YYYY
    dmy_match = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", cleaned)
    if dmy_match:
        d, m, y = dmy_match.groups()
        try:
            return datetime(int(y), int(m), int(d)).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Fall back to dateutil with dayfirst=True
    try:
        parsed = date_parser.parse(cleaned, dayfirst=True, fuzzy=True)
        return parsed.strftime("%Y-%m-%d")
    except Exception:
        return None


def normalize_number(num_val: Any) -> Tuple[Optional[float], Optional[str]]:
    """
    Extracts numeric value from text, converts Devanagari numerals,
    handles commas, and standardizes area units (sqm, acres, hectares) to square metres.
    Returns: (normalized_value_in_sqm, original_unit_detected)
    """
    if num_val is None:
        return None, None

    text = devanagari_to_ascii(str(num_val)).strip()

    # Detect unit
    text_lower = text.lower()
    unit = "sqm"
    factor = 1.0

    if "acre" in text_lower or "एकड़" in text_lower:
        unit = "acre"
        factor = 4046.8564  # 1 acre = 4046.8564 sqm
    elif "hectare" in text_lower or "हेक्टेयर" in text_lower or "ha" in text_lower.split():
        unit = "hectare"
        factor = 10000.0  # 1 hectare = 10,000 sqm
    elif "sq.m" in text_lower or "sqm" in text_lower or "sq m" in text_lower or "वर्ग मीटर" in text_lower:
        unit = "sqm"
        factor = 1.0

    # Extract digits with optional decimal point, removing commas
    match = re.search(r"[-+]?\d+(?:,\d+)*(?:\.\d+)?", text)
    if not match:
        return None, unit

    num_cleaned = match.group(0).replace(",", "")
    try:
        val = float(num_cleaned) * factor
        return round(val, 2), unit
    except ValueError:
        return None, unit


def normalize_name(name_str: Any) -> str:
    """
    Normalizes a person or institution/trust name:
    - Transliterates Devanagari Hindi into Latin if present
    - Lowercases
    - Strips honorifics (shri, sri, shree, smt, dr, श्री, etc.)
    - Collapses spaces and removes punctuation
    """
    if not name_str:
        return ""

    raw = str(name_str).strip()

    # If Devanagari characters are present, transliterate to Latin
    has_devanagari = any("\u0900" <= ch <= "\u097F" for ch in raw)
    if has_devanagari:
        raw = sanscript.transliterate(raw, sanscript.DEVANAGARI, sanscript.ITRANS)

    text = raw.lower()

    # Strip honorifics
    text = HONORIFICS_PATTERN.sub("", text)

    # Standardize phonetic spelling variations for "shri" / "sri" / "shree"
    text = re.sub(r"\b(shree|shri|sri)\b", "", text)

    # Remove non-alphanumeric characters (keep spaces)
    text = re.sub(r"[^\w\s]", " ", text)
    # Collapse multiple whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def normalize_id(id_str: Any) -> str:
    """
    Normalizes an identification / registration / certificate code:
    - Converts Devanagari numerals to ASCII
    - Uppercases
    - Strips spaces, dashes, slashes, and periods
    """
    if not id_str:
        return ""

    raw = devanagari_to_ascii(str(id_str)).upper()
    # Strip whitespace, dashes, slashes, periods, colons
    cleaned = re.sub(r"[\s\-_/\.:]", "", raw)
    return cleaned
