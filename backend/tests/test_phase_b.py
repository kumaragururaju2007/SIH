import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app as fastapi_app
from app.models import (
    Institution,
    Application,
    Document,
    RuleResult,
    ConsistencyResult,
    AuthResult,
    DeficiencyReport,
    AuditLog,
)
from app.services.deficiency import (
    load_deficiency_templates,
    scan_for_forbidden_phrases,
    build_deficiency_items,
    generate_deficiency_report,
    FORBIDDEN_PHRASES,
)

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


def test_wording_safeguards_scan_all_templates():
    """Wording safeguard: scan every deficiency template for prohibited phrases."""
    templates_en = load_deficiency_templates("en")
    templates_hi = load_deficiency_templates("hi")

    assert len(templates_en) > 0, "English templates must not be empty"
    assert len(templates_hi) > 0, "Hindi templates must not be empty"

    def check_recursive(obj, path=""):
        if isinstance(obj, str):
            found = scan_for_forbidden_phrases(obj)
            assert not found, f"Forbidden phrase(s) {found} found at {path}: '{obj}'"
        elif isinstance(obj, dict):
            for k, v in obj.items():
                check_recursive(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                check_recursive(v, f"{path}[{i}]")

    check_recursive(templates_en, "templates_en")
    check_recursive(templates_hi, "templates_hi")


def test_hindi_templates_cover_same_keys_as_english():
    """Hindi templates must cover the exact same keys and subfields as English."""
    tmpl_en = load_deficiency_templates("en")
    tmpl_hi = load_deficiency_templates("hi")

    assert set(tmpl_en.keys()) == set(tmpl_hi.keys()), (
        f"Key parity mismatch between EN and HI: {set(tmpl_en.keys()) ^ set(tmpl_hi.keys())}"
    )

    required_fields = {"title", "what_failed", "why", "what_to_resubmit", "clause"}
    for key, data in tmpl_en.items():
        assert required_fields.issubset(data.keys()), f"English key '{key}' missing required fields"
        assert required_fields.issubset(tmpl_hi[key].keys()), f"Hindi key '{key}' missing required fields"


def test_unapproved_report_cannot_be_sent(client, db_session):
    """An unapproved deficiency report cannot be sent; only approved reports can be sent."""
    inst = Institution(id=7, name="Scrutiny Test Inst", trust_name="Trust 7", state="Kerala")
    app = Application(id=70, institution_id=7, application_type="new_institution", status="submitted")
    doc = Document(id=701, application_id=70, doc_type="fire_safety_certificate", file_path="f7.png", sha256="s7")
    rr = RuleResult(application_id=70, document_id=701, rule_id="FIRE-EXPIRY", status="failed", passed=False, severity="high", message="Expired fire certificate")
    db_session.add_all([inst, app, doc, rr])
    db_session.commit()

    # 1. Generate report (status: draft)
    gen_res = client.post("/officer/applications/70/deficiency-report/generate")
    assert gen_res.status_code == 200
    report_data = gen_res.json()
    assert report_data["status"] == "draft"

    # 2. Attempt to send unapproved draft -> must fail with HTTP 400
    send_res_fail = client.post("/officer/applications/70/deficiency-report/send")
    assert send_res_fail.status_code == 400
    assert "Only approved reports can be sent" in send_res_fail.json()["detail"]

    # 3. Institution attempts to view draft -> must fail with HTTP 403
    view_inst_fail = client.get(
        "/applications/70/deficiency-report",
        headers={"X-Demo-User": "Institution Representative", "X-Demo-Role": "institution"},
    )
    assert view_inst_fail.status_code == 403

    # Officer can view draft
    view_officer_ok = client.get(
        "/applications/70/deficiency-report",
        headers={"X-Demo-User": "Officer Kulkarni", "X-Demo-Role": "officer"},
    )
    assert view_officer_ok.status_code == 200

    # 4. Approve report
    appr_res = client.post(
        "/officer/applications/70/deficiency-report/approve",
        headers={"X-Demo-User": "Officer Kulkarni"},
    )
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "approved"
    assert appr_res.json()["approved_by"] == "Officer Kulkarni"

    # 5. Now send approved report -> must succeed
    send_res_ok = client.post(
        "/officer/applications/70/deficiency-report/send",
        headers={"X-Demo-User": "Officer Kulkarni"},
    )
    assert send_res_ok.status_code == 200
    assert send_res_ok.json()["status"] == "sent"
    assert send_res_ok.json()["application_status"] == "deficiency_sent"

    # Verify audit log entry for notification
    notif_audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "send_deficiency_notification")
        .first()
    )
    assert notif_audit is not None
    assert notif_audit.details["recipient_institution"] == "Scrutiny Test Inst"

    # 6. Institution can now view sent report
    view_inst_ok = client.get(
        "/applications/70/deficiency-report",
        headers={"X-Demo-User": "Institution Representative", "X-Demo-Role": "institution"},
    )
    assert view_inst_ok.status_code == 200
    assert view_inst_ok.json()["status"] == "sent"


