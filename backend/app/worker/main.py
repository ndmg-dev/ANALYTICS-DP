import time
import os
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from app.db.session import SessionLocal
from app.models import ImportJob, ImportStatus, ParserRun
from app.parser.deterministic import ExcelDeterministicParser
from app.storage.minio_client import MinioClient
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

            incoming_company = None
            if result.records:
                incoming_company = result.records[0].get("company", "Mendonça Galvão Contadores Associados")

            # Carry over old records from the previous snapshot
            last_snapshot = db.scalar(
                select(Snapshot)
                .where(Snapshot.status == "ACTIVE", Snapshot.id < snapshot.id)
                .order_by(Snapshot.id.desc())
                .limit(1)
            )

            if last_snapshot and incoming_company:
                old_records = db.scalars(
                    select(EmployeeRecord).where(EmployeeRecord.snapshot_id == last_snapshot.id)
                ).all()
                
                for old_emp in old_records:
                    old_company = (old_emp.raw_data or {}).get("company", "N/A")
                    if old_company != incoming_company:
                        new_emp = EmployeeRecord(
                            snapshot_id=snapshot.id,
                            original_row=old_emp.original_row,
                            code=old_emp.code,
                            name=old_emp.name,
                            job_title=old_emp.job_title,
                            category=old_emp.category,
                            monthly_hours=old_emp.monthly_hours,
                            children_count=old_emp.children_count,
                            dependents_count=old_emp.dependents_count,
                            admission_date=old_emp.admission_date,
                            fgts_option=old_emp.fgts_option,
                            union_contribution=old_emp.union_contribution,
                            salary=old_emp.salary,
                            raw_data=old_emp.raw_data
                        )
                        db.add(new_emp)

            # Save incoming Employee Records
            for row in result.records:
                emp = EmployeeRecord(
                    snapshot_id=snapshot.id,
                    original_row=row.get('original_row', 0),
                    code=str(row.get('code', 'N/A')),
                    name=str(row.get('name', 'N/A')),
                    job_title=str(row.get('job_title', 'N/A')),
                    category=str(row.get('category', 'N/A')),
                    monthly_hours=row.get('monthly_hours'),
                    children_count=row.get('children_count'),
                    dependents_count=row.get('dependents_count'),
                    admission_date=row.get('admission_date'),
                    fgts_option=row.get('fgts_option'),
                    union_contribution=row.get('union_contribution'),
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

    except Exception as e:
        db.rollback()
        job.status = ImportStatus.FAILED
        job.completed_at = datetime.utcnow()
        print(f"Error processing job {job.id}: {e}")
        db.commit()

def run_worker():
    from app.models import Base
    from app.db.session import engine
    Base.metadata.create_all(bind=engine)
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
