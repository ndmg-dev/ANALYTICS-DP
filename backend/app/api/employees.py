from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.models import Snapshot, EmployeeNote
from app.services.consolidation import get_consolidated_employee_records

router = APIRouter(prefix="/employees", tags=["Employees"])

class NoteUpdate(BaseModel):
    company: str
    code: str
    notes: str

@router.get("/snapshot/{snapshot_id}")
async def list_employees(snapshot_id: int, db: Session = Depends(get_db)):
    snapshot = db.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot não encontrado")

    # The current workforce spans every company's own latest completed
    # import, not just this one snapshot — see app/services/consolidation.py.
    employees = get_consolidated_employee_records(db)

    # Fetch all notes
    notes_db = db.query(EmployeeNote).all()
    notes_map = {(n.company, n.code): n.notes for n in notes_db}
    
    result = []
    for emp in employees:
        company = (emp.raw_data or {}).get("company", "Mendonça Galvão Contadores Associados")
        result.append({
            "id": emp.id,
            "code": emp.code,
            "name": emp.name,
            "job_title": emp.job_title,
            "company": company,
            "category": emp.category,
            "admission_date": emp.admission_date,
            "salary": emp.salary,
            "notes": notes_map.get((company, emp.code), ""),
            "status": "Ativo"
        })
    return result

@router.put("/notes")
async def update_note(payload: NoteUpdate, db: Session = Depends(get_db)):
    note = db.query(EmployeeNote).filter(
        EmployeeNote.company == payload.company,
        EmployeeNote.code == payload.code
    ).first()
    
    if note:
        note.notes = payload.notes
    else:
        note = EmployeeNote(
            company=payload.company,
            code=payload.code,
            notes=payload.notes
        )
        db.add(note)
    
    db.commit()
    return {"status": "success"}
