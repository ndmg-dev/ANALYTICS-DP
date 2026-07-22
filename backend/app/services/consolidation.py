from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import ImportJob, ImportStatus, EmployeeRecord
from app.utils import extract_company_from_filename


def get_consolidated_employee_records(db: Session, company: Optional[str] = None) -> List[EmployeeRecord]:
    """The current workforce, across all companies: for each company, only
    the employees from its own most recently completed import.

    Employees are matched against the importing job's company (derived from
    the filename) rather than trusted blindly from `raw_data`, so that any
    stray records inherited from the old snapshot-chaining logic (which used
    to copy rows forward and could duplicate them on repeated reprocessing)
    are excluded rather than accumulated.

    Pass `company` to restrict the result to a single company (e.g. when the
    dashboard is filtered by clicking a company in the distribution chart).
    """
    jobs = db.scalars(
        select(ImportJob).where(ImportJob.status == ImportStatus.COMPLETED)
    ).all()

    latest_job_by_company = {}
    for job in jobs:
        job_company = extract_company_from_filename(job.filename_metadata)
        if not job_company:
            continue
        if company and job_company != company:
            continue
        current = latest_job_by_company.get(job_company)
        if not current or job.uploaded_at > current.uploaded_at:
            latest_job_by_company[job_company] = job

    records: List[EmployeeRecord] = []
    for job_company, job in latest_job_by_company.items():
        if not job.snapshots:
            continue
        # A job may have been reprocessed more than once, each run creating
        # its own Snapshot row — always use the most recent one.
        snapshot = max(job.snapshots, key=lambda s: s.id)
        snap_records = db.scalars(
            select(EmployeeRecord).where(EmployeeRecord.snapshot_id == snapshot.id)
        ).all()
        records.extend(r for r in snap_records if (r.raw_data or {}).get("company") == job_company)

    return records
