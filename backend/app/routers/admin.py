from pathlib import Path
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.schemas import ConfigResponse
from app.services.rules_engine import validate_all_configs, load_rules, ConfigValidationError
from app.services.completeness import get_application_types_config
from app.services.consistency import load_consistency_rules

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/config", response_model=ConfigResponse)
def get_all_configurations():
    """List loaded document types, application types, rules, and versions."""
    try:
        summary = validate_all_configs()
        rules_by_doc = load_rules()
        app_types = get_application_types_config()
        c_rules = load_consistency_rules()

        serializable_rules: Dict[str, List[Dict[str, Any]]] = {}
        for dtype, r_list in rules_by_doc.items():
            serializable_rules[dtype] = [r.model_dump() for r in r_list]

        return ConfigResponse(
            document_types=summary["document_types"],
            application_types=app_types,
            rules_count=summary["total_rules"],
            rules_by_type=serializable_rules,
            consistency_rules_count=len(c_rules),
            consistency_rules=[cr.model_dump() for cr in c_rules],
        )
    except ConfigValidationError as cve:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configuration error: {str(cve)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load configurations: {str(e)}",
        )


@router.post("/config/reload")
def reload_configurations():
    """Reload all YAML configurations without restarting the server."""
    try:
        summary = validate_all_configs()
        return {
            "status": "ok",
            "message": "Configurations successfully reloaded.",
            "summary": summary,
        }
    except ConfigValidationError as cve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to reload configurations due to validation error: {str(cve)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error reloading configurations: {str(e)}",
        )
