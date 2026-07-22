from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import ImportJob, ImportStatus
from app.storage.minio_client import MinioClient
import hashlib
import uuid

router = APIRouter(prefix="/imports", tags=["Imports"])
minio_client = MinioClient()

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_import_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
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
        
    new_import = ImportJob(
        filename_metadata=file.filename,
        minio_object_key=object_key,
        file_hash=file_hash,
        file_size=file_size,
        status=ImportStatus.QUEUED
    )
    
    db.add(new_import)
    db.commit()
    db.refresh(new_import)
    
    return {"message": "Importação enfileirada com sucesso.", "import_id": new_import.id, "status": new_import.status}

@router.get("/")
async def list_imports(db: Session = Depends(get_db)):
    imports = db.query(ImportJob).order_by(ImportJob.uploaded_at.desc()).limit(20).all()
    
    result = []
    for job in imports:
        # Get record count from snapshot if completed
        records = 0
        if job.snapshots:
            from app.models import EmployeeRecord
            records = db.query(EmployeeRecord).filter(EmployeeRecord.snapshot_id == job.snapshots[0].id).count()

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
            "error_message": error_message
        })
    return result

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
