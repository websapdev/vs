"""
Database migrations
Idempotent schema creation and management
"""

from sqlalchemy import inspect, text

from api.vysalytica.db import Base, SessionLocal, engine
from api.vysalytica.db.models import (
    AnswerGraph,
    APIKey,
    AuditRun,
    CitationSnapshot,
    Finding,
    Playbook,
    PlaybookFix,
    ReferralAttribution,
    ReferralCode,
    RuleDefinition,
)
from api.vysalytica.db.rule_seed_data import RULE_DEFINITION_SEED_DATA


def ensure_findings_confidence_column() -> None:
    """Ensure the findings table includes the confidence column."""
    try:
        columns = {col["name"] for col in inspect(engine).get_columns("findings")}
    except Exception:
        # If inspection fails, do not block migrations
        return

    if "confidence" in columns:
        return

    try:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE findings ADD COLUMN confidence FLOAT"))
        print("[OK] Added confidence column to findings table")
    except Exception as exc:
        # Log but do not fail migrations; rerunning with fresh DB will include column
        print(f"[FAIL] Failed to add confidence column: {exc}")


def seed_rule_definitions() -> bool:
    """Seed static rule definitions for AI Optimization pack."""
    session = SessionLocal()
    inserted = 0
    updated = 0

    try:
        for rule_data in RULE_DEFINITION_SEED_DATA:
            existing = session.get(RuleDefinition, rule_data["id"])

            if existing:
                changed = False
                for field in [
                    "title",
                    "category",
                    "pack",
                    "description",
                    "why",
                    "fix",
                    "confidence",
                    "acceptance_criteria",
                ]:
                    new_value = rule_data.get(field)
                    if getattr(existing, field) != new_value:
                        setattr(existing, field, new_value)
                        changed = True
                if changed:
                    updated += 1
            else:
                session.add(RuleDefinition(**rule_data))
                inserted += 1

        session.commit()
    except Exception as exc:
        session.rollback()
        print(f"[FAIL] Rule definition seeding failed: {exc}")
        return False
    finally:
        session.close()

    if inserted or updated:
        print(f"[OK] Seeded {len(RULE_DEFINITION_SEED_DATA)} rule definitions")
    else:
        print("[OK] Rule definitions already up to date")

    return True


def run_migrations():
    """
    Create all tables in the database.
    Idempotent - safe to run multiple times.
    """
    try:
        Base.metadata.create_all(bind=engine)
        ensure_findings_confidence_column()
        seeded = seed_rule_definitions()
        if not seeded:
            return False
        print("[OK] Database migrations completed successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Database migration failed: {str(e)}")
        return False


def rollback_migrations():
    """
    Drop all tables from the database.
    WARNING: This will delete all data!
    """
    try:
        Base.metadata.drop_all(bind=engine)
        print("[OK] Database rollback completed successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Database rollback failed: {str(e)}")
        return False


def reset_database():
    """
    Reset database by dropping and recreating all tables.
    WARNING: This will delete all data!
    """
    rollback_migrations()
    run_migrations()


if __name__ == "__main__":
    # Allow running migrations from command line
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "migrate":
            run_migrations()
        elif command == "rollback":
            rollback_migrations()
        elif command == "reset":
            reset_database()
        else:
            print("Usage: python migrations.py [migrate|rollback|reset]")
    else:
        run_migrations()
