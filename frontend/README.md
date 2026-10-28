# InfraGuard Frontend Bundle

## Quick Setup
1. Open `index.html` directly in any modern browser, or serve using any HTTP server:
   ```bash
   python -m http.server 3000 --directory .
   ```
2. The frontend automatically connects to the InfraGuard FastAPI backend at `http://127.0.0.1:8000`.
3. If running the backend on a different domain or port, adjust `API_BASE` in `js/api.js`.
