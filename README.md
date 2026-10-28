# InfraGuard — AI Multi-Infrastructure Monitoring & Predictive Maintenance Platform

**InfraGuard** is a functional, authority-focused artificial intelligence platform designed to monitor, inspect, and prioritize predictive maintenance across four critical infrastructure sectors:
1. **Roads:** Potholes, longitudinal/transverse cracks, alligator cracking, lane degradation.
2. **Bridges:** Concrete cracks, spalling, exposed rebar, efflorescence, joint deterioration.
3. **Pipelines:** Circumferential cracks, longitudinal fractures, joint displacements, corrosion.
4. **Power Grids:** Broken insulator discs, flashover burn marks, conductor strand severance, pylon rust.

---

## Core Operational Workflow

```
Camera & Sensor Data
        ↓
Category-Specific AI Detection (YOLOv8)
        ↓
Adaptive Unscented Kalman Filter (AUKF) Sensor Fusion
        ↓
Multi-Factor Confidence Assessment
        ↓
Spatial Proximity Duplicate Detection (< 15m)
        ↓
Historical Deterioration Timeline Analysis
        ↓
Transparent Risk Scoring (0–100)
        ↓
Explainable Repair Prioritization Ranking
        ↓
Authority Dashboard, Interactive Leaflet Map & Official PDF/CSV Reports
```

---

## Technology Stack

- **Frontend:** Pure HTML5, CSS3 (pastel theme, WCAG AAA compliant), Vanilla JavaScript (no fragile node dependencies required).
- **Backend:** Python 3.12, FastAPI, Uvicorn, Pydantic v2.
- **Database:** SQLite with Write-Ahead Logging (WAL) enabled, modular SQLAlchemy ORM portable to PostgreSQL/PostGIS.
- **AI & Computer Vision:** YOLOv8 model loader supporting PyTorch weights with transparent morphological feature extraction fallback (`demo_vision_fallback`).
- **Sensor Fusion:** 5-State Adaptive Unscented Kalman Filter (AUKF) with non-linear kinematics and Sage-Husa covariance matching.
- **Geospatial Mapping:** Leaflet & OpenStreetMap defaulted to Tamil Nadu, India (`[11.1271, 78.6569]`).
- **Reporting:** RFC 4180 CSV and ReportLab PDF document compilation.
- **Testing:** Pytest with 100% pass rate.

---

## Project Structure

```
infraguard/
├── frontend/
│   ├── index.html                   # Authority Overview Dashboard
│   ├── pages/
│   │   ├── detection.html           # Multi-AI Image & Video Ingestion
│   │   ├── sensor-analysis.html     # Sensor Telemetry & AUKF Fusion
│   │   ├── infrastructure-map.html  # Leaflet Geospatial Map (Tamil Nadu)
│   │   ├── records.html             # Defect Records & Field Verification
│   │   ├── deterioration.html       # Deterioration Progression Timelines
│   │   ├── risk-prioritization.html # Risk Scoring & Repair Schedules
│   │   ├── dataset-management.html  # Benchmark Dataset Registry
│   │   ├── model-status.html        # AI Weights & Limitations
│   │   ├── reports.html             # CSV & PDF Audit Exporter
│   │   └── settings.html            # RBAC Staff Management & Diagnostics
│   ├── css/
│   │   ├── style.css                # Base theme & design system
│   │   ├── dashboard.css            # Charts, KPIs & timelines
│   │   └── responsive.css           # Desktop, tablet & mobile rules
│   └── js/
│       ├── api.js                   # Unified API client & Auth
│       ├── dashboard.js             # Charts & map widget
│       ├── detection.js             # Detection & frame extractor
│       ├── map.js                   # Interactive Leaflet logic
│       └── sensors.js               # AUKF telemetry streaming
├── backend/
│   └── app/
│       ├── main.py                  # FastAPI Application & static router
│       ├── api/                     # REST Endpoint routers
│       ├── models/                  # SQLAlchemy ORM Database Schemas
│       ├── schemas/                 # Pydantic v2 domain schemas
│       ├── database/                # Connection management & seed script
│       ├── detection/               # Model loader & frame extractor
│       ├── sensor_fusion/           # 5-State Adaptive Unscented Kalman Filter
│       ├── services/                # Duplicates, deterioration, risk, priority
│       ├── reporting/               # ReportLab PDF & CSV generation
│       └── security/                # PBKDF2 Hashing & HS256 JWT
├── data/                            # Uploads, processed imagery, sample traces
├── models/
│   └── README.md                    # Weights acquiring & training manual
├── tests/                           # Complete Pytest test suite
├── docs/                            # Formulations, architecture, API & deployment guides
│   ├── DEPLOYMENT_GUIDE.md          # Complete cloud and container deployment manual
│   ├── ARCHITECTURE.md              # System design & database relationships
│   ├── AUKF_FORMULATION.md          # 5-State AUKF sensor fusion mathematical theory
│   ├── API_DOCUMENTATION.md         # REST API schema documentation
│   └── TEST_RESULTS.md              # Test execution logs
├── Dockerfile                       # Production Python 3.12-slim non-root container
├── docker-compose.yml               # Local & VPS container stack with persistent volume
├── Procfile                         # Cloud PaaS runner (Railway, Heroku, Dokku)
├── render.yaml                      # Render Blueprint infrastructure-as-code
├── pytest.ini                       # Test configuration
├── .env.example                     # Production environment template
├── .gitignore                       # Clean Git configuration
├── requirements.txt                 # Pinned dependencies
└── README.md                        # Master manual
```

