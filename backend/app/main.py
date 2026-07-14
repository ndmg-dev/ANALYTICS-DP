from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize connections here (db, minio)
    from app.db.session import engine
    from app.models import Base
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup here

app = FastAPI(
    title="Mendonça Galvão Workforce Analytics Platform",
    description="Internal API for workforce analytics dashboard",
    version="0.1.0",
    lifespan=lifespan
)

from app.api.imports import router as imports_router
app.include_router(imports_router, prefix="/api/v1")

from app.api.metrics import router as metrics_router
app.include_router(metrics_router, prefix="/api/v1")

from app.api.employees import router as employees_router
app.include_router(employees_router, prefix="/api/v1")

from app.api.quality import router as quality_router
app.include_router(quality_router, prefix="/api/v1")

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
