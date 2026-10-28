"""AICTE Document Authentication and Forensics Package."""
from app.services.auth.config import load_auth_config
from app.services.auth.duplicates import check_duplicates
from app.services.auth.metadata import check_metadata
from app.services.auth.forensics import analyze_tampering
from app.services.auth.qr_check import verify_qr_code
from app.services.auth.registry import verify_registry, RegistryClient, MockRegistryClient, get_registry_client

__all__ = [
    "load_auth_config",
    "check_duplicates",
    "check_metadata",
    "analyze_tampering",
    "verify_qr_code",
    "verify_registry",
    "RegistryClient",
    "MockRegistryClient",
    "get_registry_client",
]
