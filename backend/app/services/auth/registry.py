import os
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Document, ExtractedField
from app.services.normalize import normalize_id, normalize_date, normalize_name, normalize_number
from app.services.matching import calculate_name_score, compare_ids

logger = logging.getLogger(__name__)


class RegistryClient(ABC):
    """Abstract interface for government and municipal record registry verification.
    Real state/central API connectors (e.g. DigiLocker, e-District, Land Records API)
    can replace the mock client by implementing this interface.
    """

    @abstractmethod
    def lookup(self, doc_type: str, number: str) -> Tuple[Optional[Dict[str, Any]], bool]:
        """Lookup a document by type and unique identifier.
        
        Returns:
            (record_dict, registry_available)
            - If registry is offline/disabled: (None, False)
            - If record exists: (dict, True)
            - If record does not exist: (None, True)
        """
        pass


class MockRegistryClient(RegistryClient):
    """Mock registry reading from data/synthetic/registry_mock.json."""

    def __init__(self, mock_path: Optional[Path] = None):
        self.mock_path = mock_path or self._resolve_mock_path()
        self._cached_data: Optional[Dict[str, Any]] = None

    def _resolve_mock_path(self) -> Path:
        backend_dir = Path(__file__).resolve().parent.parent.parent.parent
        candidates = [
            backend_dir / "data" / "synthetic" / "registry_mock.json",
            backend_dir.parent / "data" / "synthetic" / "registry_mock.json",
            Path("data/synthetic/registry_mock.json").resolve(),
        ]
        for c in candidates:
            if c.exists():
                return c
        return candidates[0]

    def _load_data(self) -> Dict[str, Any]:
        if self._cached_data is None:
            if self.mock_path.exists():
                try:
                    with open(self.mock_path, "r", encoding="utf-8") as f:
                        self._cached_data = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to load registry mock from {self.mock_path}: {e}")
                    self._cached_data = {}
            else:
                self._cached_data = {}
        return self._cached_data

    def is_available(self) -> bool:
        """Check if registry is enabled via settings or environment variable."""
        env_val = os.getenv("REGISTRY_ENABLED")
        if env_val is not None:
            return env_val.lower() in ("true", "1", "yes")
        return bool(getattr(settings, "REGISTRY_ENABLED", True))

    def lookup(self, doc_type: str, number: str) -> Tuple[Optional[Dict[str, Any]], bool]:
        if not self.is_available():
            return None, False

        data = self._load_data()
        norm_number = normalize_id(number)

        # Map doc_type to registry partition
        if doc_type == "fire_safety_certificate":
            partition = data.get("fire_safety_certificates", {})
        elif doc_type == "land_document":
            partition = data.get("land_records", {})
        elif doc_type == "trust_registration":
            partition = data.get("trust_registry", {})
        else:
            partition = {}

        # Search normalized IDs
        for reg_key, reg_val in partition.items():
            if normalize_id(reg_key) == norm_number:
                return dict(reg_val), True

        return None, True


_default_registry_client: Optional[RegistryClient] = None


def get_registry_client() -> RegistryClient:
    """Return configured RegistryClient instance."""
    global _default_registry_client
    if _default_registry_client is None:
        _default_registry_client = MockRegistryClient()
    return _default_registry_client


