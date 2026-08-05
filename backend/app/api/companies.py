from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Company
from app.services.company_resolver import get_or_create_company
from app.services.consolidation import get_consolidated_employee_records

router = APIRouter(prefix="/companies", tags=["Companies"])


class CompanyCreate(BaseModel):
    name: str
    cnpj: Optional[str] = None


@router.get("/")
async def list_companies(db: Session = Depends(get_db)):
    """Companies that currently have employees, for the filter selectors.

    Counts come from the same consolidation used by the dashboard, so the
    numbers shown in the selector always agree with the charts.
    """
    counts = {}
    for _record, company in get_consolidated_employee_records(db):
        counts[company.id] = counts.get(company.id, 0) + 1

    companies = db.query(Company).order_by(Company.name).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "cnpj": c.cnpj,
            "employee_count": counts.get(c.id, 0),
        }
        for c in companies
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nome da empresa é obrigatório.")

    company = get_or_create_company(db, name=name, cnpj=payload.cnpj)
    db.commit()
    db.refresh(company)
    return {"id": company.id, "name": company.name, "cnpj": company.cnpj}
