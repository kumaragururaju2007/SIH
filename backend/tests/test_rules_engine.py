import json
import pytest
from datetime import date
from types import SimpleNamespace

from app.services.rules_engine import (
    RuleDefinition,
    evaluate_rule,
    render_message,
    create_safe_evaluator,
    load_rules,
)
from simpleeval import FeatureNotAvailable, FunctionNotDefined, NameNotDefined


def test_malicious_expressions_rejected():
    """Verify simpleeval rejects imports, class/attribute walking, and dangerous builtins."""
    names = {"x": 10, "app": SimpleNamespace(submission_date=date(2025, 6, 1))}
    evaluator = create_safe_evaluator(names)

    # 1. Attribute walking via __class__
    with pytest.raises(FeatureNotAvailable):
        evaluator.eval("().__class__")

    with pytest.raises(FeatureNotAvailable):
        evaluator.eval("'test'.__class__.__bases__")

    # 2. Imports
    with pytest.raises((FunctionNotDefined, FeatureNotAvailable)):
        evaluator.eval("__import__('os').system('whoami')")

    # 3. Arbitrary file opening
    with pytest.raises(FunctionNotDefined):
        evaluator.eval("open('secret.txt')")

    # 4. Exec / Eval
    with pytest.raises(FunctionNotDefined):
        evaluator.eval("eval('2 + 2')")


def test_fire_rules_pass_and_fail():
    """Test fire safety certificate rules pass on valid inputs and fail on violating inputs."""
    rules = load_rules()["fire_safety_certificate"]
    rules_map = {r.id: r for r in rules}
    app_params = {"submission_date": date(2025, 6, 1)}

    # Valid fire document fields
    valid_fields = {
        "certificate_number": {"value_normalized": "FS-2024-A01-901", "needs_verification": False},
        "issued_date": {"value_normalized": "2024-04-16", "needs_verification": False},
        "valid_until": {"value_normalized": "2026-04-15", "needs_verification": False},
    }

    # All should pass on valid fields
    for r_id in ("FIRE-EXPIRY", "FIRE-DATES-ORDER", "FIRE-ISSUED-NOT-FUTURE", "FIRE-NUMBER-PRESENT"):
        outcome = evaluate_rule(rules_map[r_id], valid_fields, app_params)
        assert outcome.status == "passed", f"{r_id} should pass on valid fields"
        assert outcome.passed is True

    # 1. FIRE-EXPIRY failure (expired before submission)
    expired_fields = dict(valid_fields)
    expired_fields["valid_until"] = {"value_normalized": "2024-04-15", "needs_verification": False}
    outcome_exp = evaluate_rule(rules_map["FIRE-EXPIRY"], expired_fields, app_params)
    assert outcome_exp.status == "failed"
    assert outcome_exp.passed is False
    assert "2024-04-15" in outcome_exp.message
    assert "2025-06-01" in outcome_exp.message

    # 2. FIRE-DATES-ORDER failure (issued after valid_until)
    inverted_fields = dict(valid_fields)
    inverted_fields["issued_date"] = {"value_normalized": "2027-01-01", "needs_verification": False}
    outcome_order = evaluate_rule(rules_map["FIRE-DATES-ORDER"], inverted_fields, app_params)
    assert outcome_order.status == "failed"
    assert "2027-01-01" in outcome_order.message

    # 3. FIRE-ISSUED-NOT-FUTURE failure
    future_fields = dict(valid_fields)
    future_fields["issued_date"] = {"value_normalized": "2025-08-01", "needs_verification": False}
    outcome_fut = evaluate_rule(rules_map["FIRE-ISSUED-NOT-FUTURE"], future_fields, app_params)
    assert outcome_fut.status == "failed"

    # 4. FIRE-NUMBER-PRESENT failure
    no_num_fields = dict(valid_fields)
    no_num_fields["certificate_number"] = {"value_normalized": "", "value_original": "", "needs_verification": False}
    outcome_num = evaluate_rule(rules_map["FIRE-NUMBER-PRESENT"], no_num_fields, app_params)
    # Since value is empty, it returns not_evaluable for null field
    assert outcome_num.status == "not_evaluable"


