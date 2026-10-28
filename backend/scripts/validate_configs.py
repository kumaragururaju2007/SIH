import sys
from pathlib import Path

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.services.rules_engine import validate_all_configs, ConfigValidationError


def main():
    config_dir = Path(settings.CONFIG_DIR)
    if not config_dir.exists():
        candidate = BACKEND_DIR / "configs"
        if candidate.exists():
            config_dir = candidate

    print("============================================================")
    print(" AICTE Document Validation System - Config Validator")
    print(f" Validating directory: {config_dir}")
    print("============================================================\n")

    try:
        summary = validate_all_configs(config_dir)
        print("[SUCCESS] All configurations and deterministic rules are valid!")
        print(f"- Document Types ({len(summary['document_types'])}): {', '.join(summary['document_types'])}")
        print(f"- Application Types ({len(summary['application_types'])}): {', '.join(summary['application_types'])}")
        print(f"- Per-Document Rules Loaded: {summary['total_rules']}")
        print(f"- Cross-Document Consistency Rules Loaded: {summary.get('consistency_rules_count', 0)}")
        print("\nAll rule conditions, schema references, and parameters verified.")
        return 0
    except ConfigValidationError as cve:
        print(f"[ERROR] Config Validation Failed:\n{cve}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[ERROR] Unexpected error during config validation:\n{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
