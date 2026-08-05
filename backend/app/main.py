from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.auth import require_access

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize connections here (db, minio)
    from app.db.session import engine
    from app.models import Base
    from app.db.bootstrap import ensure_schema, backfill_companies
    Base.metadata.create_all(bind=engine)
    # create_all doesn't alter existing tables — patch in newer columns and
    # link legacy imports to their company (see app/db/bootstrap.py).
    ensure_schema(engine)
    backfill_companies()
    yield
    # Cleanup here

app = FastAPI(
    title="Mendonça Galvão Workforce Analytics Platform",
    description="Internal API for workforce analytics dashboard",
    version="0.1.0",
    lifespan=lifespan
)

from app.api.auth import router as auth_router
app.include_router(auth_router, prefix="/api/v1")

from app.api.imports import router as imports_router
app.include_router(imports_router, prefix="/api/v1", dependencies=[Depends(require_access)])

from app.api.metrics import router as metrics_router
app.include_router(metrics_router, prefix="/api/v1", dependencies=[Depends(require_access)])

from app.api.employees import router as employees_router
app.include_router(employees_router, prefix="/api/v1", dependencies=[Depends(require_access)])

from app.api.quality import router as quality_router
app.include_router(quality_router, prefix="/api/v1", dependencies=[Depends(require_access)])

from app.api.companies import router as companies_router
app.include_router(companies_router, prefix="/api/v1", dependencies=[Depends(require_access)])

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "service": "api"}
