from typing import Dict, List, Optional, Sequence, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import Company, ImportJob, ImportStatus, EmployeeRecord

# An employee record paired with the company that imported it.
ConsolidatedRecord = Tuple[EmployeeRecord, Company]


def get_consolidated_employee_records(
    db: Session, company_ids: Optional[Sequence[int]] = None
) -> List[ConsolidatedRecord]:
    """The current workforce, across all companies: for each company, only
    the employees from its own most recently completed import.

    A record's company comes from `snapshot -> import -> company`, the single
    source of truth. It used to be re-derived from the filename on every read
    and cross-checked against `raw_data["company"]`, which silently dropped
    every import whose filename didn't match the expected pattern.

    Pass `company_ids` to restrict the result to specific companies (dashboard
    and employee-list filters).
    """
    jobs = db.scalars(
        select(ImportJob).where(ImportJob.status == ImportStatus.COMPLETED)
    ).all()

    wanted = set(company_ids) if company_ids else None

    latest_job_by_company: Dict[int, ImportJob] = {}
    for job in jobs:
        if not job.company_id:
            # Company could not be identified — surfaced in the imports
            # history for manual assignment rather than counted here.
            continue
        if wanted is not None and job.company_id not in wanted:
            continue
        current = latest_job_by_company.get(job.company_id)
        if not current or job.uploaded_at > current.uploaded_at:
            latest_job_by_company[job.company_id] = job

    records: List[ConsolidatedRecord] = []
    for job in latest_job_by_company.values():
        if not job.snapshots:
            continue
        # A job may have been reprocessed more than once, each run creating
        # its own Snapshot row — always use the most recent one.
        snapshot = max(job.snapshots, key=lambda s: s.id)
        snap_records = db.scalars(
            select(EmployeeRecord).where(EmployeeRecord.snapshot_id == snapshot.id)
        ).all()
        records.extend((r, job.company) for r in snap_records)

    return records
