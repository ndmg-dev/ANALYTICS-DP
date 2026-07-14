from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import EmployeeRecord, Snapshot

router = APIRouter(prefix="/employees", tags=["Employees"])

@router.get("/snapshot/{snapshot_id}")
async def list_employees(snapshot_id: int, db: Session = Depends(get_db)):
    snapshot = db.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot não encontrado")
        
    employees = db.query(EmployeeRecord).filter(EmployeeRecord.snapshot_id == snapshot_id).all()
    
    return [
        {
            "id": emp.id,
            "code": emp.code,
            "name": emp.name,
            "job_title": emp.job_title,
            "company": (emp.raw_data or {}).get("company", "Mendonça Galvão Contadores Associados"),
            "category": emp.category,
            "admission_date": emp.admission_date,
            "status": "Ativo"
        }
        for emp in employees
    ]
