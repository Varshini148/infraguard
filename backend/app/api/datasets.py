"""
InfraGuard Dataset Registry API Endpoints
"""

import json
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.entities import DatasetRegistry, User
from backend.app.services.dataset_registry import initialize_dataset_registry
from backend.app.security.auth import get_current_user, require_roles

router = APIRouter(prefix="/datasets", tags=["Dataset Registry"])

@router.get("")
def list_datasets(category: Optional[str] = None, db: Session = Depends(get_db)):
    """Fetch all registered benchmark and training datasets with licensing metadata."""
    q = db.query(DatasetRegistry)
    if category:
        q = q.filter(DatasetRegistry.category == category.lower())
    records = q.all()

    results = []
    for r in records:
        classes = []
        if r.classes:
            try:
                classes = json.loads(r.classes) if isinstance(r.classes, str) else r.classes
            except Exception:
                pass
        results.append({
            "id": r.id,
            "name": r.name,
            "category": r.category,
            "source_url": r.source_url,
            "license": r.license,
            "classes": classes,
            "geographic_coverage": r.geographic_coverage,
            "annotation_format": r.annotation_format,
            "download_status": r.download_status,
            "sample_file_count": r.sample_file_count,
            "suitability_notes": r.suitability_notes,
            "updated_at": r.updated_at.isoformat()
        })
    return results

@router.post("/seed")
def seed_datasets(db: Session = Depends(get_db)):
    """Initialize official candidate datasets if not already present."""
    initialize_dataset_registry(db)
    return {"message": "Dataset registry synchronized successfully"}

@router.patch("/{dataset_id}/status")
def update_dataset_status(
    dataset_id: int,
    status: str,
    current_user: User = Depends(require_roles(["admin", "analyst"])),
    db: Session = Depends(get_db)
):
    """Update dataset import or verification status."""
    ds = db.query(DatasetRegistry).filter(DatasetRegistry.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    ds.download_status = status
    ds.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Status updated", "id": ds.id, "status": ds.download_status}
