import os
import re
import json
from datetime import datetime, date
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Any, List, Optional, Tuple, Set

import yaml
from pydantic import BaseModel, Field, ValidationError
from simpleeval import SimpleEval, FeatureNotAvailable, FunctionNotDefined, NameNotDefined, InvalidExpression

from app.config import settings
from app.schemas import RuleOutcome


class ConfigValidationError(ValueError):
    """Raised when rule or application configurations are malformed or invalid."""
    pass


class RuleDefinition(BaseModel):
    id: str
    document_type: str
    description: str
    condition: str
    severity: str = Field(pattern="^(low|medium|high)$")
    message: str
    clause: str = "Handbook clause: <to be mapped to the current handbook edition>"
    required_fields: List[str]
    version: str = "1.0.0"
    applies_to: Optional[List[str]] = None


# Recognized aliases between manifest and document schemas
FIELD_ALIASES = {
    "registration_date": ["registered_date"],
    "registered_date": ["registration_date"],
    "trustees": ["trustee_names"],
    "trustee_names": ["trustees"],
}


def to_date_obj(val: Any) -> Optional[date]:
    """Convert string or datetime to date object for safe comparison."""
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        val_clean = val.strip()[:10]
        try:
            return datetime.strptime(val_clean, "%Y-%m-%d").date()
        except ValueError:
            for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
                try:
                    return datetime.strptime(val_clean, fmt).date()
                except ValueError:
                    pass
    return None


def fn_present(val: Any) -> bool:
    """Helper function: checks if a value is present, non-null, and non-empty."""
    if val is None:
        return False
    if isinstance(val, str):
        return len(val.strip()) > 0
    if isinstance(val, (list, tuple, dict, set)):
        return len(val) > 0
    return True


def fn_days_between(date_a: Any, date_b: Any) -> int:
    """Helper function: returns integer days between date_a and date_b (date_b - date_a)."""
    da = to_date_obj(date_a)
    db = to_date_obj(date_b)
    if da is None or db is None:
        raise ValueError(f"days_between requires valid dates, got {date_a} and {date_b}")
    return (db - da).days


def fn_len(val: Any) -> int:
    """Helper function: safe length of string, list, or JSON list."""
    if val is None:
        return 0
    if isinstance(val, (list, tuple, dict, set)):
        return len(val)
    if isinstance(val, str):
        if val.strip().startswith("["):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return len(parsed)
            except Exception:
                pass
        return len(val)
    return len(str(val))


class SafeTemplateDict(dict):
    """Dictionary that returns '[N/A]' for missing keys during string formatting."""
    def __missing__(self, key):
        return f"[{key}]"


def render_message(template: str, context: Dict[str, Any]) -> str:
    """Safely render message template with support for object attribute access (e.g. app.submission_date)."""
    try:
        # Wrap context in SafeTemplateDict
        return template.format_map(SafeTemplateDict(context))
    except Exception:
        # Fallback simple regex replacement
        out = template
        for k, v in context.items():
            if isinstance(v, SimpleNamespace):
                for sub_k, sub_v in vars(v).items():
                    out = out.replace(f"{{{k}.{sub_k}}}", str(sub_v))
            else:
                out = out.replace(f"{{{k}}}", str(v))
        return out


def create_safe_evaluator(names: Dict[str, Any]) -> SimpleEval:
    """Create a strictly locked-down SimpleEval instance."""
    s = SimpleEval()
    s.operators = SimpleEval().operators
    s.functions = {
        "present": fn_present,
        "days_between": fn_days_between,
        "len": fn_len,
    }
    s.names = names
    return s


def load_rules(config_dir: Optional[Path] = None) -> Dict[str, List[RuleDefinition]]:
    """Load all YAML rules from configs/rules/ directory grouped by document_type."""
    if config_dir is None:
        config_dir = Path(settings.CONFIG_DIR)

    rules_dir = config_dir / "rules"
    rules_by_doc: Dict[str, List[RuleDefinition]] = {}

    if not rules_dir.exists():
        return rules_by_doc

    for yaml_file in sorted(rules_dir.glob("*.yaml")):
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        rules_list = data.get("rules", [])
        if not isinstance(rules_list, list):
            raise ConfigValidationError(f"Invalid rule file '{yaml_file.name}': 'rules' must be a list.")

        for r in rules_list:
            try:
                rule_def = RuleDefinition(**r)
            except ValidationError as ve:
                raise ConfigValidationError(f"Malformed rule in '{yaml_file.name}': {ve}")

            doc_type = rule_def.document_type
            if doc_type not in rules_by_doc:
                rules_by_doc[doc_type] = []
            rules_by_doc[doc_type].append(rule_def)

    return rules_by_doc


