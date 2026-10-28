"""
InfraGuard Duplicate Detection Service
Performs multi-criteria spatial, temporal, and semantic matching to identify duplicate records,
flag uncertain matches for human review, and link re-inspections to deterioration timelines.
"""

import math
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.models.entities import Defect, DefectDuplicate

def haversine_distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate the great-circle distance between two GPS coordinates in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c

class DuplicateDetectionService:
    def __init__(
        self,
        proximity_threshold_meters: float = 15.0,
        uncertain_threshold_meters: float = 35.0,
        temporal_window_hours: float = 72.0
    ):
        self.proximity_threshold_meters = proximity_threshold_meters
        self.uncertain_threshold_meters = uncertain_threshold_meters
        self.temporal_window_hours = temporal_window_hours

    def scan_for_duplicates(
        self,
        db: Session,
        new_defect: Defect
    ) -> List[Dict[str, Any]]:
        """
        Scan existing database defects in the same category within geographic proximity.
        Links confirmed duplicates or uncertain matches without deleting underlying records.
        """
        if new_defect.lat is None or new_defect.lng is None:
            return []

        # Retrieve candidate defects in same infrastructure category
        candidates = db.query(Defect).filter(
            Defect.id != new_defect.id,
            Defect.category == new_defect.category,
            Defect.lat.isnot(None),
            Defect.lng.isnot(None)
        ).all()

        found_matches = []

        for cand in candidates:
            dist = haversine_distance_meters(
                new_defect.lat, new_defect.lng,
                cand.lat, cand.lng
            )

            if dist > self.uncertain_threshold_meters:
                continue

            # Calculate semantic similarity
            type_match = (new_defect.defect_type.lower() == cand.defect_type.lower())
            
            # Temporal delta
            time_delta = abs((new_defect.timestamp - cand.timestamp).total_seconds()) / 3600.0

            # Determine match categorization
            if dist <= self.proximity_threshold_meters and type_match:
                if time_delta <= self.temporal_window_hours:
                    match_type = "confirmed_duplicate"
                    status = "auto_detected"
                    sim_score = round(max(0.70, 1.0 - (dist / self.proximity_threshold_meters) * 0.3), 3)
                    notes = f"High spatial proximity ({dist:.1f}m) and identical defect type within inspection window."
                else:
                    match_type = "historical_reobservation"
                    status = "auto_detected"
                    sim_score = round(max(0.65, 0.90 - (dist / self.proximity_threshold_meters) * 0.2), 3)
                    notes = f"Defect at same physical location observed {time_delta:.1f} hours later. Feeds deterioration timeline."
            else:
                match_type = "uncertain_match"
                status = "auto_detected"
                sim_score = round(max(0.30, 0.65 - (dist / self.uncertain_threshold_meters) * 0.3), 3)
                notes = f"Proximity ({dist:.1f}m) or type variance ('{new_defect.defect_type}' vs '{cand.defect_type}') requires analyst review."

            # Save duplicate link
            duplicate_record = DefectDuplicate(
                primary_defect_id=cand.id,
                duplicate_defect_id=new_defect.id,
                distance_meters=round(dist, 2),
                similarity_score=sim_score,
                match_type=match_type,
                status=status,
                notes=notes
            )
            db.add(duplicate_record)
            
            # If historical reobservation, set parent pointer
            if match_type == "historical_reobservation" and not new_defect.parent_defect_id:
                new_defect.parent_defect_id = cand.id

            found_matches.append({
                "candidate_id": cand.id,
                "distance_meters": round(dist, 2),
                "match_type": match_type,
                "similarity_score": sim_score,
                "notes": notes
            })

        db.commit()
        return found_matches

duplicate_detection_service = DuplicateDetectionService()