---

## Quickstart Guide for Windows PowerShell

### 1. Prerequisites
- Windows 10 / 11
- Python 3.10+ installed and added to your `PATH`

### 2. Open Windows PowerShell
Navigate to the project root directory:
```powershell
cd C:\Users\arulk\OneDrive\Desktop\infraguard
```

### 3. Create & Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy the example configuration:
```powershell
Copy-Item .env.example .env
```

### 6. Run the Test Suite
Verify that all unit and integration tests pass:
```powershell
python -m pytest tests/ -v
```

### 7. Launch the Application
Start the unified FastAPI server:
```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your web browser and navigate to:
- **Authority Portal:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Redoc API Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Production & Online Cloud Deployment

InfraGuard is prepared for cloud deployment out-of-the-box. Full instructions are available in the [Deployment Guide](file:///docs/DEPLOYMENT_GUIDE.md).

### Quick Deployment via Docker Compose
Run the entire platform in an isolated container with persistent volume storage:
```bash
docker-compose up -d --build
```
Verify the container health:
```bash
curl -f http://localhost:8000/api/health
```

### Deploying to Render.com
1. Connect your repository to Render.
2. Select **New Blueprint** — Render will automatically read `render.yaml` and configure the Python web service with persistent disk storage.

### Deploying to Railway / Fly.io / Heroku
InfraGuard includes a root `Procfile` configured for dynamic `$PORT` assignment:
```procfile
web: uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT --workers 2
```

---

## Default Authority Credentials

InfraGuard automatically seeds three authorized operational accounts:

| Role | Username | Password | Purpose |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `admin123` | Full system control, priority recalculations, staff creation |
| **Field Inspector** | `inspector` | `inspector123` | Field verification, inspection logging, coordinate entry |
| **Data Analyst** | `analyst` | `analyst123` | Sensor analysis, reports export, duplicate review |

---

## Verified Benchmark Datasets Registry

| Infrastructure Category | Benchmark Dataset | Source Repository | License | Annotation Format |
| :--- | :--- | :--- | :--- | :--- |
| **Roads** | RDD2020 | Mendeley Data | CC BY 4.0 | Pascal VOC / YOLO |
| **Roads** | Sekilab RDD | GitHub | CC BY-SA 4.0 | YOLO Format |
| **Roads** | N-RDD2024 | Mendeley Data | CC BY 4.0 | COCO / YOLO |
| **Bridges** | IBM Cracks | GitHub | CDLA-Permissive | COCO Format |
| **Bridges** | SDNET2018 | SDNET Consortium | MIT License | Classification & BBox |
| **Pipelines** | TUBERS | EU Project | CC BY-NC 4.0 | CCTV Frame Metadata |
| **Pipelines** | Sewer-ML | Aalborg Univ | Academic Research | Multi-Label Class |
| **Power Grids** | InsPLAD | Mendeley Data | CC BY 4.0 | Pascal VOC |
| **Power Grids** | Roboflow Power | Roboflow Universe | CC BY 4.0 | YOLOv8 |

---

## Statutory Engineering Notice & Limitations

1. **Decision Support:** InfraGuard is an automated computer vision and sensor telemetry decision-support system. It assists municipal maintenance triage and resource allocation.
2. **Certification Disclaimer:** Inferences, risk rankings, and estimated urgencies do not constitute professional structural engineering certification or guaranteed failure predictions.
3. **Mandatory Field Inspection:** Mandatory on-site structural inspections by licensed civil/structural engineers are required before major capital or structural interventions.