def test_deficiency_reports_a02_a05_a11_items_and_clauses(db_session):
    """A02, A05, A11 reports contain right items with clauses, actual values, and neutral wording."""
    inst = Institution(id=8, name="Demo University", trust_name="Apex Foundation", state="Tamil Nadu")
    db_session.add(inst)
    db_session.commit()

    # --- Scenario A02: Missing document + Rule failure ---
    app2 = Application(id=2, institution_id=8, application_type="new_institution", status="submitted")
    doc2_land = Document(id=201, application_id=2, doc_type="land_document", file_path="d2.png", sha256="s2")
    # Land area failed
    rr2_land = RuleResult(
        application_id=2,
        document_id=201,
        rule_id="LAND-AREA",
        status="failed",
        passed=False,
        severity="high",
        message="Certified area 7500 sqm is below required 10000 sqm",
        clause="Handbook clause: <to be mapped to the current handbook edition - Land Norms Section 3.1>",
        evidence={"land_area_sqm": 7500, "min_required": 10000},
    )
    db_session.add_all([app2, doc2_land, rr2_land])
    db_session.commit()

    report2 = generate_deficiency_report(db_session, 2)
    items2 = report2.content["items"]
    # Should have missing fire_safety_certificate & trust_registration, plus LAND-AREA rule failure
    missing_items = [it for it in items2 if it["category"] == "missing_document"]
    rule_items = [it for it in items2 if it["category"] == "rule_failure"]
    assert len(missing_items) >= 2, "Expected missing documents in A02"
    assert len(rule_items) >= 1, "Expected rule failure item in A02"
    land_item = next(it for it in rule_items if "LAND" in it["item_id"])
    assert "7500" in land_item["why"]
    assert "Handbook clause:" in land_item["clause"]
    assert "genuine" in land_item["what_to_resubmit"].lower()

    # --- Scenario A05: Cross-document owner/trust discrepancy ---
    app5 = Application(id=5, institution_id=8, application_type="new_institution", status="submitted")
    doc5_land = Document(id=501, application_id=5, doc_type="land_document", file_path="l5.png", sha256="l5")
    doc5_trust = Document(id=502, application_id=5, doc_type="trust_registration", file_path="t5.png", sha256="t5")
    cr5 = ConsistencyResult(
        application_id=5,
        rule_id="XDOC-OWNER-TRUST",
        field="owner_name",
        doc_a_id=501,
        doc_b_id=502,
        value_a="Dr. Ramesh Rao",
        value_b="Apex Educational Trust",
        status="conflict",
        outcome="conflict",
        severity="high",
        message="Owner name does not match trust",
        clause="Handbook clause: <to be mapped to current handbook edition - Title Continuity Section 3.2>",
    )
    db_session.add_all([app5, doc5_land, doc5_trust, cr5])
    db_session.commit()

    report5 = generate_deficiency_report(db_session, 5)
    items5 = report5.content["items"]
    owner_item = next(it for it in items5 if it["category"] == "consistency")
    assert "Dr. Ramesh Rao" in owner_item["why"]
    assert "Apex Educational Trust" in owner_item["why"]
    assert "Handbook clause:" in owner_item["clause"]
    assert "genuine" in owner_item["what_to_resubmit"].lower()

    # --- Scenario A11: Tampering signal with neutral wording ---
    app11 = Application(id=11, institution_id=8, application_type="new_institution", status="submitted")
    doc11 = Document(id=1101, application_id=11, doc_type="land_document", file_path="l11.png", sha256="l11")
    ar11_tamp = AuthResult(
        document_id=1101,
        check_type="tampering",
        result="high_suspicion",
        probability=0.89,
        evidence={"regions": [{"box": [10, 10, 50, 50]}], "score": 0.89},
    )
    db_session.add_all([app11, doc11, ar11_tamp])
    db_session.commit()

    report11 = generate_deficiency_report(db_session, 11)
    items11 = report11.content["items"]
    tamp_item = next(it for it in items11 if it["category"] == "authenticity")
    # Verify neutral, non-accusing wording
    assert "the document could not be verified and shows inconsistencies; please provide a genuine copy from the issuing authority" in tamp_item["what_failed"].lower()
    # Confirm no forbidden accusation words
    assert not scan_for_forbidden_phrases(tamp_item["what_failed"])
    assert not scan_for_forbidden_phrases(tamp_item["why"])
    assert "Handbook clause:" in tamp_item["clause"]
    assert "89.0%" in tamp_item["why"]