def validate_all_configs(config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Validate all document_types, application_types, and rules YAML files."""
    if config_dir is None:
        config_dir = Path(settings.CONFIG_DIR)

    doc_types_dir = config_dir / "document_types"
    app_types_file = config_dir / "application_types.yaml"
    rules_dir = config_dir / "rules"

    known_doc_types: Dict[str, Set[str]] = {}
    known_app_types: Set[str] = set()

    # 1. Validate Document Types
    if not doc_types_dir.exists():
        raise ConfigValidationError(f"Document types directory not found at: {doc_types_dir}")

    for doc_file in doc_types_dir.glob("*.yaml"):
        with open(doc_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        dtype = data.get("document_type")
        if not dtype:
            raise ConfigValidationError(f"Document type file '{doc_file.name}' missing 'document_type' key.")

        fields = data.get("fields", [])
        if not isinstance(fields, list):
            raise ConfigValidationError(f"Document type '{dtype}' has invalid 'fields' definition.")

        field_names = set()
        for fld in fields:
            fname = fld.get("name")
            if not fname:
                raise ConfigValidationError(f"Document type '{dtype}' has field with missing 'name'.")
            field_names.add(fname)
            for alias in FIELD_ALIASES.get(fname, []):
                field_names.add(alias)

        known_doc_types[dtype] = field_names

    # 2. Validate Application Types
    if not app_types_file.exists():
        raise ConfigValidationError(f"application_types.yaml not found at: {app_types_file}")

    with open(app_types_file, "r", encoding="utf-8") as f:
        app_data = yaml.safe_load(f) or {}

    app_types = app_data.get("application_types", {})
    if not isinstance(app_types, dict):
        raise ConfigValidationError("application_types.yaml must define an 'application_types' mapping.")

    for atype, atype_spec in app_types.items():
        known_app_types.add(atype)
        req_docs = atype_spec.get("required_documents", [])
        for rdoc in req_docs:
            if rdoc not in known_doc_types:
                raise ConfigValidationError(
                    f"Application type '{atype}' requires unknown document type '{rdoc}'. "
                    f"Known types: {list(known_doc_types.keys())}"
                )

    # 3. Validate Rules
    if not rules_dir.exists():
        raise ConfigValidationError(f"Rules directory not found at: {rules_dir}")

    total_rules = 0
    rule_ids: Set[str] = set()

    for rule_file in rules_dir.glob("*.yaml"):
        with open(rule_file, "r", encoding="utf-8") as f:
            rdata = yaml.safe_load(f) or {}

        rules_list = rdata.get("rules", [])
        if not isinstance(rules_list, list):
            raise ConfigValidationError(f"Rule file '{rule_file.name}' must contain a 'rules' list.")

        for r_entry in rules_list:
            try:
                rule_def = RuleDefinition(**r_entry)
            except ValidationError as ve:
                raise ConfigValidationError(f"Malformed rule in '{rule_file.name}': {ve}")

            if rule_def.id in rule_ids:
                raise ConfigValidationError(f"Duplicate rule id '{rule_def.id}' detected in '{rule_file.name}'.")
            rule_ids.add(rule_def.id)

            if rule_def.document_type not in known_doc_types:
                raise ConfigValidationError(
                    f"Rule '{rule_def.id}' references unknown document_type '{rule_def.document_type}'."
                )

            valid_fields = known_doc_types[rule_def.document_type]
            for rf in rule_def.required_fields:
                if rf not in valid_fields:
                    raise ConfigValidationError(
                        f"Rule '{rule_def.id}' specifies unknown required field '{rf}' for document_type '{rule_def.document_type}'."
                    )

            if rule_def.applies_to:
                for app_t in rule_def.applies_to:
                    if app_t not in known_app_types:
                        raise ConfigValidationError(
                            f"Rule '{rule_def.id}' references unknown application_type '{app_t}' in applies_to."
                        )

            # Test condition syntax with simpleeval
            test_names = {rf: "mock" for rf in rule_def.required_fields}
            test_names["app"] = SimpleNamespace(submission_date=date.today(), min_area_sqm=10000.0)
            evaluator = create_safe_evaluator(test_names)
            try:
                evaluator.parse(rule_def.condition)
            except Exception as pe:
                raise ConfigValidationError(f"Syntax error in rule '{rule_def.id}' condition '{rule_def.condition}': {pe}")

            total_rules += 1

    # 4. Validate Cross-Document Consistency Rules
    consistency_file = config_dir / "consistency" / "consistency_rules.yaml"
    consistency_count = 0
    if consistency_file.exists():
        with open(consistency_file, "r", encoding="utf-8") as f:
            cdata = yaml.safe_load(f) or {}

        c_rules = cdata.get("consistency_rules", [])
        if not isinstance(c_rules, list):
            raise ConfigValidationError("consistency_rules.yaml must contain a 'consistency_rules' list.")

        allowed_relations = {"equals", "any_of", "date_before_or_equal"}
        allowed_kinds = {"name", "id", "date_order", "address"}

        for crule in c_rules:
            cid = crule.get("id")
            if not cid:
                raise ConfigValidationError("Consistency rule missing 'id'.")

            rel = crule.get("relation")
            if rel not in allowed_relations:
                raise ConfigValidationError(
                    f"Consistency rule '{cid}' has unknown relation '{rel}'. Allowed: {sorted(list(allowed_relations))}"
                )

            kind = crule.get("kind")
            if kind not in allowed_kinds:
                raise ConfigValidationError(
                    f"Consistency rule '{cid}' has unknown kind '{kind}'. Allowed: {sorted(list(allowed_kinds))}"
                )

            def check_target(t_str: str):
                parts = t_str.split(".", 1)
                if len(parts) != 2:
                    raise ConfigValidationError(
                        f"Consistency rule '{cid}' target '{t_str}' must be formatted as 'doc_type.field' or 'application.institution_name'."
                    )
                dtype, fname = parts[0].strip(), parts[1].strip()
                if dtype == "application":
                    if fname != "institution_name":
                        raise ConfigValidationError(
                            f"Consistency rule '{cid}' references unknown application field '{fname}'."
                        )
                else:
                    if dtype not in known_doc_types:
                        raise ConfigValidationError(
                            f"Consistency rule '{cid}' references unknown document_type '{dtype}'. Known: {sorted(list(known_doc_types.keys()))}"
                        )
                    if fname not in known_doc_types[dtype]:
                        raise ConfigValidationError(
                            f"Consistency rule '{cid}' references unknown field '{fname}' for document_type '{dtype}'."
                        )

            check_target(crule.get("left", ""))
            r_targets = crule.get("right", [])
            if isinstance(r_targets, str):
                r_targets = [r_targets]
            for rt in r_targets:
                check_target(rt)

            consistency_count += 1

    return {
        "status": "valid",
        "document_types": list(known_doc_types.keys()),
        "application_types": list(known_app_types),
        "total_rules": total_rules,
        "consistency_rules_count": consistency_count,
    }


def evaluate_rule(
    rule: RuleDefinition,
    extracted_fields: Dict[str, Any],
    app_params: Dict[str, Any],
    document_id: Optional[int] = None,
) -> RuleOutcome:
    """Evaluate a single rule against extracted document fields and application parameters."""
    doc_id = document_id

    # 1. Check required fields for presence, nullness, and needs_verification
    for rf in rule.required_fields:
        field_obj = extracted_fields.get(rf)

        # Check aliases if missing
        if field_obj is None:
            for alias in FIELD_ALIASES.get(rf, []):
                if alias in extracted_fields:
                    field_obj = extracted_fields[alias]
                    break

        if field_obj is None:
            return RuleOutcome(
                rule_id=rule.id,
                document_id=doc_id,
                document_type=rule.document_type,
                status="not_evaluable",
                passed=False,
                severity=rule.severity,
                message=f"Field '{rf}' required by rule {rule.id} is missing from extracted document fields.",
                clause=rule.clause,
                evidence={"reason": "missing_field", "field": rf, "document_id": doc_id},
            )

        # Get values from ExtractedField model or dict
        if hasattr(field_obj, "value_normalized"):
            val_norm = field_obj.value_normalized
            val_orig = field_obj.value_original
            needs_verif = field_obj.needs_verification
            conf = getattr(field_obj, "confidence", 1.0)
        elif isinstance(field_obj, dict):
            val_norm = field_obj.get("value_normalized")
            val_orig = field_obj.get("value_original")
            needs_verif = field_obj.get("needs_verification", False)
            conf = field_obj.get("confidence", 1.0)
        else:
            val_norm = str(field_obj)
            val_orig = str(field_obj)
            needs_verif = False
            conf = 1.0

        if not val_norm and not val_orig:
            return RuleOutcome(
                rule_id=rule.id,
                document_id=doc_id,
                document_type=rule.document_type,
                status="not_evaluable",
                passed=False,
                severity=rule.severity,
                message=f"Field '{rf}' required by rule {rule.id} has null or empty value.",
                clause=rule.clause,
                evidence={"reason": "null_field", "field": rf, "document_id": doc_id},
            )

        if needs_verif:
            return RuleOutcome(
                rule_id=rule.id,
                document_id=doc_id,
                document_type=rule.document_type,
                status="not_evaluable",
                passed=False,
                severity=rule.severity,
                message=f"Field '{rf}' is flagged needs_verification (confidence {conf:.2f}); cannot evaluate rule deterministically.",
                clause=rule.clause,
                evidence={"reason": "needs_verification", "field": rf, "confidence": conf, "document_id": doc_id},
            )

    # 2. Build Evaluation Context
    eval_names: Dict[str, Any] = {}
    formatting_context: Dict[str, Any] = {}

    for fname, f_entry in extracted_fields.items():
        if hasattr(f_entry, "value_normalized"):
            v_norm = f_entry.value_normalized
            v_orig = f_entry.value_original
        elif isinstance(f_entry, dict):
            v_norm = f_entry.get("value_normalized")
            v_orig = f_entry.get("value_original")
        else:
            v_norm = str(f_entry)
            v_orig = str(f_entry)

        raw_val = v_norm if v_norm is not None else v_orig
        typed_val: Any = raw_val

        # Attempt date conversion
        d_val = to_date_obj(raw_val)
        if d_val is not None:
            typed_val = d_val
        else:
            # Attempt float conversion
            try:
                typed_val = float(raw_val)
            except (ValueError, TypeError):
                # Attempt JSON list conversion
                if isinstance(raw_val, str) and raw_val.strip().startswith("["):
                    try:
                        parsed = json.loads(raw_val)
                        if isinstance(parsed, list):
                            typed_val = parsed
                    except Exception:
                        pass

        eval_names[fname] = typed_val
        formatting_context[fname] = raw_val

        # Populate aliases in context
        for alias in FIELD_ALIASES.get(fname, []):
            eval_names[alias] = typed_val
            formatting_context[alias] = raw_val

    # Special handling for trustees count in formatting
    if "trustees" in eval_names and isinstance(eval_names["trustees"], list):
        formatting_context["trustees_count"] = len(eval_names["trustees"])
    elif "trustee_names" in eval_names and isinstance(eval_names["trustee_names"], list):
        formatting_context["trustees_count"] = len(eval_names["trustee_names"])

    # Prepare app context
    app_dict = dict(app_params)
    app_sub_date = to_date_obj(app_dict.get("submission_date")) or date.today()
    app_dict["submission_date"] = app_sub_date
    app_obj = SimpleNamespace(**app_dict)

    eval_names["app"] = app_obj
    formatting_context["app"] = app_obj

    # 3. Evaluate Condition
    evaluator = create_safe_evaluator(eval_names)
    try:
        outcome_bool = bool(evaluator.eval(rule.condition))
    except Exception as eval_err:
        return RuleOutcome(
            rule_id=rule.id,
            document_id=doc_id,
            document_type=rule.document_type,
            status="not_evaluable",
            passed=False,
            severity=rule.severity,
            message=f"Evaluation error for rule {rule.id}: {eval_err}",
            clause=rule.clause,
            evidence={"reason": "eval_error", "error": str(eval_err), "document_id": doc_id},
        )

    # 4. Construct Passed/Failed Outcome
    evidence_fields = {
        rf: (
            extracted_fields[rf].value_normalized
            if hasattr(extracted_fields.get(rf), "value_normalized")
            else str(eval_names.get(rf))
        )
        for rf in rule.required_fields
        if rf in extracted_fields or rf in eval_names
    }

    evidence = {
        "fields": evidence_fields,
        "document_id": doc_id,
        "parameters": {k: str(v) for k, v in app_dict.items()},
    }

    if outcome_bool:
        return RuleOutcome(
            rule_id=rule.id,
            document_id=doc_id,
            document_type=rule.document_type,
            status="passed",
            passed=True,
            severity=rule.severity,
            message=f"Satisfied: {rule.description}.",
            clause=rule.clause,
            evidence=evidence,
        )
    else:
        rendered_msg = render_message(rule.message, formatting_context)
        return RuleOutcome(
            rule_id=rule.id,
            document_id=doc_id,
            document_type=rule.document_type,
            status="failed",
            passed=False,
            severity=rule.severity,
            message=rendered_msg,
            clause=rule.clause,
            evidence=evidence,
        )
