import json
from datetime import date
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Institution, Application, Document, ExtractedField, ConsistencyResult
from app.services.consistency import run_consistency


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    yield session
    session.close()


def test_owner_equal_to_one_trustee_passes_any_of(db_session):
    """
    When land_document.owner_name is an individual trustee (e.g. 'Dr. Arvind Sharma')
    and trust_registration.trustee_names contains ['Dr. Arvind Sharma', 'Meena K. Patel'],
    the 'any_of' relation must successfully match and not conflict.
    """
    inst = Institution(name="Apex Institute of Technology", state="Maharashtra", trust_name="Apex Foundation")
    db_session.add(inst)
    db_session.commit()

    app = Application(
        institution_id=inst.id,
        application_type="new_institution",
        submission_date=date(2025, 6, 1),
        status="submitted",
    )
    db_session.add(app)
    db_session.commit()

    # Land document owned by trustee
    doc_land = Document(application_id=app.id, doc_type="land_document", file_path="dummy_land.png", sha256="dummy_land_sha")
    db_session.add(doc_land)
    db_session.commit()

    db_session.add(ExtractedField(
        document_id=doc_land.id,
        name="owner_name",
        value_original="Dr. Arvind Sharma",
        value_normalized="arvind sharma",
        confidence=0.95,
        needs_verification=False,
    ))

    # Trust document
    doc_trust = Document(application_id=app.id, doc_type="trust_registration", file_path="dummy_trust.png", sha256="dummy_trust_sha")
    db_session.add(doc_trust)
    db_session.commit()

    db_session.add(ExtractedField(
        document_id=doc_trust.id,
        name="trust_name",
        value_original="Apex Educational Foundation",
        value_normalized="apex educational foundation",
        confidence=0.95,
        needs_verification=False,
    ))
    db_session.add(ExtractedField(
        document_id=doc_trust.id,
        name="trustee_names",
        value_original=json.dumps(["Dr. Arvind Sharma", "Meena K. Patel"]),
        value_normalized=json.dumps(["arvind sharma", "meena k patel"]),
        confidence=0.95,
        needs_verification=False,
    ))
    db_session.commit()

    results = run_consistency(db_session, app.id)
    owner_trust_res = next((r for r in results if r.rule_id == "XDOC-OWNER-TRUST"), None)
    assert owner_trust_res is not None
    assert owner_trust_res.status == "match"
    assert owner_trust_res.score >= 90.0


def test_missing_field_gives_not_evaluable(db_session):
    """
    When one of the documents is missing or a field is unextracted/needs_verification,
    the rule must evaluate to 'not_evaluable' rather than producing a false conflict.
    """
    inst = Institution(name="Horizon Institute", state="Maharashtra", trust_name="Horizon Foundation")
    db_session.add(inst)
    db_session.commit()

    app = Application(
        institution_id=inst.id,
        application_type="new_institution",
        submission_date=date(2025, 6, 1),
        status="submitted",
    )
    db_session.add(app)
    db_session.commit()

    # Land document without trust document present
    doc_land = Document(application_id=app.id, doc_type="land_document", file_path="dummy_land.png", sha256="dummy_land_sha")
    db_session.add(doc_land)
    db_session.commit()

    db_session.add(ExtractedField(
        document_id=doc_land.id,
        name="owner_name",
        value_original="Horizon Foundation",
        value_normalized="horizon foundation",
        confidence=0.95,
        needs_verification=False,
    ))
    db_session.commit()

    results = run_consistency(db_session, app.id)
    owner_trust_res = next((r for r in results if r.rule_id == "XDOC-OWNER-TRUST"), None)
    assert owner_trust_res is not None
    assert owner_trust_res.status == "not_evaluable"
    assert "missing" in owner_trust_res.message.lower() or "missing" in owner_trust_res.explanation.lower()


def test_date_order_violation_gives_conflict(db_session):
    """
    When trust registered date is AFTER land registration date,
    XDOC-DATE-ORDER must produce a conflict.
    """
    inst = Institution(name="Chronology Test Institute", state="Maharashtra", trust_name="Chronology Trust")
    db_session.add(inst)
    db_session.commit()

    app = Application(
        institution_id=inst.id,
        application_type="new_institution",
        submission_date=date(2025, 6, 1),
        status="submitted",
    )
    db_session.add(app)
    db_session.commit()

    # Land registered earlier in 2018
    doc_land = Document(application_id=app.id, doc_type="land_document", file_path="dummy_land.png", sha256="dummy_land_sha")
    db_session.add(doc_land)
    db_session.commit()
    db_session.add(ExtractedField(
        document_id=doc_land.id,
        name="registration_date",
        value_original="2018-01-15",
        value_normalized="2018-01-15",
        confidence=0.95,
        needs_verification=False,
    ))

    # Trust registered later in 2022 (violates trust_date <= land_date)
    doc_trust = Document(application_id=app.id, doc_type="trust_registration", file_path="dummy_trust.png", sha256="dummy_trust_sha")
    db_session.add(doc_trust)
    db_session.commit()
    db_session.add(ExtractedField(
        document_id=doc_trust.id,
        name="registered_date",
        value_original="2022-08-20",
        value_normalized="2022-08-20",
        confidence=0.95,
        needs_verification=False,
    ))
    db_session.commit()

    results = run_consistency(db_session, app.id)
    date_order_res = next((r for r in results if r.rule_id == "XDOC-DATE-ORDER"), None)
    assert date_order_res is not None
    assert date_order_res.status == "conflict"


def test_run_consistency_is_idempotent(db_session):
    """Re-running consistency clears previous results and avoids duplicates."""
    inst = Institution(name="Idempotency Test Institute", state="Maharashtra", trust_name="Idempotency Trust")
    db_session.add(inst)
    db_session.commit()

    app = Application(
        institution_id=inst.id,
        application_type="new_institution",
        submission_date=date(2025, 6, 1),
        status="submitted",
    )
    db_session.add(app)
    db_session.commit()

    run1 = run_consistency(db_session, app.id)
    count1 = db_session.query(ConsistencyResult).filter(ConsistencyResult.application_id == app.id).count()

    run2 = run_consistency(db_session, app.id)
    count2 = db_session.query(ConsistencyResult).filter(ConsistencyResult.application_id == app.id).count()

    assert count1 == count2
    assert len(run1) == len(run2)
