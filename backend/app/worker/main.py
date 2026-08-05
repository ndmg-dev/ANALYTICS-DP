import time
import os
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from app.db.session import SessionLocal
from app.models import ImportJob, ImportStatus, ParserRun
from app.parser.deterministic import ExcelDeterministicParser
from app.storage.minio_client import MinioClient
from app.services.company_resolver import resolve_company
from datetime import datetime

minio_client = MinioClient()
parser = ExcelDeterministicParser()

def claim_job(db: Session) -> ImportJob:
    # Attempt to lock a row using SKIP LOCKED for concurrent safety
    stmt = (
        select(ImportJob)
        .where(ImportJob.status == ImportStatus.QUEUED)
        .order_by(ImportJob.uploaded_at.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    job = db.execute(stmt).scalar_one_or_none()
    if job:
        job.status = ImportStatus.PROCESSING
        job.started_at = datetime.utcnow()
        job.attempt_count += 1
        db.commit()
        db.refresh(job)
    return job

def process_job(db: Session, job: ImportJob):
    try:
        # Get file from MinIO
        file_stream = minio_client.get_file_stream(job.minio_object_key)
        file_content = file_stream.read()

        # Parse
        result = parser.parse(file_content)

        # Create Parser Run record
        parser_run = ParserRun(
            import_id=job.id,
            parser_version="1.0",
            status="SUCCESS" if result.is_success else "FAILED",
            confidence_score=result.confidence_score,
            confidence_factors=result.confidence_factors,
            error_details=result.error_details,
            completed_at=datetime.utcnow()
        )
        db.add(parser_run)
        db.flush()

        # Update Job Status based on confidence
        if result.is_success:
            job.status = ImportStatus.COMPLETED
            
            # Create Snapshot
            from app.models import Snapshot, EmployeeRecord, MetricResult
            snapshot = Snapshot(
                import_id=job.id,
                reference_date=datetime.utcnow(),
                status="ACTIVE"
            )
            db.add(snapshot)
            db.flush()
            
            # Link snapshot to parser run
            parser_run.snapshot_id = snapshot.id

            # The company is resolved once, at import level (see
            # app/services/company_resolver.py): the CNPJ or name in the
            # filename first, then the spreadsheet title row when the template
            # has one. It is normally already set at upload time; resolving
            # again here covers reprocessed and backfilled jobs.
            if not job.company_id:
                sheet_title = result.records[0].get("company") if result.records else None
                company = resolve_company(db, job.filename_metadata, sheet_title=sheet_title)
                if company:
                    job.company_id = company.id
                    job.company_name_raw = company.name

            # Records still carry the name in raw_data for traceability, but
            # reads resolve the company through the import (see
            # app/services/consolidation.py) rather than trusting this copy.
            company_name = job.company.name if job.company else None
            for row in result.records:
                row["company"] = company_name

            # Each snapshot only holds the records from its own file. Other
            # companies' current employees are pulled in at read time (see
            # app/services/consolidation.py) from their own latest completed
            # import, instead of being copied here — copying used to compound
            # duplicates every time a file was reprocessed.

            # Save incoming Employee Records
            for row in result.records:
                emp = EmployeeRecord(
                    snapshot_id=snapshot.id,
                    original_row=row.get('original_row', 0),
                    code=str(row.get('code', 'N/A')),
                    name=str(row.get('name', 'N/A')),
                    job_title=str(row.get('job_title', 'N/A')),
                    category=str(row.get('category', 'N/A')),
                    admission_date=row.get('admission_date'),
                    salary=row.get('salary'),
                    raw_data={k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in row.items()}
                )
                db.add(emp)
                
            db.flush()
            
            # Run Metrics Engine
            from app.services.metrics import MetricsEngine
            engine = MetricsEngine(db)
            engine.compute_and_save_metrics(snapshot.id)
            
        else:
            if result.error_details:
                job.status = ImportStatus.FAILED
            else:
                job.status = ImportStatus.AWAITING_REVIEW

        job.completed_at = datetime.utcnow()
        db.commit()
        print(f"Processed job {job.id} - Status: {job.status}")

    except Exception:
        db.rollback()
        job.status = ImportStatus.FAILED
        job.completed_at = datetime.utcnow()
        logging.exception(f"Error processing job {job.id}")
        db.commit()

def run_worker():
    from app.models import Base
    from app.db.session import engine
    from app.db.bootstrap import ensure_schema
    Base.metadata.create_all(bind=engine)
    # The worker may boot before the API — patch the schema here too so it
    # never writes against a table missing the company columns.
    ensure_schema(engine)
    print("Worker started. Waiting for jobs...")
    while True:
        db = SessionLocal()
        try:
            job = claim_job(db)
            if job:
                process_job(db, job)
            else:
                time.sleep(5)
        except Exception as e:
            print(f"Worker iteration error: {e}")
            time.sleep(5)
        finally:
            db.close()

if __name__ == "__main__":
    run_worker()
