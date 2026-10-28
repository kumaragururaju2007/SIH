import pytest
import yaml
import shutil
from pathlib import Path
from app.services.rules_engine import validate_all_configs
from app.config import settings


def test_valid_consistency_rules_pass_validation():
    """Verify default configurations validate successfully without errors."""
    summary = validate_all_configs()
    assert summary["consistency_rules_count"] >= 4


def setup_mock_config_dir(tmp_path: Path, consistency_rules_dict: dict) -> Path:
    """Helper to set up a mock config directory with full required structure."""
    real_dir = Path(settings.CONFIG_DIR)
    
    # Copy document_types, application_types, and per-document rules
    shutil.copytree(real_dir / "document_types", tmp_path / "document_types")
    shutil.copytree(real_dir / "rules", tmp_path / "rules")
    shutil.copy(real_dir / "application_types.yaml", tmp_path / "application_types.yaml")

    # Set up consistency folder
    consistency_dir = tmp_path / "consistency"
    consistency_dir.mkdir(parents=True)
    shutil.copy(real_dir / "consistency" / "name_normalization.yaml", consistency_dir / "name_normalization.yaml")

    # Write target consistency_rules.yaml
    rule_file = consistency_dir / "consistency_rules.yaml"
    with open(rule_file, "w", encoding="utf-8") as f:
        yaml.dump(consistency_rules_dict, f)

    return tmp_path


def test_invalid_relation_rejected(tmp_path):
    """Unknown relation in consistency rule YAML must raise ValueError with clear message."""
    invalid_rule = {
        "consistency_rules": [
            {
                "id": "XDOC-INVALID-REL",
                "description": "Rule with invalid relation",
                "kind": "name",
                "left": "land_document.owner_name",
                "right": "trust_registration.trust_name",
                "relation": "some_unsupported_relation",
                "severity_on_conflict": "high",
                "thresholds": {"match_min": 85, "partial_min": 70},
            }
        ]
    }

    mock_dir = setup_mock_config_dir(tmp_path, invalid_rule)

    with pytest.raises(ValueError, match="unknown relation 'some_unsupported_relation'"):
        validate_all_configs(mock_dir)


def test_unknown_document_type_rejected(tmp_path):
    """Unknown document type in left or right must raise ValueError naming the unknown doc type."""
    invalid_rule = {
        "consistency_rules": [
            {
                "id": "XDOC-UNKNOWN-DOC",
                "description": "Rule with unknown doc type",
                "kind": "name",
                "left": "alien_doc.owner_name",
                "right": "trust_registration.trust_name",
                "relation": "equals",
                "severity_on_conflict": "high",
            }
        ]
    }

    mock_dir = setup_mock_config_dir(tmp_path, invalid_rule)

    with pytest.raises(ValueError, match="unknown document_type 'alien_doc'"):
        validate_all_configs(mock_dir)


def test_unknown_field_rejected(tmp_path):
    """Unknown field in existing doc type must raise ValueError naming the field."""
    invalid_rule = {
        "consistency_rules": [
            {
                "id": "XDOC-UNKNOWN-FIELD",
                "description": "Rule with unknown field",
                "kind": "name",
                "left": "land_document.nonexistent_field_xyz",
                "right": "trust_registration.trust_name",
                "relation": "equals",
                "severity_on_conflict": "high",
            }
        ]
    }

    mock_dir = setup_mock_config_dir(tmp_path, invalid_rule)

    with pytest.raises(ValueError, match="unknown field 'nonexistent_field_xyz'"):
        validate_all_configs(mock_dir)
