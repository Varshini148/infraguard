"""
InfraGuard Risk & Repair Prioritization API Endpoints
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.entities import User, RepairPriority
from backend.app.services.repair_priority import repair_priority_service
from backend.app.security.auth import get_current_user, require_roles

router = APIRouter(prefix="/risk", tags=["Risk & Repair Prioritization"])

@router.post("/recalculate")
def recalculate_priorities(
    category: Optional[str] = None,
    current_user: User = Depends(require_roles(["admin", "analyst"])),
    db: Session = Depends(get_db)
):
    """
    Triggers re-evaluation of multi-factor risk scores and generates
    a newly prioritized repair ranking list.
    """
    results = repair_priority_service.recompute_priorities(db, category=category)
    return {
        "message": "Repair priorities and risk scores recalculated successfully",
        "total_ranked": len(results),
        "rankings": results[:50]
    }

@router.get("/priorities")
def get_repair_priorities(
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Fetch current ordered repair priority ranking list."""
    q = db.query(RepairPriority)
    if category:
        from backend.app.models.entities import Defect
        q = q.join(Defect).filter(Defect.category == category.lower())
    
    priorities = q.order_by(RepairPriority.rank.asc()).limit(limit).all()
    results = []
    for p in priorities:
        import json
        factors = []
        if p.contributing_factors:
            try:
                factors = json.loads(p.contributing_factors) if isinstance(p.contributing_factors, str) else p.contributing_factors
            except Exception:
                pass
        results.append({
            "rank": p.rank,
            "defect_id": p.defect_id,
            "risk_score": p.score,
            "safety_impact": p.safety_impact,
            "recommended_action": p.recommended_action,
            "estimated_urgency_days": p.estimated_urgency_days,
            "contributing_factors": factors,
            "generated_at": p.generated_at.isoformat()
        })
    return results
