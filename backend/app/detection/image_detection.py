"""
InfraGuard Image Detection and Annotation Service
Handles image reading, inference invocation, bounding box rendering,
confidence assessment synthesis, and processed evidence storage.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

from backend.app.detection.model_loader import model_loader

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
PROCESSED_DIR = DATA_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

class ImageDetectionService:
    def process_image(
        self,
        image_path: str,
        category: str,
        confidence_threshold: float = 0.25,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        sensor_vibration: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Runs category-specific defect detection, renders visual annotations,
        evaluates assessed confidence and sensor alignment.
        """
        detections, model_meta = model_loader.detect_defects(
            image_path=image_path,
            category=category,
            confidence_threshold=confidence_threshold
        )

        # Open image to draw annotations
        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        # Choose pastel colors matching category
        cat_colors = {
            "road": "#ef4444",       # Red/coral
            "bridge": "#3b82f6",     # Blue
            "pipeline": "#10b981",   # Mint/Emerald
            "power_grid": "#f59e0b"  # Amber
        }
        box_color = cat_colors.get(category, "#8b5cf6")

        processed_detections = []
        for idx, det in enumerate(detections):
            bb = det["bounding_box"]
            x1, y1 = bb["x"], bb["y"]
            x2, y2 = x1 + bb["width"], y1 + bb["height"]

            # Draw bounding box
            draw.rectangle([x1, y1, x2, y2], outline=box_color, width=3)

            # Draw badge background
            label_text = f"{det['defect_type']} ({int(det['confidence']*100)}%)"
            badge_h = 24
            badge_w = max(120, len(label_text) * 8 + 12)
            draw.rectangle([x1, max(0, y1 - badge_h), x1 + badge_w, y1], fill=box_color)
            draw.text((x1 + 6, max(2, y1 - badge_h + 4)), label_text, fill="#ffffff")

            # Assess multi-factor confidence
            assessed_conf, grade, rationale = self._evaluate_confidence(
                model_conf=det["confidence"],
                sensor_vibration=sensor_vibration,
                has_gps=lat is not None and lng is not None
            )

            det["assessed_confidence"] = assessed_conf
            det["confidence_grade"] = grade
            det["confidence_rationale"] = rationale
            processed_detections.append(det)

        # Save annotated image
        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        annotated_filename = f"annotated_{Path(image_path).stem}_{timestamp_str}.jpg"
        annotated_path = PROCESSED_DIR / annotated_filename
        img.save(annotated_path, "JPEG", quality=90)

        return {
            "annotated_path": str(annotated_path),
            "annotated_filename": annotated_filename,
            "detections": processed_detections,
            "model_meta": model_meta
        }

    def _evaluate_confidence(
        self,
        model_conf: float,
        sensor_vibration: Optional[float],
        has_gps: bool
    ) -> (float, str, str):
        """
        Combines raw model confidence with physical sensor signals and metadata.
        Distinguishes High-confidence, Sensor-supported, Needs review, Insufficient data.
        """
        assessed = model_conf
        rationale_parts = [f"Raw model confidence: {int(model_conf * 100)}%"]

        sensor_boost = False
        if sensor_vibration is not None:
            if sensor_vibration > 1.8:  # Significant vibration anomaly
                assessed = min(0.99, assessed + 0.08)
                sensor_boost = True
                rationale_parts.append(f"Reinforced by vibration anomaly ({sensor_vibration:.2f} m/s²)")
            elif sensor_vibration < 0.4 and assessed > 0.6:
                assessed = max(0.40, assessed - 0.05)
                rationale_parts.append("Vibration baseline is calm; camera prediction remains unboosted")

        if not has_gps:
            assessed = max(0.35, assessed - 0.06)
            rationale_parts.append("Warning: Missing reliable GPS coordinates")

        assessed = round(assessed, 3)

        if sensor_boost and assessed >= 0.75:
            grade = "Sensor-supported"
        elif assessed >= 0.80:
            grade = "High-confidence prediction"
        elif assessed >= 0.50:
            grade = "Needs review"
        else:
            grade = "Insufficient data"

        return assessed, grade, "; ".join(rationale_parts)

image_detection_service = ImageDetectionService()