def test_land_rules_pass_and_fail():
    """Test land document rules pass and fail appropriately."""
    rules = load_rules()["land_document"]
    rules_map = {r.id: r for r in rules}
    app_params = {"submission_date": date(2025, 6, 1), "min_area_sqm": 10000.0}

    valid_fields = {
        "registration_number": {"value_normalized": "LD-2021-A01-441", "needs_verification": False},
        "owner_name": {"value_normalized": "Apex Educational Foundation", "needs_verification": False},
        "plot_number": {"value_normalized": "Plot No. 91/A", "needs_verification": False},
        "area_sqm": {"value_normalized": "12500.0", "needs_verification": False},
        "registration_date": {"value_normalized": "2021-03-22", "needs_verification": False},
    }

    for r_id in ("LAND-AREA-MIN", "LAND-OWNER-PRESENT", "LAND-PLOT-PRESENT", "LAND-REG-DATE-NOT-FUTURE"):
        outcome = evaluate_rule(rules_map[r_id], valid_fields, app_params)
        assert outcome.status == "passed", f"{r_id} should pass"

    # LAND-AREA-MIN failure (6500 < 10000)
    low_area_fields = dict(valid_fields)
    low_area_fields["area_sqm"] = {"value_normalized": "6500.0", "needs_verification": False}
    outcome_area = evaluate_rule(rules_map["LAND-AREA-MIN"], low_area_fields, app_params)
    assert outcome_area.status == "failed"
    assert "6500" in outcome_area.message
    assert "10000" in outcome_area.message


def test_trust_rules_pass_and_fail():
    """Test trust registration certificate rules."""
    rules = load_rules()["trust_registration"]
    rules_map = {r.id: r for r in rules}
    app_params = {"submission_date": date(2025, 6, 1)}

    valid_fields = {
        "registration_number": {"value_normalized": "TR-2016-A01-702", "needs_verification": False},
        "trust_name": {"value_normalized": "Apex Educational Foundation", "needs_verification": False},
        "registered_date": {"value_normalized": "2016-11-14", "needs_verification": False},
        "trustees": {"value_normalized": json.dumps(["Arvind Sharma", "Meena Patel"]), "needs_verification": False},
    }

    for r_id in ("TRUST-REG-PRESENT", "TRUST-TRUSTEES-MIN", "TRUST-DATE-NOT-FUTURE"):
        outcome = evaluate_rule(rules_map[r_id], valid_fields, app_params)
        assert outcome.status == "passed", f"{r_id} should pass"

    # TRUST-TRUSTEES-MIN failure (1 trustee < 2)
    single_trustee_fields = dict(valid_fields)
    single_trustee_fields["trustees"] = {"value_normalized": json.dumps(["Solo Trustee"]), "needs_verification": False}
    outcome_t = evaluate_rule(rules_map["TRUST-TRUSTEES-MIN"], single_trustee_fields, app_params)
    assert outcome_t.status == "failed"
    assert "found 1" in outcome_t.message


def test_not_evaluable_conditions():
    """Verify rules return not_evaluable on missing, null, or needs_verification fields."""
    rules = load_rules()["land_document"]
    land_area_rule = next(r for r in rules if r.id == "LAND-AREA-MIN")
    app_params = {"submission_date": date(2025, 6, 1), "min_area_sqm": 10000.0}

    # 1. Missing field
    outcome_missing = evaluate_rule(land_area_rule, {}, app_params)
    assert outcome_missing.status == "not_evaluable"
    assert "missing" in outcome_missing.message.lower()

    # 2. Null field
    null_fields = {"area_sqm": {"value_normalized": None, "value_original": None, "needs_verification": False}}
    outcome_null = evaluate_rule(land_area_rule, null_fields, app_params)
    assert outcome_null.status == "not_evaluable"
    assert "null" in outcome_null.message.lower()

    # 3. Field flagged needs_verification
    unverified_fields = {"area_sqm": {"value_normalized": "12500.0", "needs_verification": True, "confidence": 0.55}}
    outcome_unverif = evaluate_rule(land_area_rule, unverified_fields, app_params)
    assert outcome_unverif.status == "not_evaluable"
    assert "needs_verification" in outcome_unverif.message


def test_rendered_message_contains_actual_values():
    """Verify error message template renders with actual field values and app params."""
    template = "Certificate expired on {valid_until}; submission date was {app.submission_date}."
    context = {
        "valid_until": "2024-04-15",
        "app": SimpleNamespace(submission_date=date(2025, 6, 1)),
    }
    rendered = render_message(template, context)
    assert "2024-04-15" in rendered
    assert "2025-06-01" in rendered
