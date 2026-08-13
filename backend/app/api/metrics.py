from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Snapshot
from app.services.metrics import MetricsEngine
from app.services.consolidation import get_consolidated_employee_records
from app.services.provisions import (
    DEFAULT_REGIME,
    REGIME_LABELS,
    rate_breakdown,
    sum_provisions,
)

router = APIRouter(prefix="/metrics", tags=["Metrics"])

@router.get("/dashboard/{snapshot_id}")
async def get_dashboard_metrics(snapshot_id: int, company_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    snapshot = db.get(Snapshot, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    # The current workforce spans every company's own latest completed
    # import, not just this one snapshot — see app/services/consolidation.py.
    company_ids = [company_id] if company_id else None
    records = get_consolidated_employee_records(db, company_ids=company_ids)

    engine = MetricsEngine(db)
    metrics_list = engine.compute_metrics_for_records(records, datetime.utcnow())
    response = dict(metrics_list)

    # Labour provisions accrued monthly on top of payroll — see
    # app/services/provisions.py.
    provisions = sum_provisions(
        (r.salary, company.tax_regime or DEFAULT_REGIME) for r, company in records
    )
    response.update({
        "provision_vacation": provisions["vacation"],
        "provision_vacation_bonus": provisions["vacation_bonus"],
        "provision_thirteenth": provisions["thirteenth"],
        "provision_fgts": provisions["fgts"],
        "provision_social_security": provisions["social_security"],
        "provisions_total": provisions["total"],
        "total_cost": provisions["total_cost"],
    })

    return {"snapshot_id": snapshot_id, "reference_date": snapshot.reference_date, "metrics": response}

@router.get("/distributions/{snapshot_id}")
async def get_dashboard_distributions(snapshot_id: int, company_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    snapshot = db.get(Snapshot, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    company_ids = [company_id] if company_id else None
    records = get_consolidated_employee_records(db, company_ids=company_ids)

    engine = MetricsEngine(db)
    distributions = engine.compute_distributions_for_records(records, datetime.utcnow())

    # The company breakdown always covers every company, even when a filter is
    # active — otherwise selecting a company collapses the pie into a single
    # slice and there is no way back to the other companies from the chart.
    if company_ids:
        all_records = get_consolidated_employee_records(db)
        distributions["company"] = engine.compute_distributions_for_records(
            all_records, datetime.utcnow()
        ).get("company", {})

    return {"snapshot_id": snapshot_id, "distributions": distributions}


@router.get("/personnel-cost")
async def get_personnel_cost(company_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    """Payroll and monthly labour provisions broken down per company, grouped
    by tax regime — the "Planilha de Custo de Funcionário" as a report."""
    records = get_consolidated_employee_records(
        db, company_ids=[company_id] if company_id else None
    )

    by_company = {}
    for record, company in records:
        entry = by_company.setdefault(company.id, {"company": company, "salaries": []})
        entry["salaries"].append(record.salary)

    companies = []
    for entry in by_company.values():
        company = entry["company"]
        salaries = entry["salaries"]
        regime = company.tax_regime or DEFAULT_REGIME
        provisions = sum_provisions((s, regime) for s in salaries)
        companies.append({
            "company_id": company.id,
            "company": company.name,
            "cnpj": company.cnpj,
            "tax_regime": regime,
            "tax_regime_label": REGIME_LABELS.get(regime, regime),
            "rates": rate_breakdown(regime),
            "headcount": len(salaries),
            # Rows with no salary can't be costed; surfaced so a partial
            # payroll is never mistaken for the full one.
            "headcount_without_salary": sum(1 for s in salaries if not s),
            **provisions,
        })

    companies.sort(key=lambda c: (-c["total_cost"], c["company"]))

    all_items = [(r.salary, c.tax_regime or DEFAULT_REGIME) for r, c in records]
    return {
        # Rates differ per regime, so both are published and the UI shows the
        # one that applies to each company.
        "rates": {regime: rate_breakdown(regime) for regime in REGIME_LABELS},
        "regime_labels": REGIME_LABELS,
        "companies": companies,
        "totals": {
            "headcount": len(all_items),
            "headcount_without_salary": sum(1 for s, _r in all_items if not s),
            **sum_provisions(all_items),
        },
    }
