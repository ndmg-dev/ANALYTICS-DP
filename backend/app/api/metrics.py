from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Snapshot
from app.services.metrics import MetricsEngine
from app.services.consolidation import get_consolidated_employee_records

router = APIRouter(prefix="/metrics", tags=["Metrics"])

@router.get("/dashboard/{snapshot_id}")
async def get_dashboard_metrics(snapshot_id: int, company: Optional[str] = Query(None), db: Session = Depends(get_db)):
    snapshot = db.get(Snapshot, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    # The current workforce spans every company's own latest completed
    # import, not just this one snapshot — see app/services/consolidation.py.
    records = get_consolidated_employee_records(db, company=company)

    engine = MetricsEngine(db)
    metrics_list = engine.compute_metrics_for_records(records, datetime.utcnow())
    response = dict(metrics_list)
    return {"snapshot_id": snapshot_id, "reference_date": snapshot.reference_date, "metrics": response}

@router.get("/distributions/{snapshot_id}")
async def get_dashboard_distributions(snapshot_id: int, company: Optional[str] = Query(None), db: Session = Depends(get_db)):
    snapshot = db.get(Snapshot, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    records = get_consolidated_employee_records(db, company=company)

    engine = MetricsEngine(db)
    distributions = engine.compute_distributions_for_records(records, datetime.utcnow())

    return {"snapshot_id": snapshot_id, "distributions": distributions}
