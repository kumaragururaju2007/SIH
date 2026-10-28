import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Institution, Application, Document
from app.services.auth.metadata import check_metadata, parse_pdf_date


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_parse_pdf_date():
    """Verify parsing of PDF D: format strings."""
    d1 = parse_pdf_date("D:20240416100000Z")
    assert d1 is not None
    assert d1.year == 2024
    assert d1.month == 4
    assert d1.day == 16

    d2 = parse_pdf_date("20210322120000")
    assert d2 is not None
    assert d2.year == 2021
    assert d2.month == 3
    assert d2.day == 22

    assert parse_pdf_date(None) is None
    assert parse_pdf_date("") is None


def test_clean_metadata_ok(db_session):
    """Clean document metadata with matching CreationDate and ModDate passes as 'ok'."""
    inst = Institution(id=1, name="Apex Institute", trust_name="Apex Trust", state="Maharashtra")
    db_session.add(inst)
    app = Application(id=1, institution_id=1, application_type="new_institution", status="submitted")
    db_session.add(app)
    doc = Document(id=101, application_id=1, doc_type="fire_safety_certificate", file_path="dummy.pdf", sha256="s1")
    db_session.add(doc)
    db_session.commit()

    mock_raw = {
        "source": "pdf",
        "producer": "Synthetic Issuer System",
        "creator": "Synthetic Authority PDF Engine",
        "creationDate": "D:20240416100000Z",
        "modDate": "D:20240416100000Z",
    }

    with patch("app.services.auth.metadata.extract_raw_metadata", return_value=mock_raw):
        res = check_metadata(db=db_session, document=doc)
        assert res["result"] == "ok"
        assert res["signals"] == []
        assert res["evidence"]["status"] == "ok"


def test_suspicious_producer(db_session):
    """Metadata mentioning Photoshop or other image editors must trigger 'suspicious_producer' signal."""
    inst = Institution(id=1, name="Apex Institute", trust_name="Apex Trust", state="Maharashtra")
    db_session.add(inst)
    app = Application(id=1, institution_id=1, application_type="new_institution", status="submitted")
    db_session.add(app)
    doc = Document(id=101, application_id=1, doc_type="land_document", file_path="dummy.pdf", sha256="s1")
    db_session.add(doc)
    db_session.commit()

    mock_raw = {
        "source": "pdf",
        "producer": "Adobe Photoshop 24.1 (Windows)",
        "creator": "Adobe Photoshop",
        "creationDate": "D:20210322100000Z",
        "modDate": "D:20210322100000Z",
    }

    with patch("app.services.auth.metadata.extract_raw_metadata", return_value=mock_raw):
        res = check_metadata(db=db_session, document=doc)
        assert res["result"] == "suspicious"
        assert "suspicious_producer" in res["signals"]


def test_moddate_gap_suspicious(db_session):
    """ModDate several weeks after CreationDate must trigger 'mod_date_gap_exceeded' signal."""
    inst = Institution(id=1, name="Apex Institute", trust_name="Apex Trust", state="Maharashtra")
    db_session.add(inst)
    app = Application(id=1, institution_id=1, application_type="new_institution", status="submitted")
    db_session.add(app)
    doc = Document(id=101, application_id=1, doc_type="fire_safety_certificate", file_path="dummy.pdf", sha256="s1")
    db_session.add(doc)
    db_session.commit()

    mock_raw = {
        "source": "pdf",
        "producer": "Synthetic Issuer System",
        "creator": "Synthetic Authority PDF Engine",
        "creationDate": "D:20240416100000Z",
        "modDate": "D:20240521153000Z",  # 35 days later
    }

    with patch("app.services.auth.metadata.extract_raw_metadata", return_value=mock_raw):
        res = check_metadata(db=db_session, document=doc, config={"metadata_max_gap_days": 1})
        assert res["result"] == "suspicious"
        assert "mod_date_gap_exceeded" in res["signals"]


def test_unavailable_metadata(db_session):
    """Missing or empty metadata must report 'unavailable', not suspicious."""
    inst = Institution(id=1, name="Apex Institute", trust_name="Apex Trust", state="Maharashtra")
    db_session.add(inst)
    app = Application(id=1, institution_id=1, application_type="new_institution", status="submitted")
    db_session.add(app)
    doc = Document(id=101, application_id=1, doc_type="fire_safety_certificate", file_path="dummy.png", sha256="s1")
    db_session.add(doc)
    db_session.commit()

    mock_raw = {}

    with patch("app.services.auth.metadata.extract_raw_metadata", return_value=mock_raw):
        res = check_metadata(db=db_session, document=doc)
        assert res["result"] == "unavailable"
        assert res["signals"] == []
        assert res["evidence"]["status"] == "unavailable"
