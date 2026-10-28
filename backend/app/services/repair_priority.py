"""
InfraGuard Repair Prioritization Service
Generates ranked repair schedules across infrastructure defects.
Synthesizes risk scores, safety impacts, resource limits, and outputs explainable rationales.
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.models.entities import Defect, RepairPriority, InfrastructureAsset
from backend.app.services.risk_prediction import risk_prediction_service

class RepairPriorityService:
    def recompute_priorities(
        self,
        db: Session,
        category: Optional[str] = None,
        max_urgent_slots: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Calculates priority ordering for all active/unverified defects.
        Outputs rank, rationale, safety impact, and recommended action.
        """
        query = db.query(Defect).filter(
            Defect.verification_status != "rejected"
        )
        if category:
            query = query.filter(Defect.category == category)

        defects = query.all()

        # Recalculate risk for each defect
        scored_items = []
        for d in defects:
            risk_info = risk_prediction_service.calculate_risk(db, d)
            scored_items.append((d, risk_info))

        # Sort descending by risk score, then confidence
        scored_items.sort(
            key=lambda item: (item[1]["risk_score"], item[0].assessed_confidence),
            reverse=True
        )

        # Clear existing priority records for current scope
        if category:
            subq = db.query(Defect.id).filter(Defect.category == category)
            db.query(RepairPriority).filter(RepairPriority.defect_id.in_(subq)).delete(synchronize_session=False)
        else:
            db.query(RepairPriority).delete()

        ranked_results = []
        for rank, (defect, risk_info) in enumerate(scored_items, start=1):
            score = risk_info["risk_score"]
            factors = risk_info["contributing_factors"]

            # Safety impact explanation
            if score >= 80.0:
                safety = "Critical Life-Safety & Service Disruption Hazard"
                rationale = (
                    f"Rank #{rank}: Critical risk ({score}/100). {defect.severity.title()} {defect.defect_type} "
                    f"showing '{defect.deterioration_status}' progression. Immediate field containment required."
                )
            elif score >= 65.0:
                safety = "High Public Safety & Asset Accelerated Decay Concern"
                rationale = (
                    f"Rank #{rank}: High risk ({score}/100). Severe defect requiring prompt intervention "
                    f"within {risk_info['estimated_urgency_days']} days to prevent structural escalation."
                )
            elif score >= 45.0:
                safety = "Moderate Operational & Maintenance Impact"
                rationale = (
                    f"Rank #{rank}: Moderate risk ({score}/100). Standard maintenance workflow within scheduled cycle."
                )
            else:
                safety = "Low Immediate Operational Hazard"
                rationale = (
                    f"Rank #{rank}: Low risk ({score}/100). Routine monitoring; repair deferred until next area resurfacing."
                )

            # Store in RepairPriority model
            p_record = RepairPriority(
                defect_id=defect.id,
                rank=rank,
                score=score,
                contributing_factors=json.dumps(factors),
                safety_impact=safety,
                resource_constraint_notes=f"Assigned slot {rank} of available dispatch capacity",
                recommended_action=risk_info["recommended_action"],
                estimated_urgency_days=risk_info["estimated_urgency_days"],
                generated_at=datetime.utcnow()
            )
            db.add(p_record)

            # Update defect record
            defect.repair_priority_rank = rank
            defect.repair_priority_rationale = rationale

            ranked_results.append({
                "rank": rank,
                "defect_id": defect.id,
                "category": defect.category,
                "defect_type": defect.defect_type,
                "severity": defect.severity,
                "risk_score": score,
                "risk_level": risk_info["risk_level"],
                "safety_impact": safety,
                "rationale": rationale,
                "estimated_urgency_days": risk_info["estimated_urgency_days"],
                "recommended_action": risk_info["recommended_action"]
            })

        db.commit()
        return ranked_results

repair_priority_service = RepairPriorityService()
