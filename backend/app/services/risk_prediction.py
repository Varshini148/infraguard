"""
InfraGuard Risk Prediction Service
Computes multi-factor risk scores (0-100) combining defect severity, asset importance,
deterioration progression, sensor confirmation, and temporal exposure.
Provides transparent contributing factors and safety impact explanations.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from backend.app.models.entities import Defect, InfrastructureAsset

SEVERITY_POINTS = {
    "critical": 95.0,
    "severe": 75.0,
    "moderate": 50.0,
    "minor": 25.0
}

IMPORTANCE_POINTS = {
    "critical": 95.0,
    "high": 75.0,
    "medium": 50.0,
    "low": 25.0
}

TREND_POINTS = {
    "worsening": 90.0,
    "unresolved": 65.0,
    "new": 50.0,
    "inconclusive": 45.0,
    "stable": 40.0
}

class RiskPredictionService:
    def calculate_risk(
        self,
        db: Session,
        defect: Defect,
        asset: Optional[InfrastructureAsset] = None
    ) -> Dict[str, Any]:
        """
        Evaluate comprehensive multi-criteria risk score.
        Returns risk score (0-100), risk level, itemized contributing factors,
        and recommendations.
        """
        if not asset and defect.asset_id:
            asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == defect.asset_id).first()

        # Factor 1: Defect Severity (35%)
        sev_pts = SEVERITY_POINTS.get(defect.severity.lower(), 50.0)
        c_sev = 0.35 * sev_pts

        # Factor 2: Asset Importance (20%)
        imp_level = asset.importance_level.lower() if asset else "medium"
        imp_pts = IMPORTANCE_POINTS.get(imp_level, 50.0)
        c_imp = 0.20 * imp_pts

        # Factor 3: Deterioration Trend (20%)
        trend_status = defect.deterioration_status.lower() if defect.deterioration_status else "new"
        trend_pts = TREND_POINTS.get(trend_status, 50.0)
        c_trend = 0.20 * trend_pts

        # Factor 4: Assessed Confidence & Sensor Reinforcement (15%)
        conf_pts = defect.assessed_confidence * 100.0 if defect.assessed_confidence else 50.0
        if defect.sensor_supported:
            conf_pts = min(100.0, conf_pts + 15.0)
        c_conf = 0.15 * conf_pts

        # Factor 5: Age / Exposure Time (10%)
        days_open = max(1, (datetime.utcnow() - defect.timestamp).days)
        age_factor = min(1.0, days_open / 90.0)
        age_pts = age_factor * 100.0
        c_age = 0.10 * age_pts

        total_risk = c_sev + c_imp + c_trend + c_conf + c_age
        total_risk = round(min(100.0, max(0.0, total_risk)), 1)

        # Risk Classification
        if total_risk >= 80.0:
            risk_level = "critical"
            urgency_days = 3
            rec = "Immediate priority: schedule structural inspection and temporary mitigation within 72 hours."
        elif total_risk >= 65.0:
            risk_level = "high"
            urgency_days = 7
            rec = "High priority: schedule engineering repair crew within 7 days."
        elif total_risk >= 45.0:
            risk_level = "medium"
            urgency_days = 21
            rec = "Moderate priority: include in next routine maintenance cycle (within 21 days)."
        else:
            risk_level = "low"
            urgency_days = 60
            rec = "Low risk: monitor condition during routine quarterly survey."

        factors = [
            f"Defect Severity ({defect.severity.title()}): +{c_sev:.1f} pts",
            f"Asset Importance ({imp_level.title()}): +{c_imp:.1f} pts",
            f"Deterioration Trend ({trend_status.title()}): +{c_trend:.1f} pts",
            f"Evidence Confidence & Sensor ({defect.confidence_grade}): +{c_conf:.1f} pts",
            f"Exposure Duration ({days_open} days open): +{c_age:.1f} pts"
        ]

        if defect.sensor_supported:
            factors.append("AUKF Sensor Fusion: Confirmed vibration/kinematic anomaly reinforcement")

        # Persist to defect record
        defect.risk_score = total_risk
        defect.risk_level = risk_level
        defect.estimated_urgency_days = urgency_days
        db.commit()

        return {
            "defect_id": defect.id,
            "risk_score": total_risk,
            "risk_level": risk_level,
            "contributing_factors": factors,
            "estimated_urgency_days": urgency_days,
            "recommended_action": rec,
            "limitations_notice": "Decision support metric based on available sensor and visual telemetry. Professional engineering assessment required before major structural intervention."
        }

risk_prediction_service = RiskPredictionService()
