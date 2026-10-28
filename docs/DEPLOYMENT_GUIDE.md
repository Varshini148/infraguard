# InfraGuard Production Deployment Guide

This guide provides end-to-end instructions for deploying the **InfraGuard** AI-Powered Multi-Infrastructure Monitoring & Predictive Maintenance Platform to online cloud environments, Docker containers, and virtual private servers (VPS).

---

## Architecture Overview

```
                      +-----------------------------+
                      |   Cloud Domain / Browser    |
                      |  (HTML5 / CSS / JS / Maps)  |
                      +--------------+--------------+
                                     | HTTPS (Port 443)
                                     v
                      +-----------------------------+
                      |     Reverse Proxy / PaaS    |
                      |    (Nginx / Cloudflare)     |
                      +--------------+--------------+
                                     | HTTP (Port 8000 / $PORT)
                                     v
                      +-----------------------------+
                      |       FastAPI Backend       |
                      |   (Uvicorn ASGI Runner)     |
                      +------+---------------+------+
                             |               |
              +--------------+               +--------------+
              v                                             v
     +-----------------+                           +-----------------+
     | Persistent Disk |                           |   AI Inference  |
     |   - SQLite DB   |                           |   - YOLOv8      |
     |   - Uploads     |                           |   - Fallback    |
     |   - Reports     |                           |   - AUKF Fusion |
     +-----------------+                           +-----------------+
              OR
     +-----------------+
     | PostgreSQL DB   |
     |  (Optional)     |
     +-----------------+
```

- **Frontend:** Pure HTML/CSS/Vanilla JavaScript served directly via FastAPI static file routing (`/`, `/css`, `/js`, `/pages`). No Node.js build step or npm compilation is required in production.
- **Backend:** FastAPI with Uvicorn/Gunicorn ASGI runners.
- **Database:** Modular SQLAlchemy architecture supporting SQLite (with Write-Ahead Logging) and PostgreSQL/PostGIS.
- **AI Inference:** Modular YOLOv8 engine with an automated visual-feature fallback that runs smoothly on CPU-only cloud instances without requiring a dedicated GPU.

---

## Environment Variables Reference

Configure these environment variables in your cloud hosting provider's dashboard or in a `.env` file:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `INFRAGUARD_ENV` | `production` | Environment mode (`production` or `development`) |
| `API_HOST` | `0.0.0.0` | Host binding for Uvicorn server |
| `PORT` / `API_PORT` | `8000` | Port for incoming HTTP requests (auto-assigned by Render/Railway/Heroku) |
| `SECRET_KEY` | *(Must generate)* | Cryptographic secret for JWT authentication tokens (min 32 chars) |
| `DATABASE_URL` | `sqlite:///./data/infraguard.db` | SQLAlchemy database connection URI |
| `ALLOWED_ORIGINS` | `*` | Comma-separated list of allowed CORS origins (e.g. `https://yourdomain.com`) |
| `DATA_DIR` | `./data` | Base path for persistent database and file uploads |
| `MAX_UPLOAD_SIZE_MB`| `50` | Maximum allowable inspection file upload size in megabytes |
| `DEFAULT_MAP_LAT` | `11.1271` | Default map view latitude (Tamil Nadu, India) |
| `DEFAULT_MAP_LNG` | `78.6569` | Default map view longitude (Tamil Nadu, India) |
| `DEFAULT_MAP_ZOOM` | `7` | Default map initial zoom level |

> [!IMPORTANT]
> **Generate a Secure Secret Key:**
> Before deploying, generate a strong random secret using Python:
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

---

## Deployment Option 1: Render.com (Recommended)

Render provides simple git-backed deployments with free SSL, automated builds, and persistent disk support.

### Method A: Blueprint Deployment (One-Click via `render.yaml`)

