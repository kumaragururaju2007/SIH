import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Application, Document
from app.schemas import RuleOutcome


def get_application_types_config(config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Load application types specification from YAML."""
    if config_dir is None:
        config_dir = Path(settings.CONFIG_DIR)

    app_types_file = config_dir / "application_types.yaml"
    if not app_types_file.exists():
        candidate = Path(__file__).resolve().parent.parent.parent / "configs" / "application_types.yaml"
        if candidate.exists():
            app_types_file = candidate

    if not app_types_file.exists():
        return {}

    with open(app_types_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data.get("application_types", {})


def get_application_type_spec(application_type: str, config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Retrieve specification for a specific application type."""
    types_map = get_application_types_config(config_dir)
    return types_map.get(application_type, {})


def check_completeness(db: Session, application_id: int, config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Check document completeness for an application.
    Returns:
      {
        required: [...],
        present: [...],
        missing: [...],
        unrecognized: [...],
        duplicates_of_type: [...],
        missing_findings: [...],
        active_documents: {doc_type: Document}
      }
    """
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise ValueError(f"Application with ID {application_id} not found.")

    app_spec = get_application_type_spec(application.application_type, config_dir=config_dir)
    required_docs: List[str] = list(app_spec.get("required_documents", []))

    # Query all uploaded documents for the application
    documents = db.query(Document).filter(Document.application_id == application_id).all()

    unrecognized_doc_ids: List[int] = []
    docs_by_type: Dict[str, List[Document]] = {}

    for doc in documents:
        if not doc.doc_type or doc.doc_type.strip() == "":
            unrecognized_doc_ids.append(doc.id)
        else:
            dtype = doc.doc_type.strip()
            if dtype not in docs_by_type:
                docs_by_type[dtype] = []
            docs_by_type[dtype].append(doc)

    duplicates_of_type: List[str] = []
    active_documents: Dict[str, Document] = {}

    for dtype, docs_list in docs_by_type.items():
        if len(docs_list) > 1:
            duplicates_of_type.append(dtype)
            # Use the document with highest classification / OCR confidence
            best_doc = max(
                docs_list,
                key=lambda d: (d.ocr_confidence if d.ocr_confidence is not None else 0.0, d.id),
            )
            active_documents[dtype] = best_doc
        else:
            active_documents[dtype] = docs_list[0]

    present: List[str] = sorted(list(active_documents.keys()))
    missing: List[str] = [req for req in required_docs if req not in active_documents]

    missing_findings: List[RuleOutcome] = []
    for m_type in missing:
        display_name = m_type.replace("_", " ")
        missing_findings.append(
            RuleOutcome(
                rule_id=f"MISSING:{m_type}",
                document_id=None,
                document_type=m_type,
                status="failed",
                passed=False,
                severity="high",
                message=f"Mandatory document '{m_type}' is missing. Please upload the official {display_name}.",
                clause="Handbook clause: <to be mapped to the current handbook edition>",
                evidence={
                    "required": True,
                    "application_type": application.application_type,
                    "doc_type": m_type,
                },
            )
        )

    return {
        "application_id": application_id,
        "application_type": application.application_type,
        "is_complete": len(missing) == 0,
        "required": required_docs,
        "present": present,
        "missing": missing,
        "unrecognized": unrecognized_doc_ids,
        "duplicates_of_type": sorted(duplicates_of_type),
        "missing_findings": missing_findings,
        "active_documents": active_documents,
    }
