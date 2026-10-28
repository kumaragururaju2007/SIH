import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Institution, Application, Document, ExtractedField
from app.services.auth.duplicates import check_duplicates, are_applications_linked


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_parent_child_resubmission_not_duplicate(db_session):
    """Documents inside draft copies/resubmissions linked by parent_application_id must NOT count as duplicates."""
    inst = Institution(id=1, name="Apex Institute", trust_name="Apex Trust", state="Maharashtra")
    db_session.add(inst)
    db_session.commit()

    # Original Application
    app1 = Application(id=1, institution_id=1, application_type="new_institution", status="deficiency_sent")
    db_session.add(app1)
    db_session.commit()

    doc1 = Document(
        id=101,
        application_id=1,
        doc_type="fire_safety_certificate",
        file_path="dummy/path1.png",
        sha256="abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd",
        phash="ffff0000ffff0000",
    )
    db_session.add(doc1)
    db_session.commit()

    ef1 = ExtractedField(
        document_id=101,
        name="certificate_number",
        value_original="FS-2024-901",
        value_normalized="FS-2024-901",
    )
    db_session.add(ef1)
    db_session.commit()

    # Resubmission Application linked via parent_application_id
    app2 = Application(id=2, institution_id=1, application_type="new_institution", status="submitted", parent_application_id=1)
    db_session.add(app2)
    db_session.commit()

    assert are_applications_linked(app1, app2) is True

    doc2 = Document(
        id=102,
        application_id=2,
        doc_type="fire_safety_certificate",
        file_path="dummy/path2.png",
        sha256="abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd",  # identical sha256
        phash="ffff0000ffff0000",  # identical phash
    )
    db_session.add(doc2)
    db_session.commit()

    ef2 = ExtractedField(
        document_id=102,
        name="certificate_number",
        value_original="FS-2024-901",
        value_normalized="FS-2024-901",  # identical certificate number
    )
    db_session.add(ef2)
    db_session.commit()

    # Run duplicate check on resubmission document
    res = check_duplicates(db=db_session, document=doc2)
    assert res["result"] == "ok"
    assert res["signals"] == []
    assert res["evidence"]["duplicate_found"] is False


def test_exact_duplicate_different_application(db_session):
    """Identical sha256 in an unlinked application must be flagged as exact_duplicate."""
    inst1 = Institution(id=1, name="Apex Institute", trust_name="Apex Trust", state="Maharashtra")
    inst2 = Institution(id=2, name="Beacon College", trust_name="Beacon Trust", state="Karnataka")
    db_session.add_all([inst1, inst2])
    db_session.commit()

    app1 = Application(id=1, institution_id=1, application_type="new_institution", status="approved")
    app2 = Application(id=2, institution_id=2, application_type="new_institution", status="submitted")
    db_session.add_all([app1, app2])
    db_session.commit()

    doc1 = Document(
        id=101,
        application_id=1,
        doc_type="fire_safety_certificate",
        file_path="dummy/path1.png",
        sha256="1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff",
    )
    doc2 = Document(
        id=102,
        application_id=2,
        doc_type="fire_safety_certificate",
        file_path="dummy/path2.png",
        sha256="1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff",
    )
    db_session.add_all([doc1, doc2])
    db_session.commit()

    res = check_duplicates(db=db_session, document=doc2)
    assert res["result"] == "suspicious"
    assert "exact_duplicate" in res["signals"]
    assert len(res["evidence"]["exact_matches"]) == 1
    assert res["evidence"]["exact_matches"][0]["application_id"] == 1
    assert res["evidence"]["exact_matches"][0]["institution_name"] == "Apex Institute"


def test_near_duplicate_phash(db_session):
    """pHash within Hamming distance threshold must be flagged as near_duplicate."""
    inst1 = Institution(id=1, name="Apex Institute", trust_name="Apex Trust", state="Maharashtra")
    inst2 = Institution(id=2, name="Beacon College", trust_name="Beacon Trust", state="Karnataka")
    db_session.add_all([inst1, inst2])
    db_session.commit()

    app1 = Application(id=1, institution_id=1, application_type="new_institution", status="approved")
    app2 = Application(id=2, institution_id=2, application_type="new_institution", status="submitted")
    db_session.add_all([app1, app2])
    db_session.commit()

    # Hashes with Hamming distance of 2 (differing by 2 bits)
    # f = 1111, e = 1110 (1 bit diff), d = 1101 (1 bit diff) -> distance 2
    h1 = "ffffffffffffffff"
    h2 = "fffffffefffffffd"

    doc1 = Document(
        id=101,
        application_id=1,
        doc_type="land_document",
        file_path="dummy/path1.png",
        sha256="sha1111",
        phash=h1,
    )
    doc2 = Document(
        id=102,
        application_id=2,
        doc_type="land_document",
        file_path="dummy/path2.png",
        sha256="sha2222",
        phash=h2,
    )
    db_session.add_all([doc1, doc2])
    db_session.commit()

    res = check_duplicates(db=db_session, document=doc2, config={"phash_hamming_near_duplicate": 5})
    assert res["result"] == "suspicious"
    assert "near_duplicate" in res["signals"]
    assert len(res["evidence"]["near_matches"]) == 1
    assert res["evidence"]["near_matches"][0]["hamming_distance"] <= 5


def test_certificate_number_reuse(db_session):
    """Reusing extracted certificate number across different institutions must be flagged as id_reuse."""
    inst1 = Institution(id=1, name="Apex Institute", trust_name="Apex Trust", state="Maharashtra")
    inst2 = Institution(id=2, name="Zenith College", trust_name="Zenith Trust", state="Maharashtra")
    db_session.add_all([inst1, inst2])
    db_session.commit()

    app1 = Application(id=1, institution_id=1, application_type="new_institution", status="approved")
    app2 = Application(id=2, institution_id=2, application_type="new_institution", status="submitted")
    db_session.add_all([app1, app2])
    db_session.commit()

    doc1 = Document(id=101, application_id=1, doc_type="fire_safety_certificate", file_path="d1.png", sha256="s1")
    doc2 = Document(id=102, application_id=2, doc_type="fire_safety_certificate", file_path="d2.png", sha256="s2")
    db_session.add_all([doc1, doc2])
    db_session.commit()

    ef1 = ExtractedField(document_id=101, name="certificate_number", value_original="FS-2024-901", value_normalized="FS-2024-901")
    ef2 = ExtractedField(document_id=102, name="certificate_number", value_original="FS-2024-901", value_normalized="FS-2024-901")
    db_session.add_all([ef1, ef2])
    db_session.commit()

    res = check_duplicates(db=db_session, document=doc2)
    assert res["result"] == "suspicious"
    assert "id_reuse" in res["signals"]
    assert len(res["evidence"]["id_reuses"]) == 1
    assert res["evidence"]["id_reuses"][0]["reused_value"] == "FS-2024-901"
    assert res["evidence"]["id_reuses"][0]["institution_name"] == "Apex Institute"
