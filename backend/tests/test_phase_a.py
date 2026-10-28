import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app as fastapi_app
from app.models import (
    Institution,
    InstitutionHistory,
    Application,
    Document,
    RuleResult,
    ConsistencyResult,
    AuthResult,
    AuditLog,
)
from app.services.labels import determine_document_label, determine_application_labels
from app.services.risk import calculate_application_risk


from sqlalchemy.pool import StaticPool

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


def test_a11_highest_score_and_a01_lowest(db_session):
    """Test A11 (tampered, conflicts, duplicates, unverified) gets highest risk and A01 (clean) among lowest."""
    inst1 = Institution(id=1, name="Clean Institute A01", trust_name="Trust A01", state="Delhi")
    inst11 = Institution(id=11, name="Problematic Institute A11", trust_name="Trust A11", state="Haryana")
    db_session.add_all([inst1, inst11])
    db_session.commit()

    # Clean App A01
    app1 = Application(id=1, institution_id=1, application_type="new_institution", status="submitted")
    doc1 = Document(id=101, application_id=1, doc_type="land_document", file_path="a01.png", sha256="s1")
    db_session.add_all([app1, doc1])
    db_session.commit()

    # Add passing rule and matching registry for A01
    rr1 = RuleResult(application_id=1, document_id=101, rule_id="LAND-AREA", status="passed", passed=True, severity="high", message="Area OK")
    auth1_reg = AuthResult(document_id=101, check_type="registry", result="match", probability=1.0)
    auth1_tamp = AuthResult(document_id=101, check_type="tampering", result="ok", probability=0.04)
    db_session.add_all([rr1, auth1_reg, auth1_tamp])
    db_session.commit()

    # Problem App A11: high tampering, failed rules, consistency conflict, duplicate flag, adverse history
    h11 = InstitutionHistory(institution_id=11, year=2025, outcome="rejected", flags_count=3, deficiency_count=4)
    app11 = Application(id=11, institution_id=11, application_type="new_institution", status="submitted")
    doc11 = Document(id=111, application_id=11, doc_type="land_document", file_path="a11.png", sha256="s11")
    db_session.add_all([h11, app11, doc11])
    db_session.commit()

    rr11 = RuleResult(application_id=11, document_id=111, rule_id="LAND-AREA", status="failed", passed=False, severity="high", message="Area deficit")
    rr11_b = RuleResult(application_id=11, document_id=111, rule_id="FIRE-EXPIRY", status="failed", passed=False, severity="high", message="Certificate expired")
    cr11 = ConsistencyResult(application_id=11, rule_id="XDOC-OWNER-TRUST", field="owner_name", status="conflict", outcome="conflict", severity="high", message="Owner conflict")
    auth11_tamp = AuthResult(document_id=111, check_type="tampering", result="high_suspicion", probability=0.92)
    auth11_dup = AuthResult(document_id=111, check_type="duplicate", result="duplicate", evidence={"duplicate_found": True, "signals": ["phash_near_duplicate"]})
    auth11_reg = AuthResult(document_id=111, check_type="registry", result="mismatch", evidence={"differing_fields": [{"field": "owner"}]})
    db_session.add_all([rr11, rr11_b, cr11, auth11_tamp, auth11_dup, auth11_reg])
    db_session.commit()

    # Evaluate risk scores
    risk1 = calculate_application_risk(db_session, 1)
    risk11 = calculate_application_risk(db_session, 11)

    assert risk1["risk_score"] < 25.0, f"Clean app score expected < 25, got {risk1['risk_score']}"
    assert risk1["risk_band"] == "low"
    assert risk11["risk_score"] > 60.0, f"Problematic app score expected > 60, got {risk11['risk_score']}"
    assert risk11["risk_band"] == "high"
    assert risk11["risk_score"] > risk1["risk_score"]

    # Verify disclaimer is present
    assert "Illustrative score. Supports the officer's decision; does not replace it." in risk11["disclaimer"]


def test_history_factor_increases_risk_for_flagged_institution(db_session):
    """The same document set under an institution with flagged history must score higher than under a clean one."""
    inst_clean = Institution(id=2, name="Clean Tech", trust_name="Trust 2", state="Punjab")
    inst_flagged = Institution(id=3, name="Flagged Tech", trust_name="Trust 3", state="Punjab")
    db_session.add_all([inst_clean, inst_flagged])
    db_session.commit()

    # Add adverse regulatory history for inst_flagged
    h1 = InstitutionHistory(institution_id=3, year=2025, outcome="rejected", flags_count=3, deficiency_count=5)
    h2 = InstitutionHistory(institution_id=3, year=2024, outcome="rejected", flags_count=2, deficiency_count=3)
    db_session.add_all([h1, h2])
    db_session.commit()

    # Create identical applications
    app_clean = Application(id=20, institution_id=2, application_type="new_institution", status="submitted")
    app_flagged = Application(id=30, institution_id=3, application_type="new_institution", status="submitted")
    doc20 = Document(id=201, application_id=20, doc_type="land_document", file_path="f20.png", sha256="h20")
    doc30 = Document(id=301, application_id=30, doc_type="land_document", file_path="f30.png", sha256="h30")
    db_session.add_all([app_clean, app_flagged, doc20, doc30])
    db_session.commit()

    risk_clean = calculate_application_risk(db_session, 20)
    risk_flagged = calculate_application_risk(db_session, 30)

    assert risk_flagged["risk_score"] > risk_clean["risk_score"]
    history_factor_item = next(f for f in risk_flagged["all_factors"] if f["key"] == "history_factor")
    assert "prior rejection" in history_factor_item["description"].lower()


