from typing import Optional
from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Company, ImportJob, ImportStatus
from app.services.company_resolver import get_or_create_company, resolve_company
from app.storage.minio_client import MinioClient
import hashlib
import uuid

router = APIRouter(prefix="/imports", tags=["Imports"])
minio_client = MinioClient()


class CompanyAssignment(BaseModel):
    company_id: Optional[int] = None
    company_name: Optional[str] = None


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_import_file(
    file: UploadFile = File(...),
    company_id: Optional[int] = Form(None),
    company_name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    if not file.filename.endswith('.xls'):
        raise HTTPException(status_code=400, detail="Somente arquivos .xls são suportados atualmente.")
    
    # Read file content to generate hash and save to minio
    content = await file.read()
    file_size = len(content)
    
    # Max size 50MB
    if file_size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Arquivo excede o limite de 50MB.")
        
    file_hash = hashlib.sha256(content).hexdigest()
    
    # Check for duplicate
    existing_import = db.query(ImportJob).filter(ImportJob.file_hash == file_hash).first()
    if existing_import:
        return {"message": "Arquivo já importado anteriormente.", "import_id": existing_import.id, "status": existing_import.status}
    
    object_key = f"imports/{uuid.uuid4()}_{file.filename}"
    
    import io
    file_stream = io.BytesIO(content)
    
    success = minio_client.upload_file(file_stream, object_key, file_size, file.content_type)
    if not success:
        raise HTTPException(status_code=500, detail="Erro ao salvar o arquivo no armazenamento.")
        
    # An explicitly chosen company always wins; otherwise the CNPJ/name in the
    # filename identifies it, creating the company on first sight.
    if not company_id and company_name and company_name.strip():
        created = get_or_create_company(db, name=company_name.strip())
        company_id = created.id if created else None

    company = resolve_company(db, file.filename, explicit_company_id=company_id)

    new_import = ImportJob(
        filename_metadata=file.filename,
        minio_object_key=object_key,
        file_hash=file_hash,
        file_size=file_size,
        company_id=company.id if company else None,
        company_name_raw=company.name if company else None,
        status=ImportStatus.QUEUED
    )

    db.add(new_import)
    db.commit()
    db.refresh(new_import)
    
    return {
        "message": "Importação enfileirada com sucesso.",
        "import_id": new_import.id,
        "status": new_import.status,
        "company": company.name if company else None,
    }

@router.get("/")
async def list_imports(db: Session = Depends(get_db)):
    imports = db.query(ImportJob).order_by(ImportJob.uploaded_at.desc()).limit(20).all()
    
    result = []
    for job in imports:
        # Get record count from snapshot if completed
        records = 0
        if job.snapshots:
            from app.models import EmployeeRecord
            # A reprocessed job has several snapshots — the newest is the live one.
            snapshot = max(job.snapshots, key=lambda s: s.id)
            records = db.query(EmployeeRecord).filter(EmployeeRecord.snapshot_id == snapshot.id).count()

        error_message = None
        if job.parser_runs:
            last_run = max(job.parser_runs, key=lambda r: r.id)
            error_message = last_run.error_details or None

        result.append({
            "id": job.id,
            "filename": job.filename_metadata,
            "status": job.status.value if hasattr(job.status, 'value') else job.status,
            "date": job.uploaded_at.strftime("%d/%m/%Y %H:%M") if job.uploaded_at else "",
            "records": records,
            "company": job.company.name if job.company else None,
            "company_id": job.company_id,
            "error_message": error_message
        })
    return result


@router.patch("/{import_id}/company")
async def assign_import_company(
    import_id: int, payload: CompanyAssignment, db: Session = Depends(get_db)
):
    """Attach (or correct) the company of an existing import — the escape hatch
    for files whose name carries neither a CNPJ nor a recognizable name."""
    job = db.query(ImportJob).filter(ImportJob.id == import_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Importação não encontrada.")

    company = None
    if payload.company_id:
        company = db.get(Company, payload.company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    elif payload.company_name and payload.company_name.strip():
        company = get_or_create_company(db, name=payload.company_name.strip())

    if not company:
        raise HTTPException(status_code=400, detail="Informe a empresa.")

    job.company_id = company.id
    db.commit()

    return {"import_id": job.id, "company": company.name, "company_id": company.id}

@router.post("/{import_id}/retry")
async def retry_import(import_id: int, db: Session = Depends(get_db)):
    job = db.query(ImportJob).filter(ImportJob.id == import_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Importação não encontrada.")

    if job.status not in (ImportStatus.FAILED, ImportStatus.AWAITING_REVIEW):
        raise HTTPException(status_code=400, detail="Somente importações com falha podem ser reprocessadas.")

    job.status = ImportStatus.QUEUED
    job.started_at = None
    job.completed_at = None
    db.commit()

    return {"message": "Importação reenfileirada para reprocessamento.", "import_id": job.id, "status": job.status}

@router.get("/latest-snapshot")
async def get_latest_snapshot(db: Session = Depends(get_db)):
    from app.models import Snapshot
    snapshot = db.query(Snapshot).order_by(Snapshot.created_at.desc()).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Nenhum snapshot encontrado")
    return {"snapshot_id": snapshot.id, "reference_date": snapshot.reference_date}
