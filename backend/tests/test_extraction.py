from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Institution, Application, Document, ExtractedField
from app.services.ocr import run_ocr, get_tesserocr_api, get_paddle_ocr_engine
from app.services.classify import classify
from app.services.extract import get_extractor
from app.services.pipeline import process_document

try:
    import pytesseract
except ImportError:
    pytesseract = None

# Check if an OCR engine is available
def is_ocr_available() -> bool:
    if get_tesserocr_api() is not None:
        return True
    if pytesseract is not None:
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            pass
    if get_paddle_ocr_engine() is not None:
        return True
    return False


OCR_AVAILABLE = is_ocr_available()
pytestmark = pytest.mark.skipif(not OCR_AVAILABLE, reason="Neither Tesseract nor PaddleOCR is available")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic" / "A01"


def test_extract_a01_fire_safety_certificate():
    img_path = DATA_DIR / "fire_safety_certificate.png"
    assert img_path.exists(), f"Synthetic document not found: {img_path}"

    ocr_res = run_ocr(str(img_path))
    assert ocr_res.text, "OCR text should not be empty"
    assert ocr_res.mean_confidence > 0.5, f"Low OCR confidence: {ocr_res.mean_confidence}"

    doc_type, conf, reasons = classify(ocr_res.text, file_name=img_path.name)
    assert doc_type == "fire_safety_certificate"

    extractor = get_extractor()
    fields = extractor.extract(ocr_res, doc_type)

    assert "certificate_number" in fields
    assert fields["certificate_number"].value_original is not None
    assert "FS" in fields["certificate_number"].value_original

    assert "valid_until" in fields
    assert fields["valid_until"].value_normalized is not None
    # Validate date format YYYY-MM-DD
    assert len(fields["valid_until"].value_normalized) == 10


def test_extract_a01_land_document():
    img_path = DATA_DIR / "land_document.png"
    assert img_path.exists(), f"Synthetic document not found: {img_path}"

    ocr_res = run_ocr(str(img_path))
    assert ocr_res.text, "OCR text should not be empty"

    doc_type, conf, reasons = classify(ocr_res.text, file_name=img_path.name)
    assert doc_type == "land_document"

    extractor = get_extractor()
    fields = extractor.extract(ocr_res, doc_type)

    assert "area_sqm" in fields
    assert fields["area_sqm"].value_normalized is not None
    area_float = float(fields["area_sqm"].value_normalized)
    assert area_float >= 10000.0, f"Expected campus area >= 10000 sqm, got {area_float}"

    assert "registration_number" in fields
    assert fields["registration_number"].value_original is not None
    assert "LD" in fields["registration_number"].value_original


def test_extract_a01_trust_registration():
    img_path = DATA_DIR / "trust_registration.png"
    assert img_path.exists(), f"Synthetic document not found: {img_path}"

    ocr_res = run_ocr(str(img_path))
    assert ocr_res.text, "OCR text should not be empty"

    doc_type, conf, reasons = classify(ocr_res.text, file_name=img_path.name)
    assert doc_type == "trust_registration"

    extractor = get_extractor()
    fields = extractor.extract(ocr_res, doc_type)

    assert "trust_name" in fields
    assert fields["trust_name"].value_original is not None
    assert "apex" in fields["trust_name"].value_normalized.lower()

    assert "registration_date" in fields
    assert fields["registration_date"].value_normalized is not None


def test_process_document_pipeline_integration():
    """Test full pipeline execution on SQLite database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    inst = Institution(name="Apex Institute of Technology", state="Maharashtra", trust_name="Apex Educational Foundation")
    db.add(inst)
    db.commit()

    app = Application(institution_id=inst.id, application_type="new_institution", status="draft")
    db.add(app)
    db.commit()

    doc_file = DATA_DIR / "fire_safety_certificate.png"
    doc = Document(application_id=app.id, file_path=str(doc_file), sha256="test-sha256")
    db.add(doc)
    db.commit()

    # Process document through pipeline
    processed = process_document(db, doc.id)

    assert processed.doc_type == "fire_safety_certificate"
    assert processed.ocr_confidence > 0.5
    assert processed.ocr_text is not None

    # Check extracted fields stored in database
    db_fields = db.query(ExtractedField).filter(ExtractedField.document_id == doc.id).all()
    assert len(db_fields) > 0

    field_dict = {f.name: f for f in db_fields}
    assert "certificate_number" in field_dict
    assert "valid_until" in field_dict
    assert field_dict["certificate_number"].value_normalized is not None

    db.close()
