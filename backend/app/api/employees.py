from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.models import Company, Snapshot, EmployeeNote
from app.services.consolidation import get_consolidated_employee_records

router = APIRouter(prefix="/employees", tags=["Employees"])

class NoteUpdate(BaseModel):
    company: Optional[str] = None
    company_id: Optional[int] = None
    code: str
    notes: str

@router.get("/snapshot/{snapshot_id}")
async def list_employees(
    snapshot_id: int,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    snapshot = db.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot não encontrado")

    # The current workforce spans every company's own latest completed
    # import, not just this one snapshot — see app/services/consolidation.py.
    employees = get_consolidated_employee_records(
        db, company_ids=[company_id] if company_id else None
    )

    # Fetch all notes, keyed by company id where available and by display name
    # for notes written before companies became first-class.
    notes_db = db.query(EmployeeNote).all()
    notes_by_id = {(n.company_id, n.code): n.notes for n in notes_db if n.company_id}
    notes_by_name = {(n.company, n.code): n.notes for n in notes_db}

    result = []
    for emp, company in employees:
        result.append({
            "id": emp.id,
            "code": emp.code,
            "name": emp.name,
            "job_title": emp.job_title,
            "company": company.name,
            "company_id": company.id,
            "category": emp.category,
            "admission_date": emp.admission_date,
            "salary": emp.salary,
            "notes": notes_by_id.get((company.id, emp.code))
                     or notes_by_name.get((company.name, emp.code), ""),
            "status": "Ativo"
        })
    return result

@router.put("/notes")
async def update_note(payload: NoteUpdate, db: Session = Depends(get_db)):
    company = db.get(Company, payload.company_id) if payload.company_id else None
    company_name = company.name if company else payload.company
    if not company_name:
        raise HTTPException(status_code=400, detail="Empresa não informada.")

    note = None
    if company:
        note = db.query(EmployeeNote).filter(
            EmployeeNote.company_id == company.id,
            EmployeeNote.code == payload.code
        ).first()
    if not note:
        # Falls back to the display name so notes saved before company ids
        # existed are updated in place instead of duplicated.
        note = db.query(EmployeeNote).filter(
            EmployeeNote.company == company_name,
            EmployeeNote.code == payload.code
        ).first()

    if note:
        note.notes = payload.notes
        if company and not note.company_id:
            note.company_id = company.id
    else:
        note = EmployeeNote(
            company=company_name,
            company_id=company.id if company else None,
            code=payload.code,
            notes=payload.notes
        )
        db.add(note)

    db.commit()
    return {"status": "success"}
