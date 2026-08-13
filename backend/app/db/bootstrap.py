"""Idempotent schema patching and data backfill run at application start-up.

The schema is created by `Base.metadata.create_all`, which happily creates new
tables but never adds columns to tables that already exist. Until Alembic
revisions exist (migrations/versions/ is empty), the columns introduced by the
multi-company work are added here instead, followed by a one-off backfill that
links pre-existing imports to their company.
"""
import logging
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# Postgres supports IF NOT EXISTS on ADD COLUMN, so re-running is a no-op.
_DDL = [
    "ALTER TABLE imports ADD COLUMN IF NOT EXISTS company_id INTEGER REFERENCES companies(id)",
    "ALTER TABLE imports ADD COLUMN IF NOT EXISTS company_name_raw VARCHAR",
    "CREATE INDEX IF NOT EXISTS ix_imports_company_id ON imports (company_id)",
    "ALTER TABLE companies ADD COLUMN IF NOT EXISTS tax_regime VARCHAR NOT NULL DEFAULT 'NORMAL'",
    "ALTER TABLE employee_notes ADD COLUMN IF NOT EXISTS company_id INTEGER REFERENCES companies(id)",
    "CREATE INDEX IF NOT EXISTS ix_employee_notes_company_id ON employee_notes (company_id)",
]


def ensure_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        for statement in _DDL:
            conn.execute(text(statement))


def backfill_companies() -> None:
    """Attach every import that predates the `companies` table to a company.

    Only touches rows where company_id is NULL, so it is safe on every boot and
    never overrides a company assigned by hand.
    """
    from app.models import Company, EmployeeRecord, ImportJob, EmployeeNote
    from app.services.company_resolver import resolve_company, get_or_create_company

    db = SessionLocal()
    try:
        pending = db.query(ImportJob).filter(ImportJob.company_id.is_(None)).all()
        linked = 0
        for job in pending:
            company = resolve_company(db, job.filename_metadata)

            if not company:
                # Older imports carried the company inside each record's
                # raw_data — the last place worth looking before giving up.
                snapshot = max(job.snapshots, key=lambda s: s.id) if job.snapshots else None
                if snapshot:
                    record = (
                        db.query(EmployeeRecord)
                        .filter(EmployeeRecord.snapshot_id == snapshot.id)
                        .first()
                    )
                    raw_company = (record.raw_data or {}).get("company") if record else None
                    if raw_company:
                        company = get_or_create_company(db, name=raw_company)

            if company:
                job.company_id = company.id
                job.company_name_raw = job.company_name_raw or company.name
                linked += 1

        # Notes were keyed by the company display name; match them up.
        orphan_notes = db.query(EmployeeNote).filter(EmployeeNote.company_id.is_(None)).all()
        if orphan_notes:
            by_name = {c.name: c.id for c in db.query(Company).all()}
            for note in orphan_notes:
                note.company_id = by_name.get(note.company)

        db.commit()
        unresolved = len(pending) - linked
        logger.info(
            "Backfill de empresas: %s importações vinculadas, %s sem empresa identificada.",
            linked,
            unresolved,
        )
    except Exception:
        db.rollback()
        logger.exception("Falha no backfill de empresas")
    finally:
        db.close()
