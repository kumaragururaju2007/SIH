import json
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from app.schemas import SyntheticManifest
from scripts.generate_synthetic import generate_dataset


def test_synthetic_data_generator(tmp_path):
    """
    Runs the synthetic data generator into a temp directory and validates:
    1. Exactly 13 applications exist (A01 - A13).
    2. A02 has only 2 documents (missing trust_registration).
    3. A08's fire certificate hash equals A01's.
    4. A06 and A07 are marked tampered in the manifest.
    5. manifest.json validates against the Pydantic schema.
    6. contact_sheet.png and registry_mock.json are generated properly.
    """
    manifest = generate_dataset(output_dir=tmp_path, seed=42)

    # 1. 13 applications exist
    assert len(manifest.applications) == 13, f"Expected 13 applications, got {len(manifest.applications)}"
    app_ids = [app.app_id for app in manifest.applications]
    expected_ids = [f"A{i:02d}" for i in range(1, 14)]
    assert app_ids == expected_ids

    # 2. A02 has only 2 documents
    app_map = {app.app_id: app for app in manifest.applications}
    a02 = app_map["A02"]
    assert len(a02.documents) == 2, f"Expected 2 documents for A02, got {len(a02.documents)}"
    a02_doc_types = {d.doc_type for d in a02.documents}
    assert "trust_registration" not in a02_doc_types
    assert "fire_safety_certificate" in a02_doc_types
    assert "land_document" in a02_doc_types

    # 3. A08's fire certificate hash equals A01's
    a01 = app_map["A01"]
    a08 = app_map["A08"]
    a01_fire = next(d for d in a01.documents if d.doc_type == "fire_safety_certificate")
    a08_fire = next(d for d in a08.documents if d.doc_type == "fire_safety_certificate")
    assert a08_fire.sha256 == a01_fire.sha256, "A08 fire certificate hash must match A01 fire certificate hash"

    # 4. A06 and A07 are marked tampered in the manifest
    a06 = app_map["A06"]
    a06_fire = next(d for d in a06.documents if d.doc_type == "fire_safety_certificate")
    assert a06_fire.tampered is True, "A06 fire certificate must be marked tampered"
    assert a06_fire.tampered_bbox is not None, "A06 fire certificate must have tampered_bbox"
    assert len(a06_fire.tampered_bbox) == 4

    a07 = app_map["A07"]
    a07_land = next(d for d in a07.documents if d.doc_type == "land_document")
    assert a07_land.tampered is True, "A07 land document must be marked tampered"
    assert a07_land.tampered_bbox is not None, "A07 land document must have tampered_bbox"
    assert len(a07_land.tampered_bbox) == 4

    # 5. manifest.json validates against Pydantic schema
    manifest_file = tmp_path / "manifest.json"
    assert manifest_file.exists(), "manifest.json file must exist"
    with open(manifest_file, "r", encoding="utf-8") as f:
        raw_manifest_content = f.read()

    validated_manifest = SyntheticManifest.model_validate_json(raw_manifest_content)
    assert len(validated_manifest.applications) == 13

    # 6. registry_mock.json and contact_sheet.png exist
    registry_file = tmp_path / "registry_mock.json"
    assert registry_file.exists()
    with open(registry_file, "r", encoding="utf-8") as f:
        registry_data = json.load(f)
    assert "fire_safety_certificates" in registry_data
    assert "land_records" in registry_data
    assert "trust_registry" in registry_data

    # A13 fire certificate must be absent from registry mock
    a13_fire_cert_no = f"FS-2024-A13-901"
    assert a13_fire_cert_no not in registry_data["fire_safety_certificates"]

    contact_sheet = tmp_path / "contact_sheet.png"
    assert contact_sheet.exists()
    assert contact_sheet.stat().st_size > 0
