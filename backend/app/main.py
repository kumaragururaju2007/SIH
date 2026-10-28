from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.config import settings
from app.database import Base, engine
from app.routers import applications, officer, admin, drafts
from app.schemas import HealthResponse
from app.services.rules_engine import validate_all_configs


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate all YAML rules and configurations at startup
    validate_all_configs()

    # Recreate SQLite DB on startup if requested via env or if schema altered
    if settings.RESET_DB_ON_STARTUP and settings.DATABASE_URL.startswith("sqlite"):
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)

    # Ensure prototype SQLite tables have new columns without manual migration
    if settings.DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            try:
                res = conn.execute(text("PRAGMA table_info(documents);")).fetchall()
                doc_cols = [r[1] for r in res]
                if "qr_text" not in doc_cols and len(doc_cols) > 0:
                    conn.execute(text("ALTER TABLE documents ADD COLUMN qr_text TEXT;"))
                    conn.commit()

                res_ef = conn.execute(text("PRAGMA table_info(extracted_fields);")).fetchall()
                ef_cols = [r[1] for r in res_ef]
                if "needs_verification" not in ef_cols and len(ef_cols) > 0:
                    conn.execute(text("ALTER TABLE extracted_fields ADD COLUMN needs_verification BOOLEAN DEFAULT 0;"))
                    conn.commit()

                res_app = conn.execute(text("PRAGMA table_info(applications);")).fetchall()
                app_cols = [r[1] for r in res_app]
                if "submission_date" not in app_cols and len(app_cols) > 0:
                    conn.execute(text("ALTER TABLE applications ADD COLUMN submission_date DATE;"))
                    conn.commit()

                res_rr = conn.execute(text("PRAGMA table_info(rule_results);")).fetchall()
                rr_cols = [r[1] for r in res_rr]
                if "status" not in rr_cols and len(rr_cols) > 0:
                    conn.execute(text("ALTER TABLE rule_results ADD COLUMN status VARCHAR(50) DEFAULT 'passed';"))
                    conn.commit()

                res_cr = conn.execute(text("PRAGMA table_info(consistency_results);")).fetchall()
                cr_cols = [r[1] for r in res_cr]
                if len(cr_cols) > 0:
                    for col_name, col_type in [
                        ("rule_id", "VARCHAR(100) DEFAULT ''"),
                        ("status", "VARCHAR(50) DEFAULT 'match'"),
                        ("severity", "VARCHAR(50) DEFAULT 'high'"),
                        ("relation", "VARCHAR(50) DEFAULT 'equals'"),
                        ("message", "TEXT DEFAULT ''"),
                        ("clause", "VARCHAR(200)"),
                        ("evidence", "JSON"),
                    ]:
                        if col_name not in cr_cols:
                            conn.execute(text(f"ALTER TABLE consistency_results ADD COLUMN {col_name} {col_type};"))
                    conn.commit()

                # Add risk & label columns to applications
                for col_name, col_type in [
                    ("risk_band", "VARCHAR(50)"),
                    ("risk_factors", "JSON"),
                    ("reasons", "JSON"),
                ]:
                    if col_name not in app_cols:
                        conn.execute(text(f"ALTER TABLE applications ADD COLUMN {col_name} {col_type};"))
                conn.commit()

                # Add label & override columns to documents
                for col_name, col_type in [
                    ("system_label", "VARCHAR(100)"),
                    ("override_label", "VARCHAR(100)"),
                    ("override_reason", "TEXT"),
                    ("override_by", "VARCHAR(100)"),
                    ("reasons", "JSON"),
                ]:
                    if col_name not in doc_cols:
                        conn.execute(text(f"ALTER TABLE documents ADD COLUMN {col_name} {col_type};"))
                conn.commit()
            except Exception:
                pass
    yield


app = FastAPI(
    title="AICTE Document Validation System API",
    description="Backend API for AI-powered AICTE document validation, institution risk scoring, and deficiency management.",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for frontend development server and deployed environments
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:4173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health_check():
    return {"status": "ok"}


from pathlib import Path
from fastapi.staticfiles import StaticFiles

# Ensure storage/forensics exists
forensics_dir = Path(__file__).resolve().parent.parent / "storage" / "forensics"
forensics_dir.mkdir(parents=True, exist_ok=True)
app.mount("/forensics", StaticFiles(directory=str(forensics_dir)), name="forensics")

app.include_router(applications.router)
app.include_router(officer.router)
app.include_router(admin.router)
app.include_router(drafts.router)

