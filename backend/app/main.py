"""
InfraGuard Main Application Entry Point
FastAPI backend powering multimodal AI infrastructure monitoring, AUKF sensor fusion,
deterioration analysis, and authority reporting.
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from backend.app.database.connection import engine, Base, SessionLocal
from backend.app.database.seed import seed_database
from backend.app.api.auth import router as auth_router
from backend.app.api.detection import router as detection_router
from backend.app.api.sensors import router as sensors_router
from backend.app.api.infrastructure import router as infrastructure_router
from backend.app.api.risk import router as risk_router
from backend.app.api.datasets import router as datasets_router
from backend.app.api.reports import router as reports_router

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
UPLOADS_DIR = DATA_DIR / "uploads"
PROCESSED_DIR = DATA_DIR / "processed"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables
    Base.metadata.create_all(bind=engine)
    
    # Run seeder for default users, assets, sample data, and dataset registry
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

    yield

app = FastAPI(
    title="InfraGuard Infrastructure Monitoring & Predictive Maintenance Platform",
    description="Multimodal AI-driven defect detection, AUKF sensor fusion, deterioration timelines, and risk prioritization for Roads, Bridges, Pipelines, and Power Grids.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
if allowed_origins_env == "*":
    origins = ["*"]
else:
    origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(auth_router, prefix="/api")
app.include_router(detection_router, prefix="/api")
app.include_router(sensors_router, prefix="/api")
app.include_router(infrastructure_router, prefix="/api")
app.include_router(risk_router, prefix="/api")
app.include_router(datasets_router, prefix="/api")
app.include_router(reports_router, prefix="/api")

# Static Storage Mounts
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.mount("/processed", StaticFiles(directory=str(PROCESSED_DIR)), name="processed")

# Static Frontend Mounts
if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
    if (FRONTEND_DIR / "pages").exists():
        app.mount("/pages", StaticFiles(directory=str(FRONTEND_DIR / "pages")), name="pages")

@app.get("/api/health")
def health_check():
    """System health check and operational status."""
    return {
        "status": "healthy",
        "system": "InfraGuard",
        "version": "1.0.0",
        "mode": os.getenv("INFRAGUARD_ENV", "production")
    }

@app.get("/")
@app.get("/index.html")
def serve_index():
    """Serve the root dashboard UI."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "InfraGuard API operational. Access /api/docs for API documentation."}

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("API_PORT", 8000)))
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=False)
