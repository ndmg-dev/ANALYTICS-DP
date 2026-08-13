from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Company
from app.services.company_resolver import get_or_create_company
from app.services.consolidation import get_consolidated_employee_records
from app.services.provisions import DEFAULT_REGIME, REGIME_LABELS

router = APIRouter(prefix="/companies", tags=["Companies"])


class CompanyCreate(BaseModel):
    name: str
    cnpj: Optional[str] = None
    tax_regime: Optional[str] = None


class CompanyUpdate(BaseModel):
    tax_regime: str


def _serialize(company: Company, employee_count: int = 0) -> dict:
    regime = company.tax_regime or DEFAULT_REGIME
    return {
        "id": company.id,
        "name": company.name,
        "cnpj": company.cnpj,
        "tax_regime": regime,
        "tax_regime_label": REGIME_LABELS.get(regime, regime),
        "employee_count": employee_count,
    }


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
    return [_serialize(c, counts.get(c.id, 0)) for c in companies]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nome da empresa é obrigatório.")

    company = get_or_create_company(db, name=name, cnpj=payload.cnpj)
    if payload.tax_regime:
        company.tax_regime = _validated_regime(payload.tax_regime)
    db.commit()
    db.refresh(company)
    return _serialize(company)


@router.patch("/{company_id}")
async def update_company(company_id: int, payload: CompanyUpdate, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    company.tax_regime = _validated_regime(payload.tax_regime)
    db.commit()
    db.refresh(company)
    return _serialize(company)


def _validated_regime(regime: str) -> str:
    if regime not in REGIME_LABELS:
        raise HTTPException(
            status_code=400,
            detail=f"Regime inválido. Use um de: {', '.join(REGIME_LABELS)}.",
        )
    return regime
