# InfraGuard AI Model Registry & Weights Guide

This directory documents the category-specific AI models used by InfraGuard to monitor roads, bridges, pipelines, and power grids.

---

## Model Specifications

| Infrastructure Domain | Model Key | Base Architecture | Dataset / Source | License |
| :--- | :--- | :--- | :--- | :--- |
| **Roads** | `infraguard-rdd-yolov8n` | YOLOv8n (Detection) | [Sekilab RDD2020 & N-RDD2024](https://github.com/sekilab/RoadDamageDetector) | CC BY-SA 4.0 |
| **Bridges / Concrete** | `infraguard-bridge-yolov8n` | YOLOv8n (Detection) | [SDNET2018 & IBM Cracks](https://www.sdnetdata.com/) | MIT License |
| **Pipelines / Sewer** | `infraguard-pipeline-yolov8n` | YOLOv8n (Detection) | [TUBERS & Sewer-ML](https://tubers-project.eu/) | CC BY-NC 4.0 |
| **Power Grids** | `infraguard-powergrid-yolov8n` | YOLOv8n (Detection) | [InsPLAD & Roboflow Power](https://data.mendeley.com/datasets/5n3fjgvfyz/1) | CC BY 4.0 |

---

## Weights Directory Structure

Place trained PyTorch `.pt` model weights inside `models/weights/`:

```
models/
└── weights/
    ├── road_yolov8n.pt        # Trained Road Damage Detector weights
    ├── bridge_yolov8n.pt      # Concrete Bridge Crack & Spall weights
    ├── pipeline_yolov8n.pt    # Pipeline / Sewer internal inspection weights
    └── powergrid_yolov8n.pt   # Transmission Line & Insulator weights
```

---

## Transparent Execution Fallback

When weights files are not present or Ultralytics/Torch is not loaded, InfraGuard automatically activates its deterministic **Computer Vision Anomaly Locator** (`demo_vision_fallback`).
- The fallback identifies high-contrast luminance and spatial edge distress gradients in images.
- All inferences produced by this engine are explicitly labeled in the API, UI badges, and reports as `demo_vision_fallback`.
- The system never fakes or silently swaps models.

---

## Training Instructions

To train a custom YOLOv8 model for any category:
```bash
# 1. Install Ultralytics
pip install ultralytics

# 2. Train on benchmark annotations
yolo detect train data=datasets/rdd2020.yaml model=yolov8n.pt epochs=50 imgsz=640

# 3. Export weights to InfraGuard
cp runs/detect/train/weights/best.pt models/weights/road_yolov8n.pt
```
