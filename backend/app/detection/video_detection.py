"""
InfraGuard Video Processing & Frame Extraction Service
Supports video upload, configurable FPS/interval frame sampling, defect detection
across temporal frames, and video evidence collation.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import cv2
from PIL import Image

from backend.app.detection.image_detection import image_detection_service

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
PROCESSED_DIR = DATA_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

class VideoDetectionService:
    def process_video(
        self,
        video_path: str,
        category: str,
        sampling_interval_sec: float = 1.0,
        max_frames: int = 25,
        confidence_threshold: float = 0.25,
        lat: Optional[float] = None,
        lng: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Extract frames at regular time intervals, execute AI defect detection,
        and collate unique temporal defect events.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video stream from file: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0  # Fallback default
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0

        frame_step = max(1, int(fps * sampling_interval_sec))
        current_frame_idx = 0
        extracted_frames_count = 0

        all_detections = []
        sampled_frame_records = []

        video_stem = Path(video_path).stem
        timestamp_prefix = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        while cap.isOpened() and extracted_frames_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            if current_frame_idx % frame_step == 0:
                extracted_frames_count += 1
                frame_time_sec = round(current_frame_idx / fps, 2)
                
                # Save extracted frame as temp image
                frame_filename = f"{video_stem}_f{current_frame_idx}_{timestamp_prefix}.jpg"
                temp_frame_path = PROCESSED_DIR / frame_filename
                cv2.imwrite(str(temp_frame_path), frame)

                # Run image detection on this frame
                result = image_detection_service.process_image(
                    image_path=str(temp_frame_path),
                    category=category,
                    confidence_threshold=confidence_threshold,
                    lat=lat,
                    lng=lng
                )

                for d in result["detections"]:
                    d["frame_index"] = current_frame_idx
                    d["timestamp_offset_sec"] = frame_time_sec
                    d["frame_evidence"] = result["annotated_filename"]
                    all_detections.append(d)

                sampled_frame_records.append({
                    "frame_index": current_frame_idx,
                    "timestamp_sec": frame_time_sec,
                    "annotated_path": result["annotated_path"],
                    "detections_count": len(result["detections"])
                })

            current_frame_idx += 1

        cap.release()

        return {
            "video_path": video_path,
            "duration_seconds": round(duration, 2),
            "total_video_frames": total_frames,
            "extracted_frames_count": extracted_frames_count,
            "sampling_interval_sec": sampling_interval_sec,
            "all_detections": all_detections,
            "sampled_frames": sampled_frame_records
        }

video_detection_service = VideoDetectionService()
