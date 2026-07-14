from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import get_db
from app.models import Snapshot, MetricResult
from app.services.metrics import MetricsEngine

router = APIRouter(prefix="/metrics", tags=["Metrics"])

@router.get("/dashboard/{snapshot_id}")
async def get_dashboard_metrics(snapshot_id: int, db: Session = Depends(get_db)):
    snapshot = db.get(Snapshot, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
        
    stmt = select(MetricResult).where(MetricResult.snapshot_id == snapshot_id)
    metrics = db.scalars(stmt).all()
    
    if not metrics:
        # If not calculated, try to compute them now (fallback for MVP)
        engine = MetricsEngine(db)
        engine.compute_and_save_metrics(snapshot_id)
        metrics = db.scalars(stmt).all()

    response = { m.metric_id: m.metric_value for m in metrics }
    return {"snapshot_id": snapshot_id, "reference_date": snapshot.reference_date, "metrics": response}

@router.get("/distributions/{snapshot_id}")
async def get_dashboard_distributions(snapshot_id: int, db: Session = Depends(get_db)):
    snapshot = db.get(Snapshot, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
        
    engine = MetricsEngine(db)
    distributions = engine.get_distributions(snapshot_id)
    
    return {"snapshot_id": snapshot_id, "distributions": distributions}
