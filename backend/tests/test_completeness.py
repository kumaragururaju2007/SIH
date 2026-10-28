import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Institution, Application, Document
from app.services.completeness import check_completeness


@pytest.fixture
def db_session():
    """Create fresh isolated in-memory SQLite database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    inst = Institution(name="Test Inst", state="DL", trust_name="Test Trust")
    session.add(inst)
    session.commit()

    yield session
    session.close()


def test_a01_completeness_complete(db_session):
    """Test A01 with all 3 required documents is complete."""
    app = Application(
        institution_id=1,
        application_type="new_institution",
    )
    db_session.add(app)
    db_session.commit()

    # Add all 3 documents
    for dtype in ("fire_safety_certificate", "land_document", "trust_registration"):
        doc = Document(
            application_id=app.id,
            doc_type=dtype,
            file_path=f"storage/uploads/{dtype}.png",
            sha256=f"hash_{dtype}",
            ocr_confidence=0.95,
        )
        db_session.add(doc)
    db_session.commit()

    result = check_completeness(db_session, app.id)
    assert result["is_complete"] is True
    assert len(result["missing"]) == 0
    assert len(result["missing_findings"]) == 0
    assert set(result["present"]) == {"fire_safety_certificate", "land_document", "trust_registration"}


def test_a02_completeness_missing_trust(db_session):
    """Test A02 missing trust_registration produces missing list and MISSING finding."""
    app = Application(
        institution_id=1,
        application_type="new_institution",
    )
    db_session.add(app)
    db_session.commit()

    # Add only fire and land documents
    for dtype in ("fire_safety_certificate", "land_document"):
        doc = Document(
            application_id=app.id,
            doc_type=dtype,
            file_path=f"storage/uploads/{dtype}.png",
            sha256=f"hash_{dtype}",
            ocr_confidence=0.92,
        )
        db_session.add(doc)
    db_session.commit()

    result = check_completeness(db_session, app.id)
    assert result["is_complete"] is False
    assert result["missing"] == ["trust_registration"]
    assert len(result["missing_findings"]) == 1
    finding = result["missing_findings"][0]
    assert finding.rule_id == "MISSING:trust_registration"
    assert finding.severity == "high"
    assert finding.status == "failed"


def test_unrecognized_document_listed(db_session):
    """Test documents with null or empty doc_type are marked unrecognized."""
    app = Application(
        institution_id=1,
        application_type="new_institution",
    )
    db_session.add(app)
    db_session.commit()

    # Unrecognized doc
    doc_unrec = Document(
        application_id=app.id,
        doc_type=None,
        file_path="storage/uploads/unknown.png",
        sha256="hash_unknown",
    )
    db_session.add(doc_unrec)
    db_session.commit()

    result = check_completeness(db_session, app.id)
    assert doc_unrec.id in result["unrecognized"]
    assert result["is_complete"] is False


def test_duplicate_document_type_handled(db_session):
    """Test duplicate documents of the same type pick the higher confidence document."""
    app = Application(
        institution_id=1,
        application_type="new_institution",
    )
    db_session.add(app)
    db_session.commit()

    # Two fire certificates with different confidence
    doc1 = Document(
        application_id=app.id,
        doc_type="fire_safety_certificate",
        file_path="storage/uploads/fire1.png",
        sha256="hash_fire_1",
        ocr_confidence=0.72,
    )
    doc2 = Document(
        application_id=app.id,
        doc_type="fire_safety_certificate",
        file_path="storage/uploads/fire2.png",
        sha256="hash_fire_2",
        ocr_confidence=0.96,
    )
    db_session.add_all([doc1, doc2])
    db_session.commit()

    result = check_completeness(db_session, app.id)
    assert "fire_safety_certificate" in result["duplicates_of_type"]
    active_doc = result["active_documents"]["fire_safety_certificate"]
    assert active_doc.id == doc2.id
    assert active_doc.ocr_confidence == 0.96
