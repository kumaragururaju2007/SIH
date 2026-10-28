import pytest
import yaml
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Institution, Application, Document
from app.services.completeness import check_completeness


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    inst = Institution(name="Test Polytechnic", state="KA", trust_name="Test Trust")
    session.add(inst)
    session.commit()

    yield session
    session.close()


def test_new_application_type_via_config_only(db_session, tmp_path):
    """
    Verify that adding a completely new application type via YAML configuration file
    works dynamically without any Python code modifications.
    """
    # Create temporary config directory
    custom_config_dir = tmp_path / "configs"
    custom_config_dir.mkdir(parents=True, exist_ok=True)

    # Define brand new application type requiring only fire_safety_certificate
    app_types_data = {
        "application_types": {
            "vocational_skill_center": {
                "name": "Vocational Skill Development Center",
                "code": "vocational_skill_center",
                "description": "Short-term technical skill center approval",
                "required_documents": [
                    "fire_safety_certificate"
                ],
                "parameters": {
                    "certificate_min_validity_days": 30
                }
            }
        }
    }

    yaml_path = custom_config_dir / "application_types.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(app_types_data, f)

    # Create application of new type
    app = Application(
        institution_id=1,
        application_type="vocational_skill_center",
    )
    db_session.add(app)
    db_session.commit()

    # 1. Before uploading fire_safety_certificate: incomplete, missing fire_safety_certificate
    comp_initial = check_completeness(db_session, app.id, config_dir=custom_config_dir)
    assert comp_initial["is_complete"] is False
    assert comp_initial["required"] == ["fire_safety_certificate"]
    assert comp_initial["missing"] == ["fire_safety_certificate"]
    assert len(comp_initial["missing_findings"]) == 1
    assert comp_initial["missing_findings"][0].rule_id == "MISSING:fire_safety_certificate"

    # 2. Upload fire_safety_certificate only
    doc = Document(
        application_id=app.id,
        doc_type="fire_safety_certificate",
        file_path="storage/uploads/fire.png",
        sha256="hash_fire_vocational",
        ocr_confidence=0.94,
    )
    db_session.add(doc)
    db_session.commit()

    # 3. Re-check completeness: should be 100% complete with no other documents required!
    comp_final = check_completeness(db_session, app.id, config_dir=custom_config_dir)
    assert comp_final["is_complete"] is True
    assert comp_final["missing"] == []
    assert comp_final["present"] == ["fire_safety_certificate"]
    assert len(comp_final["missing_findings"]) == 0
