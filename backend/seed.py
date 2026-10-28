import sys
from pathlib import Path

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database import Base, engine, SessionLocal
from app.models import Institution, InstitutionHistory
from app.audit import log_action


def seed_database():
    """Seed database with sample institutions and simulated history."""
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if already seeded
        existing_count = db.query(Institution).count()
        if existing_count > 0:
            print(f"Database already contains {existing_count} institutions. Skipping duplicate seeding.")
            return

        print("Seeding sample institutions...")

        # 1. Clean record institution
        inst_clean = Institution(
            name="Apex Institute of Technology",
            state="Maharashtra",
            trust_name="Apex Educational Foundation",
        )
        db.add(inst_clean)
        db.flush()  # populate inst_clean.id

        history_clean = [
            InstitutionHistory(
                institution_id=inst_clean.id,
                year=2023,
                outcome="approved",
                flags_count=0,
                deficiency_count=0,
            ),
            InstitutionHistory(
                institution_id=inst_clean.id,
                year=2024,
                outcome="approved",
                flags_count=0,
                deficiency_count=0,
            ),
            InstitutionHistory(
                institution_id=inst_clean.id,
                year=2025,
                outcome="approved",
                flags_count=0,
                deficiency_count=0,
            ),
        ]
        db.add_all(history_clean)

        # 2. Institution with past rejections and flags
        inst_risky = Institution(
            name="Horizon Institute of Engineering",
            state="Karnataka",
            trust_name="Horizon Global Trust",
        )
        db.add(inst_risky)
        db.flush()

        history_risky = [
            InstitutionHistory(
                institution_id=inst_risky.id,
                year=2023,
                outcome="deficiency_sent",
                flags_count=3,
                deficiency_count=2,
            ),
            InstitutionHistory(
                institution_id=inst_risky.id,
                year=2024,
                outcome="rejected",
                flags_count=5,
                deficiency_count=4,
            ),
            InstitutionHistory(
                institution_id=inst_risky.id,
                year=2025,
                outcome="approved",
                flags_count=1,
                deficiency_count=1,
            ),
        ]
        db.add_all(history_risky)

        # 3. New institution with no history
        inst_new = Institution(
            name="National Polytechnic College",
            state="Tamil Nadu",
            trust_name="National Educational Society",
        )
        db.add(inst_new)
        db.flush()

        db.commit()

        # Log seeding in audit trail
        log_action(
            db=db,
            actor="seed_script",
            action="seed_institutions",
            entity="system:database",
            details={
                "seeded_institutions": [
                    {"id": inst_clean.id, "name": inst_clean.name, "history_records": len(history_clean)},
                    {"id": inst_risky.id, "name": inst_risky.name, "history_records": len(history_risky)},
                    {"id": inst_new.id, "name": inst_new.name, "history_records": 0},
                ]
            },
        )

        print("Seeding completed successfully:")
        print(f" - [ID {inst_clean.id}] {inst_clean.name} (Clean Record, 3 approved years)")
        print(f" - [ID {inst_risky.id}] {inst_risky.name} (Past Rejections & Flags)")
        print(f" - [ID {inst_new.id}] {inst_new.name} (New Institution, No History)")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
