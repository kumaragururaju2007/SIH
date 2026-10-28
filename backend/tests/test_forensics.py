from pathlib import Path
import pytest
from PIL import Image

from app.services.auth.forensics import analyze_tampering

def get_data_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "data" / "synthetic",
        Path(__file__).resolve().parent.parent / "data" / "synthetic",
        Path("../data/synthetic").resolve(),
        Path("data/synthetic").resolve(),
    ]
    for c in candidates:
        if c.exists() and (c / "A01").exists():
            return c
    return candidates[0]

DATA_DIR = get_data_dir()


def test_clean_image_scores_low():
    """A clean official document must produce a low tampering score and status 'ok'."""
    clean_path = DATA_DIR / "A01" / "fire_safety_certificate.png"
    if not clean_path.exists():
        pytest.skip(f"Synthetic document not found at {clean_path}")

    res = analyze_tampering(str(clean_path), app_id="A01", doc_id=101)
    assert res["result"] == "ok"
    assert res["probability"] < 0.35
    assert len(res["evidence"]["regions"]) == 0


def test_pasted_region_scores_high():
    """A document containing a pasted region at a lower JPEG quality must score high or suspicious."""
    tampered_path = DATA_DIR / "A06" / "fire_safety_certificate.png"
    if not tampered_path.exists():
        pytest.skip(f"Synthetic document not found at {tampered_path}")

    res = analyze_tampering(str(tampered_path), app_id="A06", doc_id=601)
    assert res["result"] in ("suspicious", "high_suspicion")
    assert res["probability"] >= 0.35
    assert len(res["evidence"]["regions"]) >= 1


def test_uniformly_blurred_noisy_image_is_low_quality_scan():
    """A uniformly blurred noisy scan (A10) must be flagged as 'low_quality_scan' and NOT as tampered."""
    poor_scan_path = DATA_DIR / "A10" / "fire_safety_certificate.png"
    if not poor_scan_path.exists():
        pytest.skip(f"Synthetic document not found at {poor_scan_path}")

    res = analyze_tampering(str(poor_scan_path), app_id="A10", doc_id=1001)
    assert res["result"] == "low_quality_scan"
    assert res["evidence"]["is_degraded"] is True
    # Tampering score is suppressed
    assert res["probability"] < 0.35
