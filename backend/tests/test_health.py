import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import Institution, Application, AuditLog

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Create all tables in a fresh in-memory SQLite DB, yield session, drop on teardown."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """TestClient that uses the test DB session override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_check(client):
    """Check that GET /health returns status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_post_applications_creates_audit_entry(client, db_session):
    """Check that POST /applications creates an application and writes an audit log entry."""
    # Pre-create an institution
    institution = Institution(
        name="Test Institute of Technology",
        state="Delhi",
        trust_name="Test Education Trust",
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)

    # Call POST /applications
    payload = {
        "institution_id": institution.id,
        "application_type": "extension_of_approval",
    }
    response = client.post("/applications", json=payload)
    assert response.status_code == 201

    app_data = response.json()
    assert app_data["institution_id"] == institution.id
    assert app_data["application_type"] == "extension_of_approval"
    assert app_data["status"] == "draft"
    assert "id" in app_data

    app_id = app_data["id"]

    # Verify Application exists in DB
    saved_app = db_session.get(Application, app_id)
    assert saved_app is not None
    assert saved_app.application_type == "extension_of_approval"

    # Verify that an AuditLog entry was written
    audit_entry = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity == f"application:{app_id}",
            AuditLog.action == "create_application",
        )
        .first()
    )
    assert audit_entry is not None
    assert audit_entry.actor == "system"
    assert audit_entry.details["institution_id"] == institution.id
    assert audit_entry.details["application_id"] == app_id
    assert audit_entry.details["status"] == "draft"


def test_get_application(client, db_session):
    """Check GET /applications/{id} returns the created application or 404."""
    # Pre-create institution and application
    institution = Institution(
        name="Apex Technical Campus",
        state="Karnataka",
        trust_name="Apex Trust",
    )
    db_session.add(institution)
    db_session.commit()

    application = Application(
        institution_id=institution.id,
        application_type="new_institute",
        status="draft",
    )
    db_session.add(application)
    db_session.commit()
    db_session.refresh(application)

    # Retrieve existing application
    response = client.get(f"/applications/{application.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == application.id
    assert data["institution_id"] == institution.id
    assert data["application_type"] == "new_institute"

    # Non-existent application returns 404
    missing_response = client.get("/applications/99999")
    assert missing_response.status_code == 404


def test_officer_queue(client):
    """Check GET /officer/queue returns an empty list."""
    response = client.get("/officer/queue")
    assert response.status_code == 200
    assert response.json() == []
