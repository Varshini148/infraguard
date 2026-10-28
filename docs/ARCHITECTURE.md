# InfraGuard System Architecture & Data Flow

## 1. High-Level Architecture

InfraGuard is an end-to-end, authority-focused AI platform designed for predictive infrastructure maintenance across Roads, Bridges, Pipelines, and Power Grids.

```mermaid
flowchart TD
    subgraph Data_Ingestion ["1. Multimodal Data Ingestion"]
        IMG["Camera Images / UAV Video"]
        SNS["GPS / Accelerometer / Vibration CSV"]
    end

    subgraph Core_AI_and_Fusion ["2. AI Detection & Sensor Fusion"]
        YOLO["YOLOv8 Category Models<br/>(Road, Bridge, Pipe, Grid)"]
        AUKF["Adaptive UKF (AUKF)<br/>(5-State Kinematics)"]
    end

    subgraph Synthesis_and_Intelligence ["3. Intelligence & Temporal Correlation"]
        CONF["Confidence Assessment Engine<br/>(Model + Physical Telemetry)"]
        DUP["Spatial Duplicate Detection<br/>(Haversine < 15m)"]
        DET["Historical Deterioration Engine<br/>(Observation Timelines)"]
        RISK["Explainable Risk Scorer (0-100)<br/>& Repair Prioritization"]
    end

    subgraph Authority_Presentation ["4. Authority Interface & Exports"]
        DASH["Authority Dashboard & KPIs"]
        MAP["Leaflet Map (Tamil Nadu, India)"]
        REP["Audit Reports (CSV & PDF)"]
        API["FastAPI REST Endpoints"]
    end

    IMG --> YOLO
    SNS --> AUKF
    YOLO --> CONF
    AUKF --> CONF
    CONF --> DUP
    DUP --> DET
    DET --> RISK
    RISK --> API
    API --> DASH
    API --> MAP
    API --> REP
```

---

## 2. Component Directory Architecture

```
infraguard/
├── frontend/                     # Pure HTML5 / CSS3 / JavaScript
│   ├── index.html                # Authority Dashboard
│   ├── pages/                    # 10 Dedicated Module Interfaces
│   ├── css/                      # Pastel Theme, Dashboard & Responsive Styles
│   └── js/                       # Unified API Client & Module Scripts
├── backend/                      # Python FastAPI Architecture
│   └── app/
│       ├── main.py               # Application entrypoint & static mount
│       ├── api/                  # Auth, Detection, Sensors, Infra, Risk, Reports
│       ├── models/               # SQLAlchemy ORM Schema Definitions
│       ├── schemas/              # Pydantic v2 Serialization Models
│       ├── database/             # SQLite WAL connection & seeder
│       ├── detection/            # Model loader & video frame extractor
│       ├── sensor_fusion/        # 5-State Adaptive Unscented Kalman Filter
│       ├── services/             # Duplicate detection, Deterioration, Risk
│       ├── reporting/            # RFC 4180 CSV & ReportLab PDF generators
│       └── security/             # PBKDF2 Password Hashing & HS256 JWT
├── data/                         # Uploads, processed imagery & datasets
├── models/                       # Model documentation & weights directory
├── tests/                        # Full Pytest Test Suite
└── docs/                         # Technical documentation & formulations
```

---

## 3. Database Entity Relationship Model

```mermaid
erDiagram
    USERS ||--o{ AUDIT_LOGS : performs
    USERS ||--o{ INSPECTION_SESSIONS : inspects
    INFRASTRUCTURE_ASSETS ||--o{ INSPECTION_SESSIONS : contains
    INFRASTRUCTURE_ASSETS ||--o{ DEFECTS : locates
    INSPECTION_SESSIONS ||--o{ MEDIA_RECORDS : captures
    INSPECTION_SESSIONS ||--o{ SENSOR_DATASETS : logs
    SENSOR_DATASETS ||--o{ SENSOR_MEASUREMENTS : samples
    SENSOR_DATASETS ||--o{ AUKF_STATE_ESTIMATES : estimates
    MEDIA_RECORDS ||--o{ DEFECTS : evidences
    DEFECTS ||--o{ DEFECT_DUPLICATES : relates
    DEFECTS ||--o{ DETERIORATION_TIMELINE : tracks
    DEFECTS ||--o{ REPAIR_PRIORITIES : schedules
```