def verify_registry(
    db: Session,
    document: Document,
    client: Optional[RegistryClient] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Verify document extracted fields against official registry record.
    
    Outcomes:
    - 'match': all present registry fields match document extracted fields
    - 'mismatch': one or more fields differ (lists differing fields with both values)
    - 'not_found': record not present in registry
    - 'unavailable': registry service is offline or disabled (REGISTRY_ENABLED=false)
    """
    reg_client = client or get_registry_client()

    # Identify document unique ID
    doc_id_val: Optional[str] = None
    target_field = "certificate_number" if document.doc_type == "fire_safety_certificate" else "registration_number"

    extracted_dict: Dict[str, str] = {}
    for ef in document.extracted_fields:
        if ef.value_normalized:
            extracted_dict[ef.name] = ef.value_normalized
            if ef.name in ("certificate_number", "registration_number") and not doc_id_val:
                doc_id_val = ef.value_normalized

    if not doc_id_val or not document.doc_type:
        return {
            "result": "unavailable",
            "probability": None,
            "signals": [],
            "evidence": {
                "status": "unavailable",
                "details": "Document missing classification doc_type or extracted identifier.",
            },
        }

    # Query registry
    record, available = reg_client.lookup(document.doc_type, doc_id_val)

    if not available:
        return {
            "result": "unavailable",
            "probability": None,
            "signals": ["registry_service_unavailable"],
            "evidence": {
                "status": "unavailable",
                "details": "Government Registry service is currently unavailable or disabled via REGISTRY_ENABLED.",
                "doc_type": document.doc_type,
                "document_id": doc_id_val,
            },
        }

    if record is None:
        return {
            "result": "not_found",
            "probability": None,
            "signals": ["registry_record_not_found"],
            "evidence": {
                "status": "not_found",
                "details": f"No official record found in registry for {document.doc_type} with ID '{doc_id_val}'.",
                "doc_type": document.doc_type,
                "document_id": doc_id_val,
            },
        }

    # Compare fields present in registry record
    differing_fields: List[Dict[str, Any]] = []
    matched_fields: List[str] = []

    for reg_field, reg_val in record.items():
        if reg_field in ("status", "registration_number", "certificate_number"):
            continue

        # Map field name variations
        doc_field = reg_field
        if reg_field == "registration_date" and "registered_date" in extracted_dict:
            doc_field = "registered_date"
        elif reg_field == "registered_date" and "registration_date" in extracted_dict:
            doc_field = "registration_date"

        if doc_field not in extracted_dict:
            continue

        ext_val = extracted_dict[doc_field]

        # Field-specific normalization comparisons
        is_match = False
        if "date" in reg_field or reg_field == "valid_until":
            is_match = (normalize_date(str(reg_val)) == normalize_date(ext_val))
        elif reg_field == "area_sqm":
            reg_num, _ = normalize_number(str(reg_val))
            ext_num, _ = normalize_number(ext_val)
            is_match = (reg_num is not None and ext_num is not None and abs(reg_num - ext_num) < 1.0)
        elif "name" in reg_field or reg_field == "issuing_authority":
            score, status, _ = calculate_name_score(str(reg_val), str(ext_val), match_min=70.0, partial_min=50.0)
            is_match = (status in ("match", "partial") or normalize_name(str(reg_val)) == normalize_name(ext_val))
        elif "number" in reg_field or "id" in reg_field or reg_field in ("plot_number", "registration_number", "certificate_number"):
            score, status = compare_ids(str(reg_val), str(ext_val))
            is_match = (status in ("match", "partial") or normalize_id(str(reg_val)) == normalize_id(str(ext_val)))
        else:
            is_match = (str(reg_val).strip().lower() == str(ext_val).strip().lower() or normalize_name(str(reg_val)) == normalize_name(ext_val))

        if is_match:
            matched_fields.append(reg_field)
        else:
            differing_fields.append({
                "field": reg_field,
                "registry_value": reg_val,
                "extracted_value": ext_val,
            })

    if differing_fields:
        return {
            "result": "mismatch",
            "probability": None,
            "signals": ["registry_field_mismatch"],
            "evidence": {
                "status": "mismatch",
                "doc_type": document.doc_type,
                "document_id": doc_id_val,
                "registry_record": record,
                "differing_fields": differing_fields,
                "matched_fields": matched_fields,
                "details": f"Registry record found with {len(differing_fields)} field mismatch(es): "
                           + ", ".join(f"{d['field']} (registry: {d['registry_value']} vs extracted: {d['extracted_value']})" for d in differing_fields),
            },
        }

    return {
        "result": "match",
        "probability": None,
        "signals": [],
        "evidence": {
            "status": "match",
            "doc_type": document.doc_type,
            "document_id": doc_id_val,
            "registry_record": record,
            "matched_fields": matched_fields,
            "details": "All verified registry fields match extracted document fields.",
        },
    }