def test_override_requires_reason_and_preserves_system_label(client, db_session):
    """Override requires at least 10 chars reason and keeps original system label."""
    inst = Institution(id=4, name="Test College", trust_name="Trust 4", state="Goa")
    app = Application(id=40, institution_id=4, application_type="new_institution", status="submitted")
    doc = Document(id=401, application_id=40, doc_type="land_document", file_path="d40.png", sha256="s40", label="possible_tampering", system_label="possible_tampering")
    db_session.add_all([inst, app, doc])
    db_session.commit()

    # 1. Reason too short (< 10 chars) should fail with 422
    res_short = client.post(
        "/officer/applications/40/override",
        json={"document_id": 401, "new_label": "verified", "reason": "too short"},
    )
    assert res_short.status_code == 422

    # 2. Valid override with reason >= 10 chars
    res_ok = client.post(
        "/officer/applications/40/override",
        headers={"X-Demo-User": "Officer Sharma"},
        json={"document_id": 401, "new_label": "verified", "reason": "Physical deed verified during on-site spot inspection."},
    )
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert data["label"] == "verified"
    assert data["system_label"] == "possible_tampering"
    assert data["override_label"] == "verified"
    assert "Physical deed" in data["override_reason"]

    # Verify audit log recorded the action
    audit_entry = db_session.query(AuditLog).filter(AuditLog.action == "override_document_label").first()
    assert audit_entry is not None
    assert audit_entry.actor == "Officer Sharma"
    assert audit_entry.details["system_label"] == "possible_tampering"
    assert audit_entry.details["new_label"] == "verified"


def test_queue_sorting_and_filters(client, db_session):
    """Officer queue returns submitted/in_review apps, sorts by risk descending, and supports filters."""
    inst = Institution(id=5, name="Filter Test Inst", trust_name="Trust 5", state="Karnataka")
    db_session.add(inst)
    db_session.commit()

    # App 1: High risk (75.0), submitted
    app1 = Application(id=51, institution_id=5, application_type="new_institution", status="submitted", risk_score=75.0, risk_band="high", label="possible_tampering")
    # App 2: Low risk (15.0), in_review
    app2 = Application(id=52, institution_id=5, application_type="extension_of_approval", status="in_review", risk_score=15.0, risk_band="low", label="verified")
    # App 3: Draft (should NOT appear in default queue)
    app3 = Application(id=53, institution_id=5, application_type="new_institution", status="draft", risk_score=50.0, risk_band="medium", label="inconsistent")
    # App 4: Resubmission linked to App 1, medium risk (45.0), submitted
    app4 = Application(id=54, institution_id=5, application_type="new_institution", status="submitted", parent_application_id=51, risk_score=45.0, risk_band="medium", label="needs_verification")

    db_session.add_all([app1, app2, app3, app4])
    db_session.commit()

    # Default queue
    res = client.get("/officer/queue")
    assert res.status_code == 200
    queue = res.json()
    assert len(queue) == 3  # app1, app2, app4 (app3 draft excluded)
    # Sorted by risk descending: app1 (75.0), app4 (45.0), app2 (15.0)
    assert queue[0]["id"] == 51
    assert queue[1]["id"] == 54
    assert queue[2]["id"] == 52

    # Check resubmission flag
    app4_item = next(item for item in queue if item["id"] == 54)
    assert app4_item["is_resubmission"] is True
    assert app4_item["parent_application_id"] == 51

    # Filter by band=high
    res_high = client.get("/officer/queue?band=high")
    assert res_high.status_code == 200
    assert len(res_high.json()) == 1
    assert res_high.json()[0]["id"] == 51

    # Filter by state=submitted
    res_sub = client.get("/officer/queue?state=submitted")
    assert res_sub.status_code == 200
    assert len(res_sub.json()) == 2  # 51 and 54

    # Filter by application_type=extension_of_approval
    res_type = client.get("/officer/queue?application_type=extension_of_approval")
    assert res_type.status_code == 200
    assert len(res_type.json()) == 1
    assert res_type.json()[0]["id"] == 52


def test_officer_decision_and_audit(client, db_session):
    """Decision endpoint updates status to approved/rejected/deficiency_sent and logs audit."""
    inst = Institution(id=6, name="Decision Inst", trust_name="Trust 6", state="Gujarat")
    app = Application(id=60, institution_id=6, application_type="new_institution", status="submitted")
    db_session.add_all([inst, app])
    db_session.commit()

    res = client.post(
        "/officer/applications/60/decision",
        headers={"X-Demo-User": "Officer Patel"},
        json={"decision": "approve", "comments": "All compliance norms verified."},
    )
    assert res.status_code == 200
    assert res.json()["new_status"] == "approved"

    db_session.refresh(app)
    assert app.status == "approved"

    audit_entry = db_session.query(AuditLog).filter(AuditLog.action == "officer_decision").first()
    assert audit_entry is not None
    assert audit_entry.actor == "Officer Patel"
    assert audit_entry.details["decision"] == "approve"
