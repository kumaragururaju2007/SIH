import pytest
import yaml
from pathlib import Path

from app.services.rules_engine import validate_all_configs, ConfigValidationError


def create_minimal_configs(base_dir: Path):
    """Helper to set up a valid base config structure."""
    doc_types = base_dir / "document_types"
    rules_dir = base_dir / "rules"
    doc_types.mkdir(parents=True, exist_ok=True)
    rules_dir.mkdir(parents=True, exist_ok=True)

    # Valid doc type
    with open(doc_types / "fire_safety_certificate.yaml", "w", encoding="utf-8") as f:
        yaml.dump({
            "document_type": "fire_safety_certificate",
            "display_name": "Fire Safety Certificate",
            "fields": [
                {"name": "valid_until", "type": "date"},
                {"name": "issued_date", "type": "date"},
            ]
        }, f)

    # Valid app types
    with open(base_dir / "application_types.yaml", "w", encoding="utf-8") as f:
        yaml.dump({
            "application_types": {
                "new_institution": {
                    "required_documents": ["fire_safety_certificate"],
                    "parameters": {"min_area_sqm": 10000.0}
                }
            }
        }, f)

    # Valid rule
    with open(rules_dir / "fire_safety_certificate.yaml", "w", encoding="utf-8") as f:
        yaml.dump({
            "rules": [
                {
                    "id": "FIRE-EXPIRY",
                    "document_type": "fire_safety_certificate",
                    "description": "Must not be expired",
                    "condition": "valid_until >= app.submission_date",
                    "severity": "high",
                    "message": "Certificate expired",
                    "required_fields": ["valid_until"],
                }
            ]
        }, f)


def test_valid_config_passes(tmp_path):
    """Verify clean base configuration passes validation without error."""
    create_minimal_configs(tmp_path)
    res = validate_all_configs(tmp_path)
    assert res["status"] == "valid"
    assert res["total_rules"] == 1


def test_malformed_rule_missing_fields_rejected(tmp_path):
    """Verify rule missing required schema field (e.g. condition) is rejected."""
    create_minimal_configs(tmp_path)
    bad_rule_file = tmp_path / "rules" / "fire_safety_certificate.yaml"
    with open(bad_rule_file, "w", encoding="utf-8") as f:
        yaml.dump({
            "rules": [
                {
                    "id": "FIRE-BROKEN",
                    "document_type": "fire_safety_certificate",
                    "description": "Missing condition and severity",
                    # condition is missing!
                    "required_fields": ["valid_until"],
                }
            ]
        }, f)

    with pytest.raises(ConfigValidationError) as exc:
        validate_all_configs(tmp_path)
    assert "Malformed rule" in str(exc.value)


def test_unknown_document_type_rejected(tmp_path):
    """Verify rule referencing unknown document type is rejected."""
    create_minimal_configs(tmp_path)
    bad_rule_file = tmp_path / "rules" / "unknown_doc.yaml"
    with open(bad_rule_file, "w", encoding="utf-8") as f:
        yaml.dump({
            "rules": [
                {
                    "id": "UNKNOWN-RULE",
                    "document_type": "completely_unknown_certificate",
                    "description": "Rule on non-existent document type",
                    "condition": "1 == 1",
                    "severity": "low",
                    "message": "Notice",
                    "required_fields": [],
                }
            ]
        }, f)

    with pytest.raises(ConfigValidationError) as exc:
        validate_all_configs(tmp_path)
    assert "unknown document_type" in str(exc.value)


def test_unknown_field_in_rule_rejected(tmp_path):
    """Verify rule specifying unknown field in required_fields is rejected."""
    create_minimal_configs(tmp_path)
    bad_rule_file = tmp_path / "rules" / "fire_safety_certificate.yaml"
    with open(bad_rule_file, "w", encoding="utf-8") as f:
        yaml.dump({
            "rules": [
                {
                    "id": "FIRE-UNKNOWN-FIELD",
                    "document_type": "fire_safety_certificate",
                    "description": "Requires non-existent field",
                    "condition": "fake_nonexistent_field == 'yes'",
                    "severity": "high",
                    "message": "Error",
                    "required_fields": ["fake_nonexistent_field"],
                }
            ]
        }, f)

    with pytest.raises(ConfigValidationError) as exc:
        validate_all_configs(tmp_path)
    assert "unknown required field" in str(exc.value)


def test_invalid_syntax_condition_rejected(tmp_path):
    """Verify rule condition with invalid expression syntax is rejected."""
    create_minimal_configs(tmp_path)
    bad_rule_file = tmp_path / "rules" / "fire_safety_certificate.yaml"
    with open(bad_rule_file, "w", encoding="utf-8") as f:
        yaml.dump({
            "rules": [
                {
                    "id": "FIRE-SYNTAX-ERROR",
                    "document_type": "fire_safety_certificate",
                    "description": "Malformed Python expression",
                    "condition": "valid_until >= >= and",
                    "severity": "high",
                    "message": "Error",
                    "required_fields": ["valid_until"],
                }
            ]
        }, f)

    with pytest.raises(ConfigValidationError) as exc:
        validate_all_configs(tmp_path)
    assert "Syntax error" in str(exc.value)
