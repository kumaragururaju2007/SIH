"""
Reset script for AICTE Demo Data.
Cleans all tables and resets database to a fresh state.
Usage: python -m scripts.reset_demo
"""

import sys
import shutil
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database import Base, engine, SessionLocal
from app.config import settings
from app.models import (
    Application,
    Document,
    ExtractedField,
    RuleResult,
    ConsistencyResult,
    AuthResult,
    DeficiencyReport,
    AuditLog,
    InstitutionHistory,
    Institution,
)


def reset_demo():
    print("=" * 60)
    print("RESETTING AICTE DEMO DATABASE & STORAGE")
    print("=" * 60)

    # 1. Clean database tables
    db = SessionLocal()
    try:
        print("[1/3] Deleting existing database records...")
        db.query(AuditLog).delete()
        db.query(DeficiencyReport).delete()
        db.query(AuthResult).delete()
        db.query(ConsistencyResult).delete()
        db.query(RuleResult).delete()
        db.query(ExtractedField).delete()
        db.query(Document).delete()
        db.query(Application).delete()
        db.query(InstitutionHistory).delete()
        db.query(Institution).delete()
        db.commit()
        print("      Database records wiped successfully.")
    except Exception as e:
        print(f"      Database clean error: {e}, dropping/recreating tables...")
        db.rollback()
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    finally:
        db.close()

    # 2. Clean uploaded storage documents (preserve synthetic ground truth)
    print("[2/3] Cleaning upload storage directory...")
    upload_dir = Path(settings.UPLOAD_DIR)
    if upload_dir.exists():
        for item in upload_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            elif item.name != ".gitkeep":
                item.unlink(missing_ok=True)
    print(f"      Cleaned {upload_dir}")

    # 3. Clean generated forensics images
    print("[3/3] Cleaning generated forensics artifacts...")
    forensics_dir = Path(settings.STORAGE_DIR) / "forensics"
    if forensics_dir.exists():
        for item in forensics_dir.iterdir():
            if item.is_file() and item.name != ".gitkeep":
                item.unlink(missing_ok=True)
    print(f"      Cleaned {forensics_dir}")

    print("\nDatabase and storage reset completed successfully.")


if __name__ == "__main__":
    reset_demo()