1. Push your InfraGuard repository to GitHub or GitLab.
2. Log in to [Render](https://render.com) and navigate to **Blueprints**.
3. Click **New Blueprint Instance** and connect your repository.
4. Render automatically parses [`render.yaml`](../render.yaml) and provisions:
   - Python 3.12 Web Service
   - Persistent Disk mounted at `/data`
   - Generated `SECRET_KEY`
5. Click **Apply**. The deployment will build and go live within 2-3 minutes.

### Method B: Manual Web Service Setup on Render

1. On Render Dashboard, click **New +** -> **Web Service**.
2. Connect your Git repository.
3. Configure settings:
   - **Name:** `infraguard`
   - **Language:** `Python 3`
   - **Build Command:** `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT --workers 2`
   - **Health Check Path:** `/api/health`
4. Under **Advanced** -> **Add Disk**:
   - **Name:** `infraguard-storage`
   - **Mount Path:** `/data`
   - **Size:** `1 GB` (or larger)
5. Under **Environment Variables**, add:
   - `INFRAGUARD_ENV` = `production`
   - `SECRET_KEY` = *(paste generated 64-char key)*
   - `DATABASE_URL` = `sqlite:////data/infraguard.db`
   - `DATA_DIR` = `/data`
   - `ALLOWED_ORIGINS` = `*`
6. Click **Create Web Service**.

---

## Deployment Option 2: Docker & Docker Compose (Any VPS / Cloud Server)

InfraGuard includes a production-ready, non-root [`Dockerfile`](../Dockerfile) and [`docker-compose.yml`](../docker-compose.yml).

### Prerequisites on your VPS (Ubuntu/Debian/Rocky Linux)
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose git
sudo systemctl enable --now docker
```

### Steps:

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url> /opt/infraguard
   cd /opt/infraguard
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   nano .env
   ```
   Set `SECRET_KEY`, `ALLOWED_ORIGINS`, and any custom settings.

3. **Start the platform with Docker Compose:**
   ```bash
   docker-compose up -d --build
   ```

4. **Verify container status:**
   ```bash
   docker ps
   docker-compose logs -f
   ```

5. **Test container health:**
   ```bash
   curl -f http://localhost:8000/api/health
   ```
   Expected response:
   ```json
   {"status":"healthy","system":"InfraGuard","version":"1.0.0","mode":"production"}
   ```

### Reverse Proxy & SSL Setup with Nginx & Certbot

Create an Nginx configuration file at `/etc/nginx/sites-available/infraguard`:

```nginx
server {
    server_name infraguard.yourdomain.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 60s;
    }
}
```

Enable the site and obtain free SSL certificates:
```bash
sudo ln -s /etc/nginx/sites-available/infraguard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d infraguard.yourdomain.com
```

---

## Deployment Option 3: Railway / Fly.io / Heroku

InfraGuard is fully compatible with PaaS buildpacks using the included [`Procfile`](../Procfile).

### Railway:
1. Link your GitHub repository in [Railway.app](https://railway.app).
2. Railway detects Python and runs the command from `Procfile`.
3. In Railway settings, add a Persistent Volume mounted at `/app/data` (or attach a Railway PostgreSQL database and set `DATABASE_URL`).
4. Set `SECRET_KEY` in environment variables.

### Fly.io:
1. Run `fly launch` in the repository root. Fly.io detects the `Dockerfile`.
2. Attach a persistent volume for SQLite:
   ```bash
   fly volumes create infraguard_data --size 1
   ```
3. Set secrets:
   ```bash
   fly secrets set SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
   ```
4. Deploy:
   ```bash
   fly deploy
   ```

---

## Database Migration: Switching from SQLite to PostgreSQL

InfraGuard supports PostgreSQL out of the box using SQLAlchemy and `psycopg2-binary`.

1. Provision a PostgreSQL instance (e.g. Render PostgreSQL, Supabase, Neon, AWS RDS).
2. Set the `DATABASE_URL` environment variable:
   ```env
   DATABASE_URL=postgresql://username:password@hostname:5432/infraguard
   ```
   *(Note: URLs starting with `postgres://` are automatically normalized to `postgresql://` by InfraGuard).*
3. On application startup, InfraGuard's lifespan event automatically checks and creates all required tables and seeds default authority accounts and sample data.

---

## Post-Deployment Verification & Smoke Testing

Once deployed, verify the system using these tests:

### 1. Health Probe
```bash
curl -i https://<your-domain>/api/health
```
Status should be `200 OK` with `"status": "healthy"`.

### 2. Authority Portal Access
- Open `https://<your-domain>/` in your browser.
- Log in with default authority credentials:
  - **Username:** `admin`
  - **Password:** `InfraGuard#2026!`
- Ensure the interactive Leaflet map loads centered on Tamil Nadu, India.

### 3. File Upload & Inference
- Navigate to **Upload & Inspect** (`/pages/upload.html`).
- Upload a test road, bridge, pipeline, or power grid image.
- Verify that detection coordinates, bounding boxes, severity assessment, and risk scores display correctly.

### 4. Report Generation
- Navigate to **Authority Reports** (`/pages/reports.html`).
- Click **Export PDF Report** and **Export CSV Report**.
- Verify that downloaded reports accurately reflect filtered database records.

---

## Security Best Practices for Production

1. **Change Default Passwords:** Immediately log in and change passwords for `admin` and `inspector` accounts, or create new administrative users and deactivate default accounts.
2. **Restrict CORS Origins:** Replace `ALLOWED_ORIGINS=*` with your specific domain name (e.g. `ALLOWED_ORIGINS=https://infraguard.yourdomain.com`).
3. **Keep `SECRET_KEY` Private:** Never commit real secret keys or `.env` files into Git repositories.
4. **Regular Backups:** If using SQLite, back up `/data/infraguard.db` regularly. If using PostgreSQL, enable automated managed snapshots.
