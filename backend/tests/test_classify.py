import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from app.services.classify import classify


def test_classify_english_fire_safety():
    """Verify classification of an English fire safety certificate."""
    ocr_text = (
        "STATE GOVERNMENT - DEPARTMENT OF FIRE & RESCUE SERVICES\n"
        "NO OBJECTION CERTIFICATE (N.O.C.) - FIRE & LIFE SAFETY\n"
        "Certificate Number: FS-2024-A01-901\n"
        "This is to certify that building complies with National Building Code norms."
    )
    doc_type, conf, reasons = classify(ocr_text, qr_text="CERT:FS-2024-A01|AUTH:Fire Dept")
    assert doc_type == "fire_safety_certificate"
    assert conf >= 0.40
    assert any("fire" in r.lower() for r in reasons)


def test_classify_english_land_document():
    """Verify classification of an English land deed document."""
    ocr_text = (
        "REVENUE DEPARTMENT - LAND RECORDS & TITLE DIVISION\n"
        "CERTIFICATE OF LAND TITLE & PROPERTY REGISTRATION\n"
        "Registration Deed No: LD-2021-A01-441\n"
        "Plot / Survey Number: Plot 104/A\n"
        "Total Land Area (sq.m): 12,500 sq.m"
    )
    doc_type, conf, reasons = classify(ocr_text)
    assert doc_type == "land_document"
    assert conf >= 0.30


def test_classify_english_trust_registration():
    """Verify classification of an English public trust registration document."""
    ocr_text = (
        "GOVERNMENT OF INDIA - CHARITY COMMISSIONER OFFICE\n"
        "CERTIFICATE OF PUBLIC CHARITABLE TRUST REGISTRATION\n"
        "Trust Registration No: TR-2016-A01-702\n"
        "Name of the Trust: Apex Educational Foundation\n"
        "Governing Trustees: Dr. Rajesh Deshmukh, Sunita Patil"
    )
    doc_type, conf, reasons = classify(ocr_text)
    assert doc_type == "trust_registration"
    assert conf >= 0.30


def test_classify_hindi_land_document():
    """Verify classification of a Hindi Devanagari land title document."""
    ocr_text = (
        "महाराष्ट्र शासन - भूमि एवं राजस्व विभाग\n"
        "भूमि स्वत्व एवं स्वामित्व पंजीकरण प्रमाण पत्र\n"
        "पंजीकरण संख्या: LD-2021-A09-441\n"
        "भूखंड / खसरा संख्या: Plot 96/A\n"
        "कुल क्षेत्रफल (वर्ग मीटर): 13,000 वर्ग मीटर"
    )
    doc_type, conf, reasons = classify(ocr_text)
    assert doc_type == "land_document"
    assert conf >= 0.30


def test_classify_nonsense_text_returns_none():
    """Verify that unrelated gibberish / nonsense text returns None (unrecognized)."""
    ocr_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore."
    doc_type, conf, reasons = classify(ocr_text)
    assert doc_type is None
    assert conf < 0.20
    assert "unrecognized" in reasons[0].lower()


def test_classify_empty_returns_none():
    """Verify empty or None text returns None."""
    doc_type, conf, _ = classify("")
    assert doc_type is None
    assert conf == 0.0

    doc_type2, conf2, _ = classify(None)
    assert doc_type2 is None
    assert conf2 == 0.0
