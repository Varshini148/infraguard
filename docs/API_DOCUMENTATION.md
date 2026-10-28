# InfraGuard REST API Documentation

The InfraGuard backend exposes a comprehensive, RESTful OpenAPI specification available interactively at `/docs` or `/redoc`.

---

## 1. Authentication & RBAC

### `POST /api/auth/login`
- **Description:** Authenticate municipal personnel and return a signed HS256 JWT access token.
- **Request Body:**
  ```json
  {
    "username": "admin",
    "password": "admin123"
  }
  ```
- **Response:**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@infraguard.gov.in",
      "full_name": "Chief Infrastructure Engineer",
      "role": "admin"
    }
  }
  ```

---

## 2. Multimodal AI Detection

### `GET /api/detection/models`
- **Description:** Returns live status, licenses, and supported classes for all 4 category models (`road`, `bridge`, `pipeline`, `power_grid`).

### `POST /api/detection/image`
- **Content-Type:** `multipart/form-data`
- **Fields:**
  - `file`: Image file (JPG, PNG, WEBP)
  - `category`: `road` | `bridge` | `pipeline` | `power_grid`
  - `lat`: Optional latitude float
  - `lng`: Optional longitude float
  - `sensor_vibration`: Optional float ($m/s^2$)
- **Response:**
  ```json
  {
    "media_id": 12,
    "annotated_path": "/processed/annotated_img_20261028.jpg",
    "total_detections": 1,
    "detections": [
      {
        "defect_type": "D40: Pothole",
        "category": "road",
        "confidence": 0.91,
        "assessed_confidence": 0.97,
        "confidence_grade": "Sensor-supported",
        "severity": "critical"
      }
    ],
    "saved_defect_ids": ["DEF-20261028-RD01"]
  }
  ```

### `POST /api/detection/video`
- **Content-Type:** `multipart/form-data`
- **Fields:**
  - `file`: Video file (MP4, AVI, MOV)
  - `category`: Domain string
  - `sampling_interval_sec`: Frame sampling rate (e.g. 1.0)
  - `max_frames`: Frame upper limit (e.g. 15)

---

## 3. Sensors & AUKF Sensor Fusion

### `POST /api/sensors/upload`
- **Content-Type:** `multipart/form-data`
- **Fields:** `file` (CSV format)
- **Response:** Contains summary of samples, identified vibration anomalies, and initial 50 state estimates.

### `GET /api/sensors/generate-sample-csv`
- **Description:** Returns a synthetic 10 Hz survey trajectory along NH 544 (Salem-Coimbatore, Tamil Nadu) with simulated pothole and expansion joint vibration spikes.

---

## 4. Infrastructure & Defect Registry

### `GET /api/infrastructure/defects`
- **Query Parameters:** `category`, `severity`, `risk_level`, `verification_status`, `sensor_supported`, `has_coords_only`, `limit`, `offset`.

### `PATCH /api/infrastructure/defects/{defect_id}/verification`
- **Request Body:**
  ```json
  {
    "verification_status": "verified_by_inspection",
    "verification_notes": "Ground truth confirmed by Field Inspector."
  }
  ```

### `PATCH /api/infrastructure/defects/{defect_id}/coordinates?lat=11.4883&lng=77.8683`
- **Description:** Authorized manual coordinate adjustment for field imagery.

### `GET /api/infrastructure/geojson`
- **Description:** Returns defects formatted as RFC 7946 GeoJSON `FeatureCollection`.

---

## 5. Risk & Repair Prioritization

### `POST /api/risk/recalculate`
- **Description:** Triggers re-evaluation of multi-factor risk scores and updates repair rankings.

### `GET /api/risk/priorities`
- **Description:** Returns ordered repair schedule with ranking rationales and safety impact descriptions.

---

## 6. Official Reports

### `GET /api/reports/summary`
- **Description:** Returns actual database-backed KPI statistics.

### `GET /api/reports/csv`
- **Description:** Downloads RFC 4180 CSV export of filtered records.

### `GET /api/reports/pdf`
- **Description:** Generates and streams official PDF inspection report.
