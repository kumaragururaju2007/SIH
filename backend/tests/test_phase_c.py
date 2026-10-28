import hashlib
import json
from pathlib import Path
import pytest
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
    ExtractedField,
    RuleResult,
    ConsistencyResult,
    AuthResult,
)
from app.services.auth.duplicates import check_duplicates

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
FIXES_DIR = ROOT_DIR / "data" / "fixes"


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


def test_original_results_hash_identical_before_and_after_draft_recheck(client, db_session):
    """The original application and all its results must remain untouched after a draft recheck."""
    inst = Institution(id=9, name="Heritage Institute", trust_name="Heritage Trust", state="Rajasthan")
    parent = Application(id=90, institution_id=9, application_type="new_institution", status="deficiency_sent", risk_score=55.0, label="inconsistent")
    doc_land = Document(id=901, application_id=90, doc_type="land_document", file_path="d901.png", sha256="h901", ocr_text="Land deed content", label="inconsistent")
    doc_trust = Document(id=902, application_id=90, doc_type="trust_registration", file_path="d902.png", sha256="h902", ocr_text="Trust deed content", label="verified")
    rr = RuleResult(application_id=90, document_id=901, rule_id="LAND-AREA", status="failed", passed=False, severity="high", message="Area deficit")
    cr = ConsistencyResult(application_id=90, rule_id="XDOC-OWNER-TRUST", field="owner_name", doc_a_id=901, doc_b_id=902, status="conflict", outcome="conflict", severity="high", message="Conflict")
    db_session.add_all([inst, parent, doc_land, doc_trust, rr, cr])
    db_session.commit()

    # Capture snapshot of parent application state
    def get_parent_snapshot():
        p = db_session.get(Application, 90)
        p_docs = [(d.id, d.doc_type, d.sha256, d.label) for d in p.documents]
        p_rrs = [(r.id, r.rule_id, r.status, r.passed) for r in p.rule_results]
        p_crs = [(c.id, c.rule_id, c.status, c.message) for c in p.consistency_results]
        snapshot_dict = {
            "status": p.status,
            "risk_score": p.risk_score,
            "label": p.label,
            "docs": p_docs,
            "rule_results": p_rrs,
            "consistency_results": p_crs,
        }
        return hashlib.sha256(json.dumps(snapshot_dict, sort_keys=True).encode("utf-8")).hexdigest()

    before_hash = get_parent_snapshot()

    # 1. Create draft copy
    res_draft = client.post("/applications/90/drafts")
    assert res_draft.status_code == 201
    draft_id = res_draft.json()["id"]

    # 2. Recheck draft copy
    res_recheck = client.post(f"/drafts/{draft_id}/recheck")
    assert res_recheck.status_code == 200

    # 3. Verify parent application snapshot hash is byte-for-byte identical
    after_hash = get_parent_snapshot()
    assert before_hash == after_hash, "Parent application or results were mutated during draft recheck!"


def test_a05_fix_resolves_xdoc_owner_trust_and_bad_fix_keeps_remaining(client, db_session):
    """A05 draft with corrected land document resolves XDOC-OWNER-TRUST; bad fix keeps it as remaining."""
    inst = Institution(id=15, name="Vanguard Academy", trust_name="Vanguard Educational Trust", state="Gujarat")
    parent = Application(id=150, institution_id=15, application_type="new_institution", status="deficiency_sent", risk_score=60.0, label="inconsistent")
    doc_land = Document(id=1501, application_id=150, doc_type="land_document", file_path="orig_land.png", sha256="ol", ocr_text="Registered Land Deed", label="inconsistent")
    doc_trust = Document(id=1502, application_id=150, doc_type="trust_registration", file_path="trust.png", sha256="ot", ocr_text="Vanguard Educational Trust Deed", label="verified")
    
    ef_trust = ExtractedField(
        document_id=1502,
        name="trust_name",
        value_original="Vanguard Educational Trust",
        value_normalized="vanguard educational trust",
    )
    ef_land_orig = ExtractedField(
        document_id=1501,
        name="owner_name",
        value_original="Rameshwar Prasad Sharma",
        value_normalized="rameshwar prasad sharma",
    )

    cr = ConsistencyResult(
        application_id=150,
        rule_id="XDOC-OWNER-TRUST",
        field="owner_name",
        doc_a_id=1501,
        doc_b_id=1502,
        value_a="Rameshwar Prasad Sharma",
        value_b="Vanguard Educational Trust",
        status="conflict",
        outcome="conflict",
        severity="high",
        message="Owner name does not match trust",
    )
    db_session.add_all([inst, parent, doc_land, doc_trust, ef_trust, ef_land_orig, cr])
    db_session.commit()

    # --- Scenario 1: Good Fix ---
    res_draft1 = client.post("/applications/150/drafts")
    assert res_draft1.status_code == 201
    draft1_id = res_draft1.json()["id"]

    good_land_file = FIXES_DIR / "A05_corrected_land.png"
    assert good_land_file.exists(), f"Missing fixture {good_land_file}"

    with open(good_land_file, "rb") as f:
        up_good = client.post(
            f"/drafts/{draft1_id}/documents",
            files={"file": ("land_document.png", f, "image/png")},
        )
    assert up_good.status_code == 201
    assert up_good.json()["doc_type"] == "land_document"

    # Recheck draft
    client.post(f"/drafts/{draft1_id}/recheck")

    # Get comparison
    comp1 = client.get(f"/drafts/{draft1_id}/comparison").json()
    resolved_ids = [it["id"] for it in comp1["resolved_issues"]]
    remaining_ids = [it["id"] for it in comp1["remaining_issues"]]

    assert "CONSISTENCY:XDOC-OWNER-TRUST" in resolved_ids, "XDOC-OWNER-TRUST should be resolved by corrected land document"
    assert "CONSISTENCY:XDOC-OWNER-TRUST" not in remaining_ids

    # --- Scenario 2: Bad Fix (still mismatches) ---
    res_draft2 = client.post("/applications/150/drafts")
    assert res_draft2.status_code == 201
    draft2_id = res_draft2.json()["id"]

    bad_land_file = FIXES_DIR / "A05_bad_fix_land.png"
    assert bad_land_file.exists(), f"Missing fixture {bad_land_file}"

    with open(bad_land_file, "rb") as f:
        up_bad = client.post(
            f"/drafts/{draft2_id}/documents",
            files={"file": ("land_document.png", f, "image/png")},
        )
    assert up_bad.status_code == 201

    # Recheck draft 2
    client.post(f"/drafts/{draft2_id}/recheck")

    comp2 = client.get(f"/drafts/{draft2_id}/comparison").json()
    remaining_ids_2 = [it["id"] for it in comp2["remaining_issues"]]
    assert "CONSISTENCY:XDOC-OWNER-TRUST" in remaining_ids_2, "Bad fix should leave XDOC-OWNER-TRUST as remaining"


