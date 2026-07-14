from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import DataQualityFinding, Snapshot

router = APIRouter(prefix="/quality", tags=["Quality"])

@router.get("/snapshot/{snapshot_id}")
async def list_quality_findings(snapshot_id: int, db: Session = Depends(get_db)):
    snapshot = db.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot não encontrado")
        
    findings = db.query(DataQualityFinding).filter(DataQualityFinding.import_id == snapshot.import_id).all()
    
    return [
        {
            "id": f.id,
            "severity": f.severity,
            "field_name": f.field_name,
            "description": f.issue_description,
            "affected_record_row": f.original_row
        }
        for f in findings
    ]
