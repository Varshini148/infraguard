"""
InfraGuard Historical Deterioration Analysis Service
Tracks temporal changes across re-inspections of infrastructure defects.
Evaluates dimensional progression, severity trends, and accounts for visual uncertainty.
Never infers failure from a single snapshot.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import json
from sqlalchemy.orm import Session

from backend.app.models.entities import Defect, DeteriorationTimeline

SEVERITY_WEIGHTS = {
    "minor": 1.0,
    "moderate": 2.0,
    "severe": 3.0,
    "critical": 4.0
}

class DeteriorationService:
    def record_observation(
        self,
        db: Session,
        defect: Defect,
        visible_dimensions: Optional[Dict[str, float]] = None,
        image_ref: Optional[str] = None
    ) -> DeteriorationTimeline:
        """
        Record an inspection snapshot for a defect and recalculate the temporal deterioration trend.
        """
        # Determine existing timeline count
        history = db.query(DeteriorationTimeline).filter(
            DeteriorationTimeline.defect_id == defect.id
        ).order_by(DeteriorationTimeline.inspection_date.asc()).all()

        obs_order = len(history) + 1
        
        # Dimensions estimation if not provided directly
        dims = visible_dimensions
        if not dims and defect.bounding_box:
            try:
                bb = json.loads(defect.bounding_box) if isinstance(defect.bounding_box, str) else defect.bounding_box
                # Approximate physical area in sq.cm assuming standard camera calibration
                dims = {
                    "width_cm": round(bb.get("width", 50) * 0.1, 1),
                    "length_cm": round(bb.get("height", 50) * 0.1, 1),
                    "area_sqcm": round((bb.get("width", 50) * bb.get("height", 50)) * 0.01, 1)
                }
            except Exception:
                dims = {"area_sqcm": 25.0}

        # Determine trend comparing to prior observation
        if obs_order == 1:
            status = "new"
            severity_delta = "baseline_established"
            notes = "First verified observation. Baseline established; requires future re-inspection to confirm trend."
        else:
            prev = history[-1]
            prev_sev_weight = SEVERITY_WEIGHTS.get(prev.severity.lower(), 2.0)
            curr_sev_weight = SEVERITY_WEIGHTS.get(defect.severity.lower(), 2.0)

            prev_area = 25.0
            if prev.visible_dimensions:
                try:
                    prev_dim = json.loads(prev.visible_dimensions) if isinstance(prev.visible_dimensions, str) else prev.visible_dimensions
                    prev_area = prev_dim.get("area_sqcm", 25.0)
                except Exception:
                    pass

            curr_area = dims.get("area_sqcm", 25.0) if dims else 25.0
            area_growth_ratio = (curr_area - prev_area) / max(1.0, prev_area)

            # Evaluate trend
            if curr_sev_weight > prev_sev_weight or area_growth_ratio > 0.15:
                status = "worsening"
                severity_delta = "increased"
                notes = f"Defect showing visible expansion (+{area_growth_ratio*100:.1f}% estimated area) and/or increased severity."
            elif abs(area_growth_ratio) <= 0.15 and curr_sev_weight == prev_sev_weight:
                status = "stable"
                severity_delta = "stable"
                notes = "Defect dimensions and severity remain stable within observational margin of error."
            elif curr_sev_weight < prev_sev_weight and area_growth_ratio < -0.20:
                status = "unresolved"
                severity_delta = "inconclusive"
                notes = "Observed dimensions smaller than previous; likely camera angle or lighting discrepancy. Marked inconclusive."
            else:
                status = "unresolved"
                severity_delta = "unresolved"
                notes = "Defect remains present and active across inspection cycles."

        timeline_record = DeteriorationTimeline(
            defect_id=defect.id,
            inspection_date=defect.timestamp,
            observation_order=obs_order,
            visible_dimensions=json.dumps(dims) if dims else None,
            severity=defect.severity,
            severity_delta=severity_delta,
            status=status,
            notes=notes,
            image_ref=image_ref or (defect.media.file_path if defect.media else None),
            recorded_at=datetime.utcnow()
        )
        db.add(timeline_record)

        # Update defect's overall deterioration status
        defect.deterioration_status = status
        db.commit()

        return timeline_record

    def get_defect_timeline(self, db: Session, defect_id: str) -> Dict[str, Any]:
        """Fetch chronological deterioration timeline and synthesize multi-observation summary."""
        records = db.query(DeteriorationTimeline).filter(
            DeteriorationTimeline.defect_id == defect_id
        ).order_by(DeteriorationTimeline.inspection_date.asc()).all()

        defect = db.query(Defect).filter(Defect.id == defect_id).first()
        if not defect:
            return {"error": "Defect not found"}

        if not records:
            # Baseline entry if timeline record was not created yet
            self.record_observation(db, defect)
            records = db.query(DeteriorationTimeline).filter(
                DeteriorationTimeline.defect_id == defect_id
            ).order_by(DeteriorationTimeline.inspection_date.asc()).all()

        timeline_data = []
        for r in records:
            dims = {}
            if r.visible_dimensions:
                try:
                    dims = json.loads(r.visible_dimensions) if isinstance(r.visible_dimensions, str) else r.visible_dimensions
                except Exception:
                    pass
            timeline_data.append({
                "id": r.id,
                "observation_order": r.observation_order,
                "inspection_date": r.inspection_date.isoformat(),
                "severity": r.severity,
                "severity_delta": r.severity_delta,
                "status": r.status,
                "visible_dimensions": dims,
                "notes": r.notes,
                "image_ref": r.image_ref
            })

        latest_status = records[-1].status if records else "new"
        
        # Urgency recommendation
        if latest_status == "worsening":
            urgency = "High urgency: Active deterioration verified across multiple inspection dates."
        elif latest_status == "stable":
            urgency = "Moderate urgency: Condition stable; continue scheduled monitoring."
        elif latest_status == "inconclusive":
            urgency = "Review recommended: Re-inspect with standardized lighting and distance."
        else:
            urgency = "Baseline established: Monitor during next quarterly cycle."

        return {
            "defect_id": defect.id,
            "category": defect.category,
            "defect_type": defect.defect_type,
            "total_observations": len(records),
            "current_status": latest_status,
            "urgency_recommendation": urgency,
            "timeline": timeline_data
        }

deterioration_service = DeteriorationService()