def test_a03_fix_resolves_fire_expiry_and_comparison_counts(client, db_session):
    """A03 resolves FIRE-EXPIRY and before/after comparison counts are accurate."""
    inst = Institution(id=13, name="National Institute", trust_name="National Trust", state="Tamil Nadu")
    parent = Application(id=130, institution_id=13, application_type="new_institution", status="deficiency_sent", risk_score=40.0, label="inconsistent")
    doc_fire = Document(id=1301, application_id=130, doc_type="fire_safety_certificate", file_path="f13.png", sha256="f13", ocr_text="Fire safety certificate content")
    rr = RuleResult(
        application_id=130,
        document_id=1301,
        rule_id="FIRE-EXPIRY",
        status="failed",
        passed=False,
        severity="high",
        message="Fire certificate validity expired on 2024-04-15",
    )
    db_session.add_all([inst, parent, doc_fire, rr])
    db_session.commit()

    # Create draft
    res_draft = client.post("/applications/130/drafts")
    assert res_draft.status_code == 201
    draft_id = res_draft.json()["id"]

    # Upload corrected fire certificate
    good_fire_file = FIXES_DIR / "A03_corrected_fire.png"
    assert good_fire_file.exists()

    with open(good_fire_file, "rb") as f:
        up_fire = client.post(
            f"/drafts/{draft_id}/documents",
            files={"file": ("fire_safety_certificate.png", f, "image/png")},
        )
    assert up_fire.status_code == 201

    # Recheck
    client.post(f"/drafts/{draft_id}/recheck")

    comp = client.get(f"/drafts/{draft_id}/comparison").json()
    resolved_ids = [it["id"] for it in comp["resolved_issues"]]
    assert "RULE:FIRE-EXPIRY:fire_safety_certificate" in resolved_ids
    assert comp["resolved_count"] >= 1
    assert "2 remaining" in comp["summary_sentence"]


def test_resubmission_queued_with_parent_link_and_no_duplicate(client, db_session):
    """Resubmission appears in officer queue with parent link and does not trigger duplicate flags against parent."""
    inst = Institution(id=16, name="Resubmission College", trust_name="Trust 16", state="Goa")
    parent = Application(id=160, institution_id=16, application_type="new_institution", status="deficiency_sent", risk_score=50.0, label="inconsistent")
    doc_fire = Document(
        id=1601,
        application_id=160,
        doc_type="fire_safety_certificate",
        file_path="f16.png",
        sha256="hash1601_abcdef1234567890abcdef1234567890abcdef1234567890abcdef123456",
        phash="ffff0000ffff0000",
        ocr_text="Fire safety certificate content",
    )
    db_session.add_all([inst, parent, doc_fire])
    db_session.commit()

    # Create draft and submit resubmission
    res_draft = client.post("/applications/160/drafts")
    draft_id = res_draft.json()["id"]

    # Recheck draft
    client.post(f"/drafts/{draft_id}/recheck")

    # Check duplicate check ignores parent
    draft_doc = db_session.query(Document).filter(Document.application_id == draft_id).first()
    assert draft_doc is not None
    dup_res = check_duplicates(db_session, draft_doc)
    assert dup_res["result"] == "ok"
    assert dup_res["evidence"]["duplicate_found"] is False, "Draft must NOT flag identical parent documents as duplicates!"

    # Submit resubmission
    sub_res = client.post(f"/drafts/{draft_id}/submit-resubmission")
    assert sub_res.status_code == 200
    assert sub_res.json()["is_resubmission"] is True
    assert sub_res.json()["parent_application_id"] == 160

    # Parent status became 'superseded'
    db_session.refresh(parent)
    assert parent.status == "superseded"

    # Verify queue contains the resubmission with parent link
    queue_res = client.get("/officer/queue")
    assert queue_res.status_code == 200
    queue_items = queue_res.json()
    resub_item = next(it for it in queue_items if it["id"] == draft_id)
    assert resub_item["is_resubmission"] is True
    assert resub_item["parent_application_id"] == 160
