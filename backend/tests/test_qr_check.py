import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Document, ExtractedField
from app.services.auth.qr_check import verify_qr_code, parse_qr_payload


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_parse_qr_payload():
    p1 = parse_qr_payload("CERT:FS-2024-A01-901|AUTH:Maharashtra Fire|EXP:2026-04-15")
    assert p1 is not None
    assert p1["CERT"] == "FS-2024-A01-901"
    assert p1["EXP"] == "2026-04-15"

    p2 = parse_qr_payload('{"certificate_number": "FS-101", "status": "valid"}')
    assert p2 is not None
    assert p2["CERTIFICATE_NUMBER"] == "FS-101"

    assert parse_qr_payload(None) is None
    assert parse_qr_payload("") is None


def test_qr_match(db_session):
    """When QR payload ID matches document extracted field, outcome is 'match'."""
    doc = Document(
        id=101,
        application_id=1,
        doc_type="fire_safety_certificate",
        file_path="dummy.png",
        sha256="s1",
        qr_text="CERT:FS-2024-A01-901|AUTH:Fire Dept|EXP:2026-04-15",
    )
    db_session.add(doc)
    db_session.commit()

    ef = ExtractedField(
        document_id=101,
        name="certificate_number",
        value_original="FS-2024-A01-901",
        value_normalized="FS-2024-A01-901",
    )
    db_session.add(ef)
    db_session.commit()

    res = verify_qr_code(db=db_session, document=doc)
    assert res["result"] == "match"
    assert res["evidence"]["status"] == "match"
    assert res["evidence"]["qr_id_normalized"] == "FS2024A01901"


def test_qr_mismatch(db_session):
    """When QR payload ID differs from extracted text, outcome is 'mismatch'."""
    doc = Document(
        id=101,
        application_id=1,
        doc_type="fire_safety_certificate",
        file_path="dummy.png",
        sha256="s1",
        qr_text="CERT:FS-2024-A01-901|AUTH:Fire Dept|EXP:2026-04-15",
    )
    db_session.add(doc)
    db_session.commit()

    ef = ExtractedField(
        document_id=101,
        name="certificate_number",
        value_original="FS-2024-ALTERED-999",
        value_normalized="FS-2024-ALTERED-999",
    )
    db_session.add(ef)
    db_session.commit()

    res = verify_qr_code(db=db_session, document=doc)
    assert res["result"] == "mismatch"
    assert "qr_id_mismatch" in res["signals"]


def test_qr_absent(db_session):
    """When no QR code is present on document, outcome is 'absent' reported as unavailable."""
    doc = Document(
        id=101,
        application_id=1,
        doc_type="fire_safety_certificate",
        file_path="dummy.png",
        sha256="s1",
        qr_text=None,
    )
    db_session.add(doc)
    db_session.commit()

    res = verify_qr_code(db=db_session, document=doc)
    assert res["result"] == "absent"
    assert res["evidence"]["status"] == "unavailable"
    assert res["signals"] == []
