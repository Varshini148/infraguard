# InfraGuard Backend Service

## Quick Setup (Windows PowerShell)
1. Create a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Copy environment settings:
   ```powershell
   Copy-Item .env.example .env
   ```
4. Start the API server:
   ```powershell
   python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
5. Test suite execution:
   ```powershell
   python -m pytest tests/ -v
   ```
