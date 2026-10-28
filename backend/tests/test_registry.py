import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Document, ExtractedField
from app.services.auth.registry import verify_registry, RegistryClient


class FakeRegistryClient(RegistryClient):
    def __init__(self, records=None, available=True):
        self.records = records or {}
        self.available = available

    def lookup(self, doc_type: str, number: str):
        if not self.available:
            return None, False
        rec = self.records.get(doc_type, {}).get(number)
        return (rec, True)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_registry_match(db_session):
    """When all verified registry fields match document fields, outcome is 'match'."""
    doc = Document(id=101, application_id=1, doc_type="fire_safety_certificate", file_path="d.png", sha256="s")
    db_session.add(doc)
    ef1 = ExtractedField(document_id=101, name="certificate_number", value_original="FS-101", value_normalized="FS-101")
    ef2 = ExtractedField(document_id=101, name="valid_until", value_original="2026-04-15", value_normalized="2026-04-15")
    db_session.add_all([ef1, ef2])
    db_session.commit()

    client = FakeRegistryClient({
        "fire_safety_certificate": {
            "FS-101": {
                "certificate_number": "FS-101",
                "valid_until": "2026-04-15",
                "status": "valid",
            }
        }
    })

    res = verify_registry(db=db_session, document=doc, client=client)
    assert res["result"] == "match"
    assert res["evidence"]["status"] == "match"


def test_registry_field_mismatch(db_session):
    """When a registry field differs (e.g. valid_until or area_sqm), outcome is 'mismatch'."""
    doc = Document(id=101, application_id=1, doc_type="land_document", file_path="d.png", sha256="s")
    db_session.add(doc)
    ef1 = ExtractedField(document_id=101, name="registration_number", value_original="LD-201", value_normalized="LD-201")
    ef2 = ExtractedField(document_id=101, name="area_sqm", value_original="12,500 sq.m", value_normalized="12500")
    db_session.add_all([ef1, ef2])
    db_session.commit()

    # Registry has original smaller area: 7500
    client = FakeRegistryClient({
        "land_document": {
            "LD-201": {
                "registration_number": "LD-201",
                "area_sqm": 7500.0,
                "status": "registered",
            }
        }
    })

    res = verify_registry(db=db_session, document=doc, client=client)
    assert res["result"] == "mismatch"
    assert "registry_field_mismatch" in res["signals"]
    assert len(res["evidence"]["differing_fields"]) == 1
    diff = res["evidence"]["differing_fields"][0]
    assert diff["field"] == "area_sqm"
    assert diff["registry_value"] == 7500.0
    assert diff["extracted_value"] == "12500"


def test_registry_not_found(db_session):
    """When record does not exist in registry, outcome is 'not_found'."""
    doc = Document(id=101, application_id=1, doc_type="fire_safety_certificate", file_path="d.png", sha256="s")
    db_session.add(doc)
    ef1 = ExtractedField(document_id=101, name="certificate_number", value_original="FS-999-ABSENT", value_normalized="FS-999-ABSENT")
    db_session.add(ef1)
    db_session.commit()

    client = FakeRegistryClient({})
    res = verify_registry(db=db_session, document=doc, client=client)
    assert res["result"] == "not_found"
    assert "registry_record_not_found" in res["signals"]


def test_registry_unavailable(db_session):
    """When registry client reports unavailable / offline, outcome is 'unavailable'."""
    doc = Document(id=101, application_id=1, doc_type="fire_safety_certificate", file_path="d.png", sha256="s")
    db_session.add(doc)
    ef1 = ExtractedField(document_id=101, name="certificate_number", value_original="FS-101", value_normalized="FS-101")
    db_session.add(ef1)
    db_session.commit()

    client = FakeRegistryClient(available=False)
    res = verify_registry(db=db_session, document=doc, client=client)
    assert res["result"] == "unavailable"
    assert "registry_service_unavailable" in res["signals"]
